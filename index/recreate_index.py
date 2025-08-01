#!/usr/bin/env python3
"""
Delete old index and create new one with canonical schema
"""

import os
import sys
from dotenv import load_dotenv
from azure.search.documents.indexes import SearchIndexClient
from azure.core.credentials import AzureKeyCredential

# Load environment variables
load_dotenv()

def delete_index(index_name):
    """Delete an existing index"""
    endpoint = os.getenv("ACS_ENDPOINT")
    api_key = os.getenv("ACS_ADMIN_KEY")
    
    index_client = SearchIndexClient(
        endpoint=endpoint,
        credential=AzureKeyCredential(api_key)
    )
    
    try:
        index_client.delete_index(index_name)
        print(f"✅ Deleted index: {index_name}")
        return True
    except Exception as e:
        print(f"❌ Error deleting index: {e}")
        return False

def create_new_index():
    """Create the new index with canonical schema"""
    # Import after path setup
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from enhanced_rag.azure_integration.enhanced_index_builder import EnhancedIndexBuilder
    
    try:
        builder = EnhancedIndexBuilder()
        
        # Build all components
        fields = builder._build_enhanced_fields()
        vector_search = builder._build_vector_search_config()
        semantic_search = builder._build_semantic_config()
        scoring_profiles = builder._build_scoring_profiles()
        suggesters = builder._build_suggesters()
        analyzers = builder._build_code_analyzers()
        
        from azure.search.documents.indexes.models import SearchIndex, CorsOptions
        
        # Create the index
        index = SearchIndex(
            name="codebase-mcp-sota",
            fields=fields,
            vector_search=vector_search,
            semantic_search=semantic_search,
            scoring_profiles=scoring_profiles,
            default_scoring_profile="code_quality_boost",
            suggesters=suggesters,
            analyzers=analyzers,
            cors_options=CorsOptions(allowed_origins=["*"], max_age_in_seconds=300)
        )
        
        # Create it
        result = builder.index_client.create_or_update_index(index)
        
        print(f"✅ Created enhanced index: {result.name}")
        print(f"   Total fields: {len(result.fields)}")
        print(f"   Key fields: id, content, repository, file_path, function_name")
        print(f"   Vector search: Enabled")
        print(f"   Semantic search: Enabled")
        print(f"   Scoring profiles: {', '.join([p.name for p in result.scoring_profiles])}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating index: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Index Recreation Tool")
    print("=" * 50)
    
    # Auto-confirm for automation
    print("\n⚠️  This will DELETE the existing index and all its data.")
    print("Proceeding with recreation...")
    
    if True:  # Auto-confirm
        print("\n1. Deleting old index...")
        if delete_index("codebase-mcp-sota"):
            print("\n2. Creating new index with canonical schema...")
            if create_new_index():
                print("\n✅ Successfully recreated index with new schema!")
                print("\nNext steps:")
                print("1. Run: python smart_indexer.py --repo-path . --repo-name mcprag")
                print("2. Start MCP server: python mcp_server_sota.py")
            else:
                print("\n❌ Failed to create new index")
        else:
            print("\n❌ Failed to delete old index")
    else:
        print("\nCancelled. No changes made.")