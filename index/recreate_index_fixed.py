#!/usr/bin/env python3
"""
Recreate index with fixed schema (no analyzer on Collection fields)
"""

import os
import asyncio
from typing import Optional
from dotenv import load_dotenv
from enhanced_rag.azure_integration.automation import IndexAutomation
from enhanced_rag.azure_integration.config import AzureSearchConfig
import json
from pathlib import Path

load_dotenv()

def _require_env(name: str, *, allow_empty: bool = False, aliases: Optional[list[str]] = None) -> str:
    """
    Fetch a required environment variable as a non-None, non-empty string.
    - Strips whitespace
    - Supports common alias names if provided (first non-empty wins)
    Raises RuntimeError with a clear message if missing/empty.
    """
    candidates = [name] + (aliases or [])
    for key in candidates:
        val: Optional[str] = os.getenv(key)
        if val is not None:
            val = val.strip()
            if allow_empty or val:
                return val
    alias_note = f" (aliases tried: {', '.join(candidates[1:])})" if aliases else ""
    raise RuntimeError(f"Required environment variable '{name}' is not set or empty{alias_note}")

async def recreate_index():
    # Resolve required configuration with validation to satisfy type checkers and runtime
    endpoint = _require_env("ACS_ENDPOINT", aliases=["AZURE_SEARCH_ENDPOINT"])
    admin_key = _require_env("ACS_ADMIN_KEY", aliases=["AZURE_SEARCH_ADMIN_KEY", "SEARCH_ADMIN_KEY"])
    # Optional: allow overriding index name via env, else default
    index_name = os.getenv("ACS_INDEX_NAME", "codebase-mcp-sota").strip() or "codebase-mcp-sota"

    # Construct automation client using guaranteed non-empty strings
    automation = IndexAutomation(endpoint=endpoint, api_key=admin_key)

    # Delete if exists
    try:
        import asyncio as _asyncio
        _loop = _asyncio.new_event_loop()
        _asyncio.set_event_loop(_loop)
        try:
            _loop.run_until_complete(automation.ops.delete_index(index_name))
            print(f"Deleted existing index: {index_name}")
        finally:
            _loop.close()
    except Exception as e:
        # Avoid failing if index doesn't exist; provide context
        print(f"No existing index to delete or deletion skipped: {e}")

    # Create new index with fixed schema
    # Create new index from canonical schema
    schema_path = Path("azure_search_index_schema.json")
    if not schema_path.exists():
        raise FileNotFoundError("Index schema file 'azure_search_index_schema.json' not found")
    index_def = json.loads(schema_path.read_text())
    index_def["name"] = index_name
    op = await automation.ensure_index_exists(index_def)

    print(f"\n✅ Successfully created index: {index_name} (created={op.get('created')}, updated={op.get('updated')})")
    # Fetch current index schema via REST to inspect fields
    current = await automation.ops.get_index(index_name)
    fields = current.get("fields", [])
    print(f"Fields: {len(fields)}")

    # List collection fields
    collection_fields = []
    for field in fields:
        ftype = field.get("type")
        if isinstance(ftype, str) and ftype.startswith("Collection("):
            analyzer = field.get("analyzer")
            collection_fields.append(f"{field.get('name')} (analyzer: {analyzer})")

    print(f"\nCollection fields:")
    for cf in collection_fields:
        print(f"  - {cf}")

# Async entrypoint structure is correct for a standalone script
asyncio.run(recreate_index())
