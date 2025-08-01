#!/usr/bin/env python3
"""
Check existing Azure Search indexes
"""

import os
from dotenv import load_dotenv
from azure.search.documents.indexes import SearchIndexClient
from azure.core.credentials import AzureKeyCredential

# Load environment variables
load_dotenv()

def check_indexes():
    endpoint = os.getenv("ACS_ENDPOINT")
    api_key = os.getenv("ACS_ADMIN_KEY")
    
    if not endpoint or not api_key:
        print("❌ Missing Azure Search credentials")
        return
    
    # Create index client
    index_client = SearchIndexClient(
        endpoint=endpoint,
        credential=AzureKeyCredential(api_key)
    )
    
    try:
        # List all indexes
        indexes = index_client.list_indexes()
        print("Existing indexes:")
        print("-" * 50)
        
        for index in indexes:
            print(f"\n📁 Index: {index.name}")
            print(f"   Fields: {len(index.fields)}")
            print(f"   Created: {index.e_tag}")
            
            # Check if it's our target index
            if index.name == "codebase-mcp-sota":
                print("\n   ⚠️  Target index already exists!")
                print("   Field names:")
                for field in index.fields[:10]:  # Show first 10 fields
                    print(f"      - {field.name} ({field.type})")
                if len(index.fields) > 10:
                    print(f"      ... and {len(index.fields) - 10} more fields")
                
                # Check semantic config
                if index.semantic_search:
                    print("\n   Semantic configurations:")
                    for config in index.semantic_search.configurations:
                        print(f"      - {config.name}")
        
        print("\n" + "-" * 50)
        
        # Ask what to do
        if "codebase-mcp-sota" in [idx.name for idx in index_client.list_indexes()]:
            print("\n⚠️  The index 'codebase-mcp-sota' already exists.")
            print("Options:")
            print("1. Delete and recreate (will lose all data)")
            print("2. Use existing index")
            print("3. Create with different name")
            
    except Exception as e:
        print(f"❌ Error listing indexes: {e}")

if __name__ == "__main__":
    check_indexes()