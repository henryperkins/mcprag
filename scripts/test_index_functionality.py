#!/usr/bin/env python3
"""
Acceptance tests for Azure Search index functionality
"""
import os
import sys
import asyncio
from dotenv import load_dotenv
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

# Load environment
load_dotenv()

async def test_index_functionality():
    """Run acceptance tests for index functionality"""
    endpoint = os.getenv("ACS_ENDPOINT")
    admin_key = os.getenv("ACS_ADMIN_KEY")
    index_name = os.getenv("ACS_INDEX_NAME", "codebase-mcp-sota")
    
    if not endpoint or not admin_key:
        print("❌ Missing Azure Search credentials")
        return False
    
    # Create search client
    search_client = SearchClient(
        endpoint=endpoint,
        index_name=index_name,
        credential=AzureKeyCredential(admin_key)
    )
    
    print(f"🧪 Running acceptance tests for index: {index_name}")
    print()
    
    all_tests_passed = True
    
    # Test 1: Basic search
    print("1️⃣ Testing basic keyword search...")
    try:
        results = search_client.search(
            search_text="function",
            select=["content", "function_name", "repository"],
            top=5
        )
        
        count = 0
        for result in results:
            count += 1
        
        if count > 0:
            print(f"✅ Basic search returned {count} results")
        else:
            print("⚠️  Basic search returned no results")
    except Exception as e:
        print(f"❌ Basic search failed: {e}")
        all_tests_passed = False
    
    # Test 2: Vector search (if documents have vectors)
    print("\n2️⃣ Testing vector search...")
    try:
        # Create a dummy vector with correct dimensions (3072)
        dummy_vector = [0.1] * 3072
        
        from azure.search.documents.models import VectorizedQuery
        
        vector_query = VectorizedQuery(
            vector=dummy_vector,
            k_nearest_neighbors=5,
            fields="content_vector"
        )
        
        results = search_client.search(
            search_text="",
            vector_queries=[vector_query],
            select=["content", "function_name", "repository"],
            top=5
        )
        
        count = 0
        for result in results:
            count += 1
        
        if count > 0:
            print(f"✅ Vector search returned {count} results")
        else:
            print("⚠️  Vector search returned no results (may need to index documents with vectors)")
    except Exception as e:
        print(f"❌ Vector search failed: {e}")
        all_tests_passed = False
    
    # Test 3: Semantic search
    print("\n3️⃣ Testing semantic search...")
    try:
        results = search_client.search(
            search_text="how to create an index",
            query_type="semantic",
            semantic_configuration_name="semantic-config",
            select=["content", "function_name", "repository"],
            top=5
        )
        
        count = 0
        has_captions = False
        for result in results:
            count += 1
            if hasattr(result, '@search.captions') and result['@search.captions']:
                has_captions = True
        
        if count > 0:
            print(f"✅ Semantic search returned {count} results")
            if has_captions:
                print("   ✅ Results include semantic captions")
        else:
            print("⚠️  Semantic search returned no results")
    except Exception as e:
        print(f"❌ Semantic search failed: {e}")
        all_tests_passed = False
    
    # Test 4: Filtering
    print("\n4️⃣ Testing filtered search...")
    try:
        results = search_client.search(
            search_text="*",
            filter="language eq 'python'",
            select=["content", "function_name", "language"],
            top=5
        )
        
        count = 0
        for result in results:
            count += 1
            if result.get('language') != 'python':
                print(f"❌ Filter violation: got language={result.get('language')}")
                all_tests_passed = False
        
        if count > 0:
            print(f"✅ Filtered search returned {count} Python results")
        else:
            print("⚠️  Filtered search returned no results")
    except Exception as e:
        print(f"❌ Filtered search failed: {e}")
        all_tests_passed = False
    
    # Test 5: Faceted search
    print("\n5️⃣ Testing faceted search...")
    try:
        results = search_client.search(
            search_text="*",
            facets=["language,count:5", "repository,count:5"],
            top=1
        )
        
        # Consume results to get facets
        list(results)
        
        facets = results.get_facets()
        if facets:
            print("✅ Faceted search returned facets:")
            for facet_name, facet_values in facets.items():
                print(f"   {facet_name}: {len(facet_values)} values")
        else:
            print("⚠️  No facets returned")
    except Exception as e:
        print(f"❌ Faceted search failed: {e}")
        all_tests_passed = False
    
    # Test 6: Scoring profiles
    print("\n6️⃣ Testing scoring profiles...")
    try:
        results = search_client.search(
            search_text="function",
            scoring_profile="code_quality_boost",
            select=["content", "function_name"],
            top=5
        )
        
        count = 0
        for result in results:
            count += 1
        
        if count > 0:
            print(f"✅ Search with scoring profile returned {count} results")
        else:
            print("⚠️  Search with scoring profile returned no results")
    except Exception as e:
        print(f"❌ Search with scoring profile failed: {e}")
        all_tests_passed = False
    
    # Summary
    print("\n" + "="*50)
    if all_tests_passed:
        print("✅ ALL ACCEPTANCE TESTS PASSED")
        print(f"Index '{index_name}' is fully functional")
    else:
        print("❌ SOME TESTS FAILED")
        print("Please check the index configuration and data")
    
    return all_tests_passed

async def main():
    try:
        success = await test_index_functionality()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())