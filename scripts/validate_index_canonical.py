#!/usr/bin/env python3
"""
Validate index against canonical MCP schema requirements
"""
import os
import sys
import asyncio
from dotenv import load_dotenv
from enhanced_rag.azure_integration.enhanced_index_builder import EnhancedIndexBuilder
from enhanced_rag.core.config import EmbeddingConfig

# Load environment
load_dotenv()

# Required canonical fields
CANONICAL_FIELDS = ["content", "function_name", "repository", "language", "content_vector"]
EXPECTED_VECTOR_DIMENSIONS = EmbeddingConfig().dimensions  # Should be 3072

async def validate_canonical_index():
    """Validate the index meets all canonical requirements"""
    index_name = os.getenv("ACS_INDEX_NAME", "codebase-mcp-sota")
    
    print(f"🔍 Validating index: {index_name}")
    print(f"   Expected vector dimensions: {EXPECTED_VECTOR_DIMENSIONS}")
    print(f"   Required fields: {', '.join(CANONICAL_FIELDS)}")
    print()
    
    builder = EnhancedIndexBuilder()
    
    # Check 1: Schema validation
    print("1️⃣ Validating schema fields...")
    schema_validation = await builder.validate_index_schema(
        index_name,
        CANONICAL_FIELDS
    )
    
    if schema_validation['valid']:
        print("✅ Schema validation PASSED")
        print(f"   Total fields: {schema_validation['total_fields']}")
        print(f"   Has vector search: {schema_validation['has_vector_search']}")
        print(f"   Has semantic search: {schema_validation['has_semantic_search']}")
        print(f"   Scoring profiles: {', '.join(schema_validation['scoring_profiles'])}")
    else:
        print("❌ Schema validation FAILED")
        print(f"   Missing fields: {schema_validation['missing_fields']}")
        return False
    
    # Check 2: Vector dimensions
    print("\n2️⃣ Validating vector dimensions...")
    vector_validation = await builder.validate_vector_dimensions(
        index_name,
        expected=EXPECTED_VECTOR_DIMENSIONS
    )
    
    if vector_validation['ok']:
        print("✅ Vector dimension validation PASSED")
        print(f"   Content vector dimensions: {vector_validation['actual']}")
        print(f"   Message: {vector_validation['message']}")
    else:
        print("❌ Vector dimension validation FAILED")
        print(f"   Expected: {vector_validation['expected']}")
        print(f"   Actual: {vector_validation['actual']}")
        print(f"   Message: {vector_validation['message']}")
    
    # Check 3: Semantic configuration
    print("\n3️⃣ Checking semantic configuration...")
    if schema_validation.get('has_semantic_search'):
        # Get detailed semantic info via REST API
        import requests
        
        endpoint = os.getenv("ACS_ENDPOINT")
        admin_key = os.getenv("ACS_ADMIN_KEY")
        api_version = "2024-05-01-preview"
        url = f"{endpoint}/indexes/{index_name}?api-version={api_version}"
        headers = {
            "Content-Type": "application/json",
            "api-key": admin_key
        }
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            index_def = response.json()
            semantic_configs = []
            if 'semantic' in index_def and 'configurations' in index_def['semantic']:
                semantic_configs = [cfg['name'] for cfg in index_def['semantic']['configurations']]
            
            if 'semantic-config' in semantic_configs:
                print("✅ Found expected 'semantic-config'")
            else:
                print(f"⚠️  Semantic configs found: {', '.join(semantic_configs) if semantic_configs else 'None'}")
                print("   Expected: semantic-config")
    
    # Summary
    print("\n" + "="*50)
    all_valid = schema_validation['valid'] and vector_validation['ok']
    if all_valid:
        print("✅ ALL VALIDATIONS PASSED")
        print(f"Index '{index_name}' is properly configured for MCP")
    else:
        print("❌ VALIDATION FAILED")
        print("Please recreate the index using: python index/create_enhanced_index.py")
    
    return all_valid

async def main():
    try:
        success = await validate_canonical_index()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Error during validation: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())