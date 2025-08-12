#!/usr/bin/env python3
"""
Create enhanced Azure Search index with all advanced features
"""

import asyncio
import sys
import json
from pathlib import Path
from enhanced_rag.azure_integration.automation import IndexAutomation
from enhanced_rag.core.unified_config import get_config
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


async def main():
    try:
        print("Creating Enhanced RAG Index...")
        # Resolve config
        cfg = get_config()
        endpoint = cfg.acs_endpoint
        api_key = cfg.acs_admin_key.get_secret_value() if cfg.acs_admin_key else ""

        automation = IndexAutomation(endpoint=endpoint, api_key=api_key)

        # Load canonical schema and set index name
        schema_path = Path("azure_search_index_schema.json")
        if not schema_path.exists():
            raise FileNotFoundError("Index schema file 'azure_search_index_schema.json' not found")

        index_def = json.loads(schema_path.read_text())
        index_def["name"] = "codebase-mcp-sota"

        # Ensure index exists / is updated
        op = await automation.ensure_index_exists(index_def)
        print(f"✅ Ensured index: {index_def['name']} (created={op.get('created')}, updated={op.get('updated')})")

        # Validate required fields presence
        current = await automation.ops.get_index(index_def["name"])
        field_names = {f["name"] for f in current.get("fields", [])}
        required = {"content", "function_name", "repository", "language", "content_vector"}
        missing = list(required - field_names)
        if not missing:
            print("✅ Schema validation passed")
            print(f"   Total fields: {len(field_names)}")
            print(f"   Has vector search: {bool(current.get('vectorSearch'))}")
            print(f"   Has semantic search: {bool(current.get('semantic'))}")
            profiles = [p.get('name') for p in current.get('scoringProfiles', [])]
            print(f"   Scoring profiles: {', '.join(profiles)}")
        else:
            print(f"⚠️  Missing fields: {missing}")

    except Exception as e:
        print(f"❌ Error creating index: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
