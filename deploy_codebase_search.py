#!/usr/bin/env python3
"""Deploy complete code-base search infrastructure via Azure Search REST API.

This script is the REST-centric replacement for the old SDK version that relied
on `IndexOperations`.  It performs the following steps:

1.  Ensures the target index exists (and contains the required vector search
    configuration).
2.  Creates/updates the data-source definition.
3.  Creates/updates the skill-set definition.
4.  Creates/updates the indexer.

All HTTP traffic is executed through the minimal asynchronous client defined in
`enhanced_rag.azure_integration.rest` so **no Azure SDK packages are
required**.
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, Any

from enhanced_rag.azure_integration.config import AzureSearchConfig
from enhanced_rag.azure_integration.rest import AzureSearchClient, SearchOperations
from enhanced_rag.azure_integration.automation import IndexAutomation

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


async def _load_json(path: Path) -> Dict[str, Any]:  # noqa: D401
    """Load a JSON file, raising if it does not exist or is invalid."""

    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text())


async def deploy_codebase_search() -> None:  # noqa: D401
    """Deploy the code-base search components using REST API helpers."""

    # ---------------------------------------------------------------------
    # Load environment configuration (ACS_ENDPOINT / ACS_ADMIN_KEY, …)
    # ---------------------------------------------------------------------
    cfg = AzureSearchConfig.from_env()

    print(f"🚀 Deploying to Azure Cognitive Search via REST: {cfg.endpoint}")

    # Create REST client/ops helpers
    async with AzureSearchClient(cfg.endpoint, cfg.api_key, cfg.api_version) as client:
        ops = SearchOperations(client)

        # ------------------------------------------------------------------
        # Step 1: Ensure the index schema exists
        # ------------------------------------------------------------------
        print("\n📊 Step 1: Ensuring index schema …")

        schema_path = Path("azure_search_index_schema.json")
        index_schema = await _load_json(schema_path)

        index_name = index_schema["name"]
        index_auto = IndexAutomation(cfg.endpoint, cfg.api_key, cfg.api_version)
        ensure_result = await index_auto.ensure_index_exists(index_schema)

        if ensure_result["created"]:
            print(f"✅ Index '{index_name}' created")
        elif ensure_result["updated"]:
            print(f"🔄 Index '{index_name}' updated to match schema")
        else:
            print(f"✅ Index '{index_name}' already up-to-date")

        # ------------------------------------------------------------------
        # Steps 2-4 still rely on JSON ARM templates.  We simply POST them to
        # the management endpoints.  These steps mirror the original SDK
        # implementation but without any SDK calls.
        # ------------------------------------------------------------------

        async def _apply_resource(file_name: str, url_suffix: str) -> None:
            body = await _load_json(Path(file_name))
            await client.request("PUT", url_suffix, json=body)
            print(f"✅ {file_name} applied")

        print("\n📁 Step 2: Creating/Updating data-source …")
        await _apply_resource("datasource-config.json", "/datasources/test-datasource")

        print("\n🧠 Step 3: Creating/Updating skill-set …")
        await _apply_resource("skillset-config.json", "/skillsets/test-skillset")

        print("\n⚙️  Step 4: Creating/Updating indexer …")
        await _apply_resource("indexer-config.json", "/indexers/test-indexer")

    # ---------------------------------------------------------------------
    # Verification – fetch index stats to confirm the service is reachable.
    # ---------------------------------------------------------------------
    async with AzureSearchClient(cfg.endpoint, cfg.api_key, cfg.api_version) as client:
        ops = SearchOperations(client)
        stats = await ops.get_index_stats(index_name)
        doc_count = stats.get("documentCount", "N/A")
        print("\n🔍 Index statistics:")
        print(f"   Document count: {doc_count}")

    print("\n🎉 Deployment finished!")


if __name__ == "__main__":
    asyncio.run(deploy_codebase_search())
