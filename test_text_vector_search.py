#!/usr/bin/env python3
"""Test text-to-vector search using index vectorizer"""

import os
from dotenv import load_dotenv
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizableTextQuery
from azure.core.credentials import AzureKeyCredential

load_dotenv()

def test_text_vector_search():
    # Initialize client
    client = SearchClient(
        endpoint=os.getenv("ACS_ENDPOINT"),
        index_name="codebase-mcp-sota",
        credential=AzureKeyCredential(os.getenv("ACS_ADMIN_KEY"))
    )
    
    # Test query
    query = "test function"
    
    try:
        print(f"🔍 Testing text-to-vector search for: '{query}'")
        
        # Create a text-based vector query that uses the index's vectorizer
        vector_query = VectorizableTextQuery(
            text=query,
            k_nearest_neighbors=5,
            fields="content_vector"
        )
        
        # Search with text-to-vector
        results = client.search(
            search_text=None,  # No text search, just vector
            vector_queries=[vector_query],
            top=5,
            select=["file_path", "signature", "function_name", "semantic_context"]
        )
        
        count = 0
        for result in results:
            count += 1
            print(f"\nResult {count}:")
            print(f"  File: {result.get('file_path', 'N/A')}")
            print(f"  Function: {result.get('function_name', 'N/A')}")
            print(f"  Signature: {result.get('signature', 'N/A')}")
            print(f"  Score: {result.get('@search.score', 'N/A')}")
            
        if count == 0:
            print("❌ No results found")
        else:
            print(f"\n✅ Found {count} results")
            
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_text_vector_search()