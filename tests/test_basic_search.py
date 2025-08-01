#!/usr/bin/env python3
"""Test basic search without vectors"""

import os
from dotenv import load_dotenv
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

load_dotenv()

def test_basic_search():
    # Initialize client
    client = SearchClient(
        endpoint=os.getenv("ACS_ENDPOINT"),
        index_name="codebase-mcp-sota",
        credential=AzureKeyCredential(os.getenv("ACS_ADMIN_KEY"))
    )
    
    # Test basic text search
    query = "test function"
    
    try:
        print(f"🔍 Testing basic text search for: '{query}'")
        results = client.search(
            search_text=query,
            top=5,
            select=["file_path", "signature", "content", "semantic_context", "function_name"]
        )
        
        count = 0
        for result in results:
            count += 1
            print(f"\nResult {count}:")
            print(f"  File: {result.get('file_path', 'N/A')}")
            print(f"  Function: {result.get('function_name', 'N/A')}")
            print(f"  Signature: {result.get('signature', 'N/A')}")
            context = result.get('semantic_context', 'N/A')
            if context and context != 'N/A':
                print(f"  Context: {context[:100]}...")
            else:
                print(f"  Context: N/A")
            
        if count == 0:
            print("❌ No results found")
        else:
            print(f"\n✅ Found {count} results")
            
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    test_basic_search()