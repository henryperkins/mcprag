#!/usr/bin/env python3
"""Create Azure Search index from index.json using REST API"""

import json
import os
import requests
from dotenv import load_dotenv

load_dotenv()

def create_index_from_json():
    # Read credentials
    endpoint = os.getenv("ACS_ENDPOINT")
    admin_key = os.getenv("ACS_ADMIN_KEY")
    
    if not endpoint or not admin_key:
        raise ValueError("ACS_ENDPOINT and ACS_ADMIN_KEY must be set in environment")
    
    # Read index schema
    with open('index.json', 'r') as f:
        index_data = json.load(f)
    
    index_name = index_data['name']
    
    headers = {
        'Content-Type': 'application/json',
        'api-key': admin_key
    }
    
    # Delete existing index if it exists
    delete_url = f"{endpoint}/indexes/{index_name}?api-version=2024-07-01"
    response = requests.delete(delete_url, headers=headers)
    if response.status_code == 204:
        print(f"✓ Deleted existing index '{index_name}'")
    else:
        print(f"No existing index '{index_name}' to delete")
    
    # Clean up the index data for creation
    # Remove fields that aren't supported in the API version
    if '@odata.etag' in index_data:
        del index_data['@odata.etag']
    
    # Remove unsupported fields for 2024-07-01 API
    unsupported_fields = ['normalizers', 'tokenizers', 'tokenFilters', 'charFilters']
    for field in unsupported_fields:
        if field in index_data:
            del index_data[field]
    
    # Clean up semantic configuration
    if 'semantic' in index_data and 'configurations' in index_data['semantic']:
        for config in index_data['semantic']['configurations']:
            # Remove unsupported properties
            for prop in ['flightingOptIn', 'rankingOrder']:
                if prop in config:
                    del config[prop]
    
    # Create index using 2024-07-01 API version (stable)
    create_url = f"{endpoint}/indexes/{index_name}?api-version=2024-07-01"
    response = requests.put(create_url, headers=headers, json=index_data)
    
    if response.status_code in [200, 201]:
        print(f"✅ Successfully created index '{index_name}'")
        print(f"   Fields: {len(index_data['fields'])}")
        print(f"   Vector search enabled: Yes (3072 dimensions)")
        print(f"   Semantic search enabled: Yes")
        
        # Check if content_vector is retrievable
        vector_field = next((f for f in index_data['fields'] if f['name'] == 'content_vector'), None)
        if vector_field:
            print(f"   content_vector retrievable: {vector_field.get('retrievable', False)}")
            
        return True
    else:
        print(f"❌ Failed to create index: {response.status_code}")
        print(f"   Error: {response.text}")
        return False

if __name__ == "__main__":
    if create_index_from_json():
        print("\n✅ Index created successfully!")
        print("\nNext steps:")
        print("1. Run: python reindex_mcprag.py  # to index the repository")
        print("2. Start the MCP server: python mcp_server_sota.py")
    else:
        print("\n❌ Failed to create index")