#!/usr/bin/env python3
"""
Simple script to add the content_vector field to the existing index
Uses direct environment variable access to avoid import issues
"""

import os
import json
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def get_env_config():
    """Get configuration from environment variables"""
    endpoint = os.getenv("ACS_ENDPOINT", "")
    admin_key = os.getenv("ACS_ADMIN_KEY", "")
    
    if not endpoint:
        raise ValueError("ACS_ENDPOINT environment variable is required")
    if not admin_key:
        raise ValueError("ACS_ADMIN_KEY environment variable is required")
    
    return endpoint, admin_key


def get_current_index_schema(endpoint, admin_key):
    """Get the current index schema"""
    url = f"{endpoint}/indexes/codebase-mcp-sota?api-version=2025-05-01-preview"
    headers = {
        "api-key": admin_key,
        "Content-Type": "application/json"
    }
    
    print(f"🔍 Getting index schema from: {url}")
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ Failed to get index schema: {response.status_code}")
        print(f"   Error: {response.text}")
        return None


def add_vector_field_to_schema(schema):
    """Add the content_vector field to the schema"""
    
    # Check if content_vector field already exists
    vector_field_exists = any(field["name"] == "content_vector" for field in schema["fields"])
    
    if vector_field_exists:
        print("✅ content_vector field already exists!")
        return schema, False
    
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
    
    schema["fields"].append(vector_field)
    
    # Add vector search configuration if it doesn't exist
    if "vectorSearch" not in schema:
        print("➕ Adding vector search configuration...")
        schema["vectorSearch"] = {
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
    
    return schema, True


def update_index_schema(endpoint, admin_key, schema):
    """Update the index with the new schema"""
    url = f"{endpoint}/indexes/codebase-mcp-sota?api-version=2025-05-01-preview"
    headers = {
        "api-key": admin_key,
        "Content-Type": "application/json"
    }
    
    print("🔄 Updating index schema...")
    response = requests.put(url, headers=headers, json=schema)
    
    if response.status_code in [200, 201]:
        print("✅ Successfully updated index schema!")
        return True
    else:
        print(f"❌ Failed to update index: {response.status_code}")
        print(f"   Error: {response.text}")
        return False


def verify_vector_field(endpoint, admin_key):
    """Verify the vector field was added correctly"""
    print("\n🔍 Verifying vector field...")
    
    updated_schema = get_current_index_schema(endpoint, admin_key)
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


def main():
    """Main function to add vector field to index"""
    print("🔧 Adding Vector Field to Azure Cognitive Search Index")
    print("=" * 55)
    
    try:
        # Get configuration
        endpoint, admin_key = get_env_config()
        print(f"📊 Azure Search Endpoint: {endpoint}")
        
        # Get current schema
        current_schema = get_current_index_schema(endpoint, admin_key)
        if not current_schema:
            return False
        
        print(f"📋 Current index has {len(current_schema['fields'])} fields")
        
        # Add vector field
        updated_schema, was_modified = add_vector_field_to_schema(current_schema)
        
        if not was_modified:
            print("ℹ️  No changes needed - vector field already exists")
            return True
        
        # Update the index
        success = update_index_schema(endpoint, admin_key, updated_schema)
        
        if success:
            # Verify the update
            verify_success = verify_vector_field(endpoint, admin_key)
            
            if verify_success:
                print("\n🎉 Vector field addition complete!")
                print("\n📋 What was added:")
                print("✅ content_vector field (3072 dimensions)")
                print("✅ Vector search configuration (HNSW algorithm)")
                print("✅ Vector search profile (vector-profile)")
                
                print("\n📋 Next steps:")
                print("1. Your indexer should now work without field mapping errors")
                print("2. Run your indexer to start processing documents")
                print("3. Vector embeddings will be stored in content_vector field")
                return True
            else:
                print("\n⚠️  Update completed but verification failed")
                return False
        else:
            print("\n❌ Failed to update index schema")
            return False
            
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
