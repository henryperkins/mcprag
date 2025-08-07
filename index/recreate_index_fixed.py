#!/usr/bin/env python3
"""
Recreate index with fixed schema (no analyzer on Collection fields)
"""

import os
import asyncio
from typing import Optional
from dotenv import load_dotenv
from azure.search.documents.indexes import SearchIndexClient
from azure.core.credentials import AzureKeyCredential
from enhanced_rag.azure_integration.rest_index_builder import EnhancedIndexBuilder

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

    # Construct client using guaranteed non-empty strings
    index_client = SearchIndexClient(
        endpoint=endpoint,
        credential=AzureKeyCredential(admin_key)
    )
    
    # Delete if exists
    try:
        index_client.delete_index(index_name)
        print(f"Deleted existing index: {index_name}")
    except Exception as e:
        # Avoid failing if index doesn't exist; provide context
        print(f"No existing index to delete or deletion skipped: {e}")
    
    # Create new index with fixed schema
    builder = EnhancedIndexBuilder()
    index = await builder.create_enhanced_rag_index(
        index_name=index_name,
        description="State-of-the-art code search index with semantic search and vector capabilities",
        enable_vectors=True,
        enable_semantic=True
    )
    
    print(f"\n✅ Successfully created index: {index_name}")
    print(f"Fields: {len(index.fields)}")
    
    # List collection fields
    collection_fields = []
    for field in index.fields:
        if hasattr(field, 'type') and str(field.type).startswith('Collection'):
            analyzer = getattr(field, 'analyzer_name', None)
            collection_fields.append(f"{field.name} (analyzer: {analyzer})")
    
    print(f"\nCollection fields:")
    for cf in collection_fields:
        print(f"  - {cf}")

# Async entrypoint structure is correct for a standalone script
asyncio.run(recreate_index())