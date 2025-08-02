#!/usr/bin/env python3
"""
Recreate the Azure Search index using the RAG-optimized schema
that includes repository, file_path, and language fields required by MCP server
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv()

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from enhanced_rag.azure_integration.enhanced_index_builder import EnhancedIndexBuilder

async def recreate_index_for_mcp():
    """Recreate index with proper schema for MCP compatibility"""
    
    endpoint = os.getenv("ACS_ENDPOINT")
    admin_key = os.getenv("ACS_ADMIN_KEY")
    
    if not endpoint or not admin_key:
        print("ERROR: ACS_ENDPOINT and ACS_ADMIN_KEY must be set", file=sys.stderr)
        sys.exit(1)
    
    # Index name
    index_name = os.getenv("ACS_INDEX_NAME", "codebase-mcp-sota-3072")
    
    print(f"Recreating index '{index_name}' with MCP-compatible schema...")
    
    # Initialize builder
    builder = EnhancedIndexBuilder()
    
    # Delete existing index if present
    try:
        builder.index_client.delete_index(index_name)
        print(f"✓ Deleted existing index '{index_name}'")
    except Exception as e:
        print(f"  (No existing index to delete: {e})")
    
    # Create the RAG-optimized index which includes repository field
    index = builder.create_rag_optimized_index(
        index_name=index_name,
        enable_vectors=True,
        vector_dimensions=3072
    )
    
    # Create the index
    result = builder.create_or_update_index(index)
    print(f"✓ Created index '{result.name}'")
    
    # Verify critical fields
    print("\nVerifying MCP-required fields:")
    required_fields = ["repository", "file_path", "language", "content"]
    
    # Get the created index to verify fields
    created_index = builder.index_client.get_index(index_name)
    field_names = {f.name for f in created_index.fields}
    
    all_present = True
    for field_name in required_fields:
        if field_name in field_names:
            print(f"  ✓ {field_name}: Present")
        else:
            print(f"  ✗ {field_name}: MISSING")
            all_present = False
    
    if all_present:
        print("\n✅ Index is now compatible with MCP server!")
        print("\nNext steps:")
        print("1. Re-index your code using smart_indexer.py")
        print("2. The MCP server should now work correctly")
    else:
        print("\n❌ Some required fields are still missing!")
        print("Check the EnhancedIndexBuilder.create_rag_optimized_index method")
    
    # Also check vector field configuration
    print("\nVector field configuration:")
    for field in created_index.fields:
        if hasattr(field, 'vector_search_dimensions') and field.vector_search_dimensions:
            print(f"  ✓ {field.name}: {field.vector_search_dimensions} dimensions")

if __name__ == "__main__":
    asyncio.run(recreate_index_for_mcp())