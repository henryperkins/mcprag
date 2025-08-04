#!/usr/bin/env python3
"""
Check the current index schema - compatible version
"""
import os
import sys
import json
import requests
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Configuration
endpoint = os.getenv("ACS_ENDPOINT")
admin_key = os.getenv("ACS_ADMIN_KEY")
index_name = "codebase-mcp-sota"

if not endpoint or not admin_key:
    print("❌ Missing Azure Search credentials")
    sys.exit(1)

# Use REST API directly
api_version = "2024-05-01-preview"
url = f"{endpoint}/indexes/{index_name}?api-version={api_version}"
headers = {
    "Content-Type": "application/json",
    "api-key": admin_key
}

try:
    # Get the index definition
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        index = response.json()
        
        print(f"📚 Index: {index['name']}")
        print(f"\n📋 Fields in the index:")
        
        for field in index.get('fields', []):
            print(f"\n  Field: {field['name']}")
            print(f"    Type: {field['type']}")
            print(f"    Key: {field.get('key', False)}")
            print(f"    Searchable: {field.get('searchable', False)}")
            print(f"    Filterable: {field.get('filterable', False)}")
            print(f"    Sortable: {field.get('sortable', False)}")
            print(f"    Facetable: {field.get('facetable', False)}")
            print(f"    Retrievable: {field.get('retrievable', True)}")
            
            # Check if it's a vector field
            if field['type'] == 'Collection(Edm.Single)':
                print(f"    ⚡ VECTOR FIELD")
                if 'dimensions' in field:
                    print(f"    Dimensions: {field['dimensions']}")
                if 'vectorSearchProfile' in field:
                    print(f"    Vector Profile: {field['vectorSearchProfile']}")
        
        # Check vector search configuration
        if 'vectorSearch' in index:
            print(f"\n🔍 Vector Search Configuration:")
            vs = index['vectorSearch']
            if 'algorithms' in vs:
                print(f"  Algorithms: {len(vs['algorithms'])}")
                for algo in vs['algorithms']:
                    print(f"    - {algo['name']} (kind: {algo['kind']})")
                    if 'hnswParameters' in algo:
                        params = algo['hnswParameters']
                        print(f"      metric: {params.get('metric', 'N/A')}")
                        print(f"      m: {params.get('m', 'N/A')}")
                        print(f"      efConstruction: {params.get('efConstruction', 'N/A')}")
            
            if 'profiles' in vs:
                print(f"\n  Vector Profiles: {len(vs['profiles'])}")
                for profile in vs['profiles']:
                    print(f"    - {profile['name']} (algorithm: {profile['algorithmConfigurationName']})")
        
        # Check semantic configuration
        if 'semantic' in index:
            print(f"\n🧠 Semantic Search Configuration:")
            if 'configurations' in index['semantic']:
                for config in index['semantic']['configurations']:
                    print(f"  - {config['name']}")
        
        # Save full schema for analysis
        with open('current_index_schema.json', 'w') as f:
            json.dump(index, f, indent=2)
        print(f"\n💾 Full schema saved to current_index_schema.json")
        
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()