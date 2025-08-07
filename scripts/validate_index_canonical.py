#!/usr/bin/env python3
"""Validate live index against the canonical schema file."""

import os
import sys
import json

from enhanced_rag.azure_integration.rest_index_builder import EnhancedIndexBuilder


async def run(index_name: str) -> int:
    builder = EnhancedIndexBuilder()
    # Load canonical schema and extract required field names
    try:
        with open("azure_search_index_schema.json", "r", encoding="utf-8") as f:
            schema = json.load(f)
        required = [f["name"] for f in schema.get("fields", [])]
    except Exception as e:
        print(f"Failed to load canonical schema: {e}", file=sys.stderr)
        return 2

    result = await builder.validate_index_schema(index_name, required)
    print(json.dumps(result, indent=2))
    return 0 if result.get("valid") else 1


def main() -> int:
    index_name = os.getenv("ACS_INDEX_NAME", "codebase-mcp-sota")
    import asyncio
    return asyncio.run(run(index_name))


if __name__ == "__main__":
    raise SystemExit(main())

