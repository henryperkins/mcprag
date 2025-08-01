#!/usr/bin/env python3
"""Test vector search functionality"""

import os
from dotenv import load_dotenv
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.core.credentials import AzureKeyCredential
from vector_embeddings import VectorEmbedder

load_dotenv()

def test_vector_search():
    # Initialize clients
    client = SearchClient(
        endpoint=os.getenv("ACS_ENDPOINT"),
        index_name="codebase-mcp-sota",
        credential=AzureKeyCredential(os.getenv("ACS_ADMIN_KEY"))
    )
    
    embedder = VectorEmbedder()
    
    # Test query
    query = "test function"
    
    try:
        # Generate embedding
        embedding = embedder.generate_embedding(query)
        print(f"✅ Generated embedding with {len(embedding)} dimensions")
        
        # Create vector query
        vector_query = VectorizedQuery(
            vector=embedding,
            k_nearest_neighbors=5,
            fields="content_vector"
        )
        
        # Search with just vector
        print("\n🔍 Testing vector-only search...")
        results = client.search(
            search_text=None,
            vector_queries=[vector_query],
            top=3
        )
        
        count = 0
        for result in results:
            count += 1
            print(f"\nResult {count}:")
            print(f"  File: {result.get('file_path', 'N/A')}")
            print(f"  Function: {result.get('function_signature', 'N/A')}")
            print(f"  Score: {result.get('@search.score', 'N/A')}")
        
        if count == 0:
            print("❌ No results found")
        else:
            print(f"\n✅ Found {count} results")
            
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

    # Test hybrid search
    try:
        print("\n\n🔍 Testing hybrid search (text + vector)...")
        embedding = embedder.generate_embedding(query)
        vector_query = VectorizedQuery(
            vector=embedding,
            k_nearest_neighbors=5,
            fields="content_vector"
        )
        
        results = client.search(
            search_text=query,
            vector_queries=[vector_query],
            top=3
        )
        
        count = 0
        for result in results:
            count += 1
            print(f"\nResult {count}:")
            print(f"  File: {result.get('file_path', 'N/A')}")
            print(f"  Function: {result.get('function_signature', 'N/A')}")
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
    test_vector_search()