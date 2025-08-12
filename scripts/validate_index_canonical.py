#!/usr/bin/env python3
"""Validate live index against the canonical schema file."""

import os
import sys
import json
from enhanced_rag.azure_integration.automation import IndexAutomation
from enhanced_rag.core.unified_config import get_config


async def run(index_name: str) -> int:
    # Resolve config for automation
    cfg = get_config()
    automation = IndexAutomation(
        endpoint=cfg.acs_endpoint, 
        api_key=cfg.acs_admin_key.get_secret_value() if cfg.acs_admin_key else ""
    )
    # Load canonical schema and extract required field names
    try:
        with open("azure_search_index_schema.json", "r", encoding="utf-8") as f:
            schema = json.load(f)
        required = [f["name"] for f in schema.get("fields", [])]
    except Exception as e:
        print(f"Failed to load canonical schema: {e}", file=sys.stderr)
        return 2

    # Fetch current index and validate required field presence
    current = await automation.ops.get_index(index_name)
    field_names = {f["name"] for f in current.get("fields", [])}
    missing = [f for f in required if f not in field_names]
    result = {
        "valid": len(missing) == 0,
        "missing_fields": missing,
        "total_fields": len(field_names),
        "has_vector_search": bool(current.get("vectorSearch")),
        "has_semantic_search": bool(current.get("semantic")),
        "scoring_profiles": [p.get("name") for p in current.get("scoringProfiles", [])],
    }
    print(json.dumps(result, indent=2))
    return 0 if result.get("valid") else 1


def main() -> int:
    index_name = os.getenv("ACS_INDEX_NAME", "codebase-mcp-sota")
    import asyncio
    return asyncio.run(run(index_name))


if __name__ == "__main__":
    raise SystemExit(main())
