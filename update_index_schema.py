#!/usr/bin/env python3
"""
Update the existing index schema to add the content_vector field via REST API
"""

import json
import requests
from enhanced_rag.core.config import get_config


def get_current_index_schema():
    """Get the current index schema"""
    config = get_config()
    
    url = f"{config.azure.endpoint}/indexes/codebase-mcp-sota?api-version=2025-05-01-preview"
    headers = {
        "api-key": config.azure.admin_key,
        "Content-Type": "application/json"
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ Failed to get index schema: {response.status_code}")
        print(f"   Error: {response.text}")
        return None


def update_index_with_vector_field():
    """Update the index to include the content_vector field"""
    
    print("📊 Getting current index schema...")
    current_schema = get_current_index_schema()
    
    if not current_schema:
        return False
    
    # Check if content_vector field already exists
    vector_field_exists = any(field["name"] == "content_vector" for field in current_schema["fields"])
    
    if vector_field_exists:
        print("✅ content_vector field already exists!")
        return True
    
    print("➕ Adding content_vector field to schema...")
    
    # Add the vector field
    vector_field = {
        "name": "content_vector",
        "type": "Collection(Edm.Single)",
        "searchable": True,
        "filterable": False,
        "retrievable": True,
        "stored": True,
        "sortable": False,
        "facetable": False,
        "key": False,
        "dimensions": 3072,
        "vectorSearchProfile": "vector-profile"
    }
    
    current_schema["fields"].append(vector_field)
    
    # Add vector search configuration if it doesn't exist
    if "vectorSearch" not in current_schema:
        print("➕ Adding vector search configuration...")
        current_schema["vectorSearch"] = {
            "profiles": [
                {
                    "name": "vector-profile",
                    "algorithmConfigurationName": "vector-config"
                }
            ],
            "algorithms": [
                {
                    "name": "vector-config",
                    "kind": "hnsw",
                    "hnswParameters": {
                        "m": 4,
                        "efConstruction": 400,
                        "efSearch": 500,
                        "metric": "cosine"
                    }
                }
            ]
        }
    
    # Update the index
    config = get_config()
    url = f"{config.azure.endpoint}/indexes/codebase-mcp-sota?api-version=2025-05-01-preview"
    headers = {
        "api-key": config.azure.admin_key,
        "Content-Type": "application/json"
    }
    
    print("🔄 Updating index schema...")
    response = requests.put(url, headers=headers, json=current_schema)
    
    if response.status_code in [200, 201]:
        print("✅ Successfully updated index schema!")
        return True
    else:
        print(f"❌ Failed to update index: {response.status_code}")
        print(f"   Error: {response.text}")
        return False


def verify_updated_schema():
    """Verify the schema was updated correctly"""
    
    print("\n🔍 Verifying updated schema...")
    updated_schema = get_current_index_schema()
    
    if not updated_schema:
        return False
    
    # Check for vector field
    vector_field = next(
        (field for field in updated_schema["fields"] if field["name"] == "content_vector"), 
        None
    )
    
    if vector_field:
        print("✅ content_vector field found!")
        print(f"   Type: {vector_field['type']}")
        print(f"   Dimensions: {vector_field.get('dimensions', 'N/A')}")
        print(f"   Vector Profile: {vector_field.get('vectorSearchProfile', 'N/A')}")
    else:
        print("❌ content_vector field not found!")
        return False
    
    # Check vector search config
    if "vectorSearch" in updated_schema:
        print("✅ Vector search configuration found!")
        profiles = updated_schema["vectorSearch"].get("profiles", [])
        algorithms = updated_schema["vectorSearch"].get("algorithms", [])
        print(f"   Profiles: {len(profiles)}")
        print(f"   Algorithms: {len(algorithms)}")
    else:
        print("❌ Vector search configuration missing!")
        return False
    
    return True


if __name__ == "__main__":
    print("🔧 Updating Index Schema for Vector Search")
    print("=" * 45)
    
    try:
        # Update the index
        success = update_index_with_vector_field()
        
        if success:
            # Verify the update
            verify_success = verify_updated_schema()
            
            if verify_success:
                print("\n🎉 Index schema update complete!")
                print("\n📋 What was added:")
                print("✅ content_vector field (3072 dimensions)")
                print("✅ Vector search configuration (HNSW algorithm)")
                print("✅ Vector search profile (vector-profile)")
                
                print("\n📋 Next steps:")
                print("1. Your indexer should now work without field mapping errors")
                print("2. Run your indexer to start processing documents")
                print("3. Vector embeddings will be stored in content_vector field")
            else:
                print("\n⚠️  Update completed but verification failed")
        else:
            print("\n❌ Failed to update index schema")
            
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
