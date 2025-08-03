#!/usr/bin/env python3
"""
Test Azure Search directly to diagnose the issue
"""

import os
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizableTextQuery
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv

load_dotenv()

def test_search():
    endpoint = os.getenv("ACS_ENDPOINT")
    admin_key = os.getenv("ACS_ADMIN_KEY")
    index_name = "codebase-mcp-sota"
    
    print(f"Connecting to: {endpoint}")
    print(f"Index: {index_name}")
    
    client = SearchClient(
        endpoint=endpoint,
        index_name=index_name,
        credential=AzureKeyCredential(admin_key)
    )
    
    # Test 1: Simple text search
    print("\n1. Testing simple text search...")
    try:
        results = client.search(
            search_text="ErrorHandler",
            select=["repository", "file_path", "language", "content"],
            top=3
        )
        
        count = 0
        for result in results:
            count += 1
            print(f"\nResult {count}:")
            print(f"  Repository: {result.get('repository')}")
            print(f"  File: {result.get('file_path')}")
            print(f"  Language: {result.get('language')}")
            print(f"  Content preview: {str(result.get('content', ''))[:100]}...")
            
        if count == 0:
            print("No results found")
            
    except Exception as e:
        print(f"Error in text search: {e}")
    
    # Test 2: Semantic search
    print("\n\n2. Testing semantic search...")
    try:
        results = client.search(
            search_text="ErrorHandler class definition",
            query_type="semantic",
            semantic_configuration_name="semantic-config",
            select=["repository", "file_path", "language", "content"],
            top=3
        )
        
        count = 0
        for result in results:
            count += 1
            print(f"\nResult {count}:")
            print(f"  Repository: {result.get('repository')}")
            print(f"  File: {result.get('file_path')}")
            print(f"  Score: {result.get('@search.score')}")
            
        if count == 0:
            print("No results found")
            
    except Exception as e:
        print(f"Error in semantic search: {e}")
    
    # Test 3: Vector search with VectorizableTextQuery
    print("\n\n3. Testing vector search with text-to-vector...")
    try:
        vector_query = VectorizableTextQuery(
            text="ErrorHandler class",
            k_nearest_neighbors=3,
            fields="content_vector"
        )
        
        results = client.search(
            search_text="ErrorHandler",
            vector_queries=[vector_query],
            select=["repository", "file_path", "language", "content"],
            top=3
        )
        
        count = 0
        for result in results:
            count += 1
            print(f"\nResult {count}:")
            print(f"  Repository: {result.get('repository')}")
            print(f"  File: {result.get('file_path')}")
            print(f"  Score: {result.get('@search.score')}")
            
        if count == 0:
            print("No results found")
            
    except Exception as e:
        print(f"Error in vector search: {e}")
        print(f"Error type: {type(e).__name__}")

if __name__ == "__main__":
    test_search()