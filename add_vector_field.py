#!/usr/bin/env python3
"""
Add the missing content_vector field to the existing codebase-mcp-sota index
"""

import asyncio
from enhanced_rag.azure_integration.index_operations import IndexOperations
from azure.search.documents.indexes.models import (
    SearchField,
    SearchFieldDataType,
    VectorSearch,
    VectorSearchProfile,
    HnswAlgorithmConfiguration,
    VectorSearchAlgorithmKind,
    VectorSearchAlgorithmMetric
)


async def add_vector_field_to_index():
    """Add the content_vector field to the existing index"""
    
    index_ops = IndexOperations()
    
    try:
        # Get the current index
        print("📊 Getting current index schema...")
        current_index = await index_ops._run_in_executor(
            index_ops.client.get_index, "codebase-mcp-sota"
        )
        
        print(f"✅ Current index has {len(current_index.fields)} fields")
        
        # Check if content_vector field already exists
        vector_field_exists = any(field.name == "content_vector" for field in current_index.fields)
        
        if vector_field_exists:
            print("✅ content_vector field already exists!")
            return True
        
        print("➕ Adding content_vector field...")
        
        # Create the vector field
        vector_field = SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=3072,
            vector_search_profile_name="vector-profile"
        )
        
        # Add the field to the existing fields
        current_index.fields.append(vector_field)
        
        # Create vector search configuration if it doesn't exist
        if not current_index.vector_search:
            print("➕ Adding vector search configuration...")
            current_index.vector_search = VectorSearch(
                profiles=[
                    VectorSearchProfile(
                        name="vector-profile",
                        algorithm_configuration_name="vector-config"
                    )
                ],
                algorithms=[
                    HnswAlgorithmConfiguration(
                        name="vector-config",
                        kind=VectorSearchAlgorithmKind.HNSW,
                        parameters={
                            "m": 4,
                            "efConstruction": 400,
                            "efSearch": 500,
                            "metric": VectorSearchAlgorithmMetric.COSINE
                        }
                    )
                ]
            )
        
        # Update the index
        print("🔄 Updating index schema...")
        await index_ops._run_in_executor(
            index_ops.client.create_or_update_index, current_index
        )
        
        print("✅ Successfully added content_vector field to index!")
        print(f"📊 Index now has {len(current_index.fields)} fields")
        
        return True
        
    except Exception as e:
        print(f"❌ Error adding vector field: {e}")
        return False
    finally:
        await index_ops.close()


async def verify_vector_field():
    """Verify the vector field was added correctly"""
    
    index_ops = IndexOperations()
    
    try:
        print("\n🔍 Verifying vector field...")
        
        # Get the updated index
        updated_index = await index_ops._run_in_executor(
            index_ops.client.get_index, "codebase-mcp-sota"
        )
        
        # Find the vector field
        vector_field = next(
            (field for field in updated_index.fields if field.name == "content_vector"), 
            None
        )
        
        if vector_field:
            print("✅ content_vector field found!")
            print(f"   Type: {vector_field.type}")
            print(f"   Dimensions: {vector_field.vector_search_dimensions}")
            print(f"   Profile: {vector_field.vector_search_profile_name}")
            print(f"   Searchable: {vector_field.searchable}")
        else:
            print("❌ content_vector field not found!")
            return False
        
        # Check vector search configuration
        if updated_index.vector_search:
            print("✅ Vector search configuration found!")
            print(f"   Profiles: {len(updated_index.vector_search.profiles)}")
            print(f"   Algorithms: {len(updated_index.vector_search.algorithms)}")
        else:
            print("❌ Vector search configuration missing!")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error verifying vector field: {e}")
        return False
    finally:
        await index_ops.close()


if __name__ == "__main__":
    print("🔧 Adding Vector Field to Existing Index")
    print("=" * 45)
    
    # Add the vector field
    success = asyncio.run(add_vector_field_to_index())
    
    if success:
        # Verify it was added correctly
        asyncio.run(verify_vector_field())
        
        print("\n🎉 Vector field addition complete!")
        print("\n📋 Next steps:")
        print("1. ✅ Index now has content_vector field")
        print("2. 🔄 Your indexer should now work without the field mapping error")
        print("3. ▶️  Try running your indexer again")
    else:
        print("\n❌ Failed to add vector field")
        print("   Please check the error messages above")
