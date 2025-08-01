#!/usr/bin/env python3
"""
Recreate index with fixed schema (no analyzer on Collection fields)
"""

import os
import asyncio
from dotenv import load_dotenv
from azure.search.documents.indexes import SearchIndexClient
from azure.core.credentials import AzureKeyCredential
from enhanced_rag.azure_integration.enhanced_index_builder import EnhancedIndexBuilder

load_dotenv()

async def recreate_index():
    # Delete existing index
    index_client = SearchIndexClient(
        endpoint=os.getenv("ACS_ENDPOINT"),
        credential=AzureKeyCredential(os.getenv("ACS_ADMIN_KEY"))
    )
    
    index_name = "codebase-mcp-sota"
    
    # Delete if exists
    try:
        index_client.delete_index(index_name)
        print(f"Deleted existing index: {index_name}")
    except:
        print("No existing index to delete")
    
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

# Run
asyncio.run(recreate_index())