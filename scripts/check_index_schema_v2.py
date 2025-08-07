#!/usr/bin/env python3
"""Export the current live index schema to current_index_schema.json."""

import os
import json

from enhanced_rag.azure_integration.rest import AzureSearchClient, SearchOperations


async def run(index_name: str) -> None:
    endpoint = os.getenv("ACS_ENDPOINT")
    api_key = os.getenv("ACS_ADMIN_KEY")
    client = AzureSearchClient(endpoint=endpoint, api_key=api_key)
    ops = SearchOperations(client)
    schema = await ops.get_index(index_name)
    with open("current_index_schema.json", "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)


def main() -> int:
    index_name = os.getenv("ACS_INDEX_NAME", "codebase-mcp-sota")
    import asyncio
    asyncio.run(run(index_name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

