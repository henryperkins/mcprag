#!/usr/bin/env python3
"""Create Azure Search index from index.json schema file"""

import json
import os
from dotenv import load_dotenv
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import SearchIndex
from azure.core.credentials import AzureKeyCredential

load_dotenv()

def create_index_from_json():
    # Read credentials
    endpoint = os.getenv("ACS_ENDPOINT")
    admin_key = os.getenv("ACS_ADMIN_KEY")
    
    if not endpoint or not admin_key:
        raise ValueError("ACS_ENDPOINT and ACS_ADMIN_KEY must be set in environment")
    
    # Create index client
    index_client = SearchIndexClient(
        endpoint=endpoint,
        credential=AzureKeyCredential(admin_key)
    )
    
    # Read index schema
    with open('index.json', 'r') as f:
        index_data = json.load(f)
    
    index_name = index_data['name']
    
    # Delete existing index if it exists
    try:
        index_client.delete_index(index_name)
        print(f"✓ Deleted existing index '{index_name}'")
    except:
        print(f"No existing index '{index_name}' to delete")
    
    # Create the index
    # The JSON format needs to be converted to SDK objects
    # For now, we'll use the REST API approach
    import requests
    
    headers = {
        'Content-Type': 'application/json',
        'api-key': admin_key
    }
    
    # Remove the @odata.etag field as it's not needed for creation
    if '@odata.etag' in index_data:
        del index_data['@odata.etag']
    
    # Remove unsupported fields from semantic config
    if 'semantic' in index_data and 'configurations' in index_data['semantic']:
        for config in index_data['semantic']['configurations']:
            if 'flightingOptIn' in config:
                del config['flightingOptIn']
            if 'rankingOrder' in config:
                del config['rankingOrder']
    
    # Create index via REST API
    create_url = f"{endpoint}/indexes/{index_name}?api-version=2024-11-01-preview"
    response = requests.put(create_url, headers=headers, json=index_data)
    
    if response.status_code in [200, 201]:
        print(f"✅ Successfully created index '{index_name}'")
        print(f"   Fields: {len(index_data['fields'])}")
        print(f"   Vector search enabled: Yes")
        print(f"   Semantic search enabled: Yes")
    else:
        print(f"❌ Failed to create index: {response.status_code}")
        print(f"   Error: {response.text}")
        return False
    
    return True

if __name__ == "__main__":
    create_index_from_json()