#!/usr/bin/env python3
"""
Check the current index schema to understand field configuration
"""
import os
import sys
import json
from dotenv import load_dotenv
from azure.search.documents.indexes import SearchIndexClient
from azure.core.credentials import AzureKeyCredential

# Load environment
load_dotenv()

# Configuration
endpoint = os.getenv("ACS_ENDPOINT")
admin_key = os.getenv("ACS_ADMIN_KEY")
index_name = "codebase-mcp-sota"

if not endpoint or not admin_key:
    print("❌ Missing Azure Search credentials")
    sys.exit(1)

# Create index client
index_client = SearchIndexClient(
    endpoint=endpoint,
    credential=AzureKeyCredential(admin_key)
)

try:
    # Get the index definition
    index = index_client.get_index(index_name)
    
    print(f"📚 Index: {index.name}")
    print(f"\n📋 Fields in the index:")
    
    for field in index.fields:
        print(f"\n  Field: {field.name}")
        print(f"    Type: {field.type}")
        print(f"    Key: {field.key}")
        print(f"    Searchable: {field.searchable}")
        print(f"    Filterable: {field.filterable}")
        print(f"    Sortable: {field.sortable}")
        print(f"    Facetable: {field.facetable}")
        print(f"    Retrievable: {field.retrievable}")
        
        # Check if it's a vector field
        if hasattr(field, 'vector_search_dimensions'):
            print(f"    Vector Dimensions: {field.vector_search_dimensions}")
            print(f"    Vector Config: {field.vector_search_configuration}")
    
    # Check vector search configuration
    if hasattr(index, 'vector_search') and index.vector_search:
        print(f"\n🔍 Vector Search Configuration:")
        print(f"  Algorithms: {len(index.vector_search.algorithms) if index.vector_search.algorithms else 0}")
        if index.vector_search.algorithms:
            for algo in index.vector_search.algorithms:
                print(f"    - {algo.name} ({algo.kind})")
                
    # Check semantic configuration
    if hasattr(index, 'semantic_search') and index.semantic_search:
        print(f"\n🧠 Semantic Search Configuration:")
        if index.semantic_search.configurations:
            for config in index.semantic_search.configurations:
                print(f"  - {config.name}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()