#!/usr/bin/env python3
"""Add or verify the `content_vector` field on an existing index (REST version).

This is the REST-API replacement for the original `add_vector_field.py` that
depended on `IndexOperations` and the Azure SDK models.  The new
implementation fetches the index JSON definition, patches it in-memory, and
sends it back with a PUT request.

Limitations
-----------
• The script no longer tries to build a full `SearchIndex` object; instead it
  works directly with the JSON representation.
• Some advanced settings (e.g. algorithm parameters) are hard-coded to the
  defaults required by the migration guidance.
"""

import asyncio
import copy
import json
from typing import Any, Dict

from enhanced_rag.azure_integration.config import AzureSearchConfig
from enhanced_rag.azure_integration.rest import AzureSearchClient, SearchOperations


VECTOR_FIELD_NAME = "content_vector"


def _vector_field_definition(dimensions: int = 3072) -> Dict[str, Any]:
    """Return a minimal vector field definition compatible with REST schema."""
    return {
        "name": VECTOR_FIELD_NAME,
        "type": "Collection(Edm.Single)",
        "searchable": True,
        "vectorSearchDimensions": dimensions,
        "vectorSearchProfileName": "vector-profile",
    }


async def add_vector_field(index_name: str = "codebase-mcp-sota", dimensions: int = 3072) -> None:
    """Ensure *content_vector* exists on *index_name* and update if missing."""

    cfg = AzureSearchConfig.from_env()
    async with AzureSearchClient(cfg.endpoint, cfg.api_key, cfg.api_version) as client:
        ops = SearchOperations(client)

        # ------------------------------------------------------------------
        # Fetch current index definition
        # ------------------------------------------------------------------
        index_def = await ops.get_index(index_name)

        fields = index_def.get("fields", [])
        if any(f.get("name") == VECTOR_FIELD_NAME for f in fields):
            print("✅ content_vector field already present – nothing to do.")
            return

        print("➕ Adding content_vector field …")

        # Patch fields
        updated_def = copy.deepcopy(index_def)
        updated_def["fields"] = fields + [_vector_field_definition(dimensions)]

        # Ensure vectorSearch section exists
        if "vectorSearch" not in updated_def:
            updated_def["vectorSearch"] = {
                "profiles": [
                    {
                        "name": "vector-profile",
                        "algorithmConfigurationName": "vector-config",
                    }
                ],
                "algorithms": [
                    {
                        "name": "vector-config",
                        "kind": "hnsw",
                        "parameters": {
                            "m": 4,
                            "efConstruction": 400,
                            "efSearch": 500,
                            "metric": "cosine",
                        },
                    }
                ],
            }

        # PUT the updated index definition
        await ops.create_index(updated_def)

        print("✅ Vector field added and index updated successfully.")


if __name__ == "__main__":
    asyncio.run(add_vector_field())
