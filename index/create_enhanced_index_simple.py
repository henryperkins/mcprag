#!/usr/bin/env python3
"""
Create enhanced Azure Search index - simplified version
"""

import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the current directory to Python path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import *
from azure.core.credentials import AzureKeyCredential

def create_simple_index():
    """Create a simple index to test connectivity"""
    
    endpoint = os.getenv("ACS_ENDPOINT")
    api_key = os.getenv("ACS_ADMIN_KEY")
    
    if not endpoint or not api_key:
        print("❌ Missing Azure Search credentials")
        return False
    
    print(f"Connecting to: {endpoint}")
    
    # Create index client
    index_client = SearchIndexClient(
        endpoint=endpoint,
        credential=AzureKeyCredential(api_key)
    )
    
    # Define simple fields first
    fields = [
        SimpleField(
            name="id",
            type=SearchFieldDataType.String,
            key=True
        ),
        SearchableField(
            name="content",
            type=SearchFieldDataType.String
        ),
        SimpleField(
            name="repository",
            type=SearchFieldDataType.String,
            filterable=True
        ),
        SimpleField(
            name="file_path",
            type=SearchFieldDataType.String,
            filterable=True
        ),
        SimpleField(
            name="language",
            type=SearchFieldDataType.String,
            filterable=True
        )
    ]
    
    # Create simple index
    index = SearchIndex(
        name="codebase-mcp-sota",
        fields=fields
    )
    
    try:
        result = index_client.create_or_update_index(index)
        print(f"✅ Created index: {result.name}")
        print(f"   Fields: {len(result.fields)}")
        return True
    except Exception as e:
        print(f"❌ Error creating index: {e}")
        return False

def create_enhanced_index():
    """Create the full enhanced index"""
    from enhanced_rag.azure_integration.enhanced_index_builder import EnhancedIndexBuilder
    
    try:
        print("\nCreating Enhanced RAG Index...")
        builder = EnhancedIndexBuilder()
        
        # Note: The create_enhanced_rag_index is async, but we'll call the underlying sync method
        # Build comprehensive field collection
        fields = builder._build_enhanced_fields()
        
        # Add vector search configuration
        vector_search = builder._build_vector_search_config()
        
        # Add semantic configuration
        semantic_search = builder._build_semantic_config()
        
        # Build scoring profiles
        scoring_profiles = builder._build_scoring_profiles()
        
        # Build suggesters
        suggesters = builder._build_suggesters()
        
        # Build analyzers
        analyzers = builder._build_code_analyzers()
        
        # Configure CORS for browser-based access
        cors_options = CorsOptions(
            allowed_origins=["*"],
            max_age_in_seconds=300
        )
        
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
            cors_options=cors_options
        )
        
        # Create or update
        result = builder.index_client.create_or_update_index(index)
        
        print(f"✅ Created enhanced index: {result.name}")
        print(f"   Total fields: {len(result.fields)}")
        print(f"   Vector search: {'Yes' if result.vector_search else 'No'}")
        print(f"   Semantic search: {'Yes' if result.semantic_search else 'No'}")
        print(f"   Scoring profiles: {len(result.scoring_profiles or [])}")
        
        # Validate
        validation = builder.index_client.get_index("codebase-mcp-sota")
        if validation:
            print("✅ Index validation passed")
            
        return True
        
    except Exception as e:
        print(f"❌ Error creating enhanced index: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Enhanced RAG Index Creator")
    print("=" * 50)
    
    # Try simple index first
    print("\n1. Testing with simple index...")
    if create_simple_index():
        print("\n2. Creating enhanced index...")
        create_enhanced_index()
    else:
        print("\n❌ Failed to create simple index. Check your credentials.")