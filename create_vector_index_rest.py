#!/usr/bin/env python3
"""
Create Azure Search index with vector support using REST API directly
"""

import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

def main():
    endpoint = os.getenv("ACS_ENDPOINT")
    admin_key = os.getenv("ACS_ADMIN_KEY")
    index_name = "codebase-mcp-sota"
    
    if not endpoint or not admin_key:
        print("❌ Missing ACS_ENDPOINT or ACS_ADMIN_KEY")
        return
    
    # Determine vector dimensions based on available API keys
    if os.getenv("AZURE_OPENAI_KEY") and os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME") == "text-embedding-3-large":
        dimensions = 3072  # text-embedding-3-large
        print("✅ Azure OpenAI text-embedding-3-large detected - using 3072 dimensions")
    elif os.getenv("OPENAI_API_KEY"):
        dimensions = 3072  # text-embedding-3-large
        print("✅ OpenAI API key detected - using text-embedding-3-large (3072 dimensions)")
    else:
        dimensions = 1536  # text-embedding-ada-002
        print("ℹ️  No embedding API key found - using default 1536 dimensions")
    
    # Define the index schema
    index_schema = {
        "name": index_name,
        "fields": [
            {"name": "id", "type": "Edm.String", "key": True, "filterable": True},
            {"name": "content", "type": "Edm.String", "searchable": True, "analyzer": "en.microsoft"},
            {
                "name": "content_vector",
                "type": "Collection(Edm.Single)",
                "searchable": True,
                "retrievable": False,
                "dimensions": dimensions,
                "vectorSearchProfile": "vector-profile-hnsw"
            },
            {"name": "repository", "type": "Edm.String", "searchable": True, "filterable": True, "sortable": True, "facetable": True},
            {"name": "file_path", "type": "Edm.String", "searchable": True, "filterable": True, "sortable": True},
            {"name": "language", "type": "Edm.String", "filterable": True, "facetable": True},
            {"name": "function_name", "type": "Edm.String", "searchable": True, "filterable": True},
            {"name": "class_name", "type": "Edm.String", "searchable": True, "filterable": True},
            {"name": "signature", "type": "Edm.String", "retrievable": True},
            {"name": "docstring", "type": "Edm.String", "searchable": True},
            {"name": "semantic_context", "type": "Edm.String", "searchable": True},
            {"name": "chunk_type", "type": "Edm.String", "filterable": True},
            {"name": "chunk_id", "type": "Edm.String", "filterable": True},
            {"name": "start_line", "type": "Edm.Int32", "filterable": True},
            {"name": "end_line", "type": "Edm.Int32", "filterable": True},
            {"name": "last_modified", "type": "Edm.DateTimeOffset", "filterable": True, "sortable": True},
            {"name": "file_extension", "type": "Edm.String", "filterable": True, "facetable": True},
            {"name": "imports", "type": "Collection(Edm.String)", "searchable": True, "filterable": True},
            {"name": "dependencies", "type": "Collection(Edm.String)", "retrievable": True}
        ],
        "vectorSearch": {
            "algorithms": [
                {
                    "name": "hnsw-config",
                    "kind": "hnsw",
                    "hnswParameters": {
                        "m": 12,
                        "efConstruction": 300,
                        "efSearch": 120,
                        "metric": "cosine"
                    }
                }
            ],
            "profiles": [
                {
                    "name": "vector-profile-hnsw",
                    "algorithm": "hnsw-config"
                }
            ]
        }
    }
    
    # Delete existing index if it exists
    delete_url = f"{endpoint}/indexes/{index_name}?api-version=2024-05-01-preview"
    headers = {
        "Content-Type": "application/json",
        "api-key": admin_key
    }
    
    print(f"🔧 Deleting existing index: {index_name}")
    response = requests.delete(delete_url, headers=headers)
    if response.status_code == 204:
        print("✅ Deleted existing index")
    elif response.status_code == 404:
        print("ℹ️  No existing index to delete")
    
    # Create new index
    create_url = f"{endpoint}/indexes?api-version=2024-05-01-preview"
    print(f"🔧 Creating new index: {index_name}")
    
    response = requests.post(create_url, headers=headers, json=index_schema)
    
    if response.status_code == 201:
        print("✅ Successfully created index with vector support!")
        
        # Get and display the created index
        get_url = f"{endpoint}/indexes/{index_name}?api-version=2024-05-01-preview"
        response = requests.get(get_url, headers=headers)
        
        if response.status_code == 200:
            index = response.json()
            vector_search = index.get("vectorSearch")
            
            if vector_search:
                print("\n📊 Vector Search Configuration:")
                algorithms = vector_search.get("algorithms", [])
                for algo in algorithms:
                    print(f"  - Algorithm: {algo['name']} ({algo['kind']})")
                    if algo['kind'] == 'hnsw':
                        params = algo.get('hnswParameters', {})
                        print(f"    - m: {params.get('m')}")
                        print(f"    - efConstruction: {params.get('efConstruction')}")
                        print(f"    - efSearch: {params.get('efSearch')}")
                        print(f"    - metric: {params.get('metric')}")
            
            # Count vector fields
            vector_fields = [f for f in index.get("fields", []) 
                           if f.get("type") == "Collection(Edm.Single)" and f.get("dimensions")]
            print(f"\n✅ Vector fields: {len(vector_fields)}")
            for vf in vector_fields:
                print(f"  - {vf['name']}: {vf['dimensions']} dimensions")
    else:
        print(f"❌ Failed to create index: {response.status_code}")
        print(response.text)
    
    print("\n✅ Index is ready for vector search!")
    print("\n🚀 Next steps:")
    print("1. Set OPENAI_API_KEY in .env for embeddings")
    print("2. Run: python reindex_with_embeddings.py")

if __name__ == "__main__":
    main()