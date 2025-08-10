#!/usr/bin/env python3
"""Direct test of Azure Search repository filtering"""

import asyncio
import os
import sys
import json

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_azure_search_directly():
    """Test Azure Search repository filter directly via REST API"""
    
    print("=" * 70)
    print("AZURE SEARCH REPOSITORY FILTER DIAGNOSTIC")
    print("=" * 70)
    
    # Import Azure Search components
    from enhanced_rag.azure_integration.config import AzureSearchConfig
    from enhanced_rag.azure_integration.rest.client import AzureSearchClient
    from enhanced_rag.azure_integration.rest.operations import SearchOperations
    
    # Initialize
    config = AzureSearchConfig.from_env()
    client = AzureSearchClient(config.endpoint, config.api_key)
    ops = SearchOperations(client)
    
    print(f"\nConfiguration:")
    print(f"  Endpoint: {config.endpoint}")
    print(f"  Index: {config.index_name}")
    
    # ============================================
    # TEST 1: Get Index Schema
    # ============================================
    print("\n" + "=" * 70)
    print("TEST 1: Check Index Schema for 'repository' Field")
    print("-" * 70)
    
    try:
        index_def = await ops.get_index(config.index_name)
        fields = index_def.get('fields', [])
        
        # Find repository field
        repo_field = None
        for field in fields:
            if field['name'] == 'repository':
                repo_field = field
                break
        
        if repo_field:
            print("✅ Repository field EXISTS in schema:")
            print(f"   Type: {repo_field.get('type', 'unknown')}")
            print(f"   Filterable: {repo_field.get('filterable', False)}")
            print(f"   Searchable: {repo_field.get('searchable', False)}")
            print(f"   Facetable: {repo_field.get('facetable', False)}")
            
            if not repo_field.get('filterable'):
                print("\n⚠️  WARNING: Field is NOT filterable! Filters will fail.")
        else:
            print("❌ Repository field NOT FOUND in schema!")
            print("\nOther fields in index:")
            for f in fields[:10]:
                print(f"   - {f['name']} ({f.get('type', 'unknown')})")
                
    except Exception as e:
        print(f"❌ Error getting index schema: {e}")
        return
    
    # ============================================
    # TEST 2: Check if Documents Have Repository Data
    # ============================================
    print("\n" + "=" * 70)
    print("TEST 2: Check if Documents Have Repository Values")
    print("-" * 70)
    
    try:
        # Get a sample of documents
        result = await ops.search(
            index_name=config.index_name,
            query="*",
            top=20,
            select="id,file_path,repository"
        )
        
        docs = result.get('value', [])
        total_count = result.get('@odata.count', len(docs))
        
        print(f"Sampled {len(docs)} documents (total in index: {total_count})")
        
        # Analyze repository values
        repos_found = {}
        empty_count = 0
        
        for doc in docs:
            repo = doc.get('repository', '')
            if repo:
                repos_found[repo] = repos_found.get(repo, 0) + 1
            else:
                empty_count += 1
        
        if repos_found:
            print(f"\n✅ Found {len(repos_found)} unique repository values:")
            for repo, count in list(repos_found.items())[:5]:
                print(f"   '{repo}': {count} documents")
        
        if empty_count > 0:
            print(f"\n⚠️  {empty_count}/{len(docs)} documents have EMPTY repository field")
            
        if not repos_found and empty_count == len(docs):
            print("\n❌ ALL sampled documents have EMPTY repository field!")
            print("   This means filtering by repository will return no results.")
            
    except Exception as e:
        print(f"❌ Error checking documents: {e}")
    
    # ============================================
    # TEST 3: Test Repository Filter
    # ============================================
    print("\n" + "=" * 70)
    print("TEST 3: Test Repository Filter Queries")
    print("-" * 70)
    
    # Try different filter syntaxes
    test_cases = [
        {
            "name": "Exact match (OData)",
            "filter": "repository eq 'mcprag'",
            "query": "def"
        },
        {
            "name": "Contains match",
            "filter": "search.ismatch('mcprag', 'repository')",
            "query": "def"
        },
        {
            "name": "Wildcard search with filter",
            "filter": "repository eq 'mcprag'",
            "query": "*"
        }
    ]
    
    for test in test_cases:
        print(f"\nTest: {test['name']}")
        print(f"  Filter: {test['filter']}")
        print(f"  Query: {test['query']}")
        
        try:
            result = await ops.search(
                index_name=config.index_name,
                query=test['query'],
                filter=test['filter'],
                top=5,
                select="id,file_path,repository"
            )
            
            docs = result.get('value', [])
            count = result.get('@odata.count', len(docs))
            
            if docs:
                print(f"  ✅ SUCCESS: Found {count} results")
                for i, doc in enumerate(docs[:2], 1):
                    print(f"     {i}. {doc.get('file_path', 'unknown')} (repo={doc.get('repository', 'EMPTY')})")
            else:
                print(f"  ⚠️  Query succeeded but returned 0 results")
                
        except Exception as e:
            error_str = str(e)
            if 'Invalid expression' in error_str:
                print(f"  ❌ SYNTAX ERROR: Invalid filter expression")
            elif 'not filterable' in error_str or 'cannot be used for filtering' in error_str:
                print(f"  ❌ FIELD ERROR: 'repository' field is not filterable")
            elif 'not found' in error_str:
                print(f"  ❌ FIELD ERROR: 'repository' field does not exist")
            else:
                print(f"  ❌ ERROR: {error_str[:150]}")
    
    # ============================================
    # TEST 4: Get Facets (if field is facetable)
    # ============================================
    if repo_field and repo_field.get('facetable'):
        print("\n" + "=" * 70)
        print("TEST 4: Get Repository Facets")
        print("-" * 70)
        
        try:
            result = await ops.search(
                index_name=config.index_name,
                query="*",
                facets=["repository"],
                top=0  # Don't need documents, just facets
            )
            
            facets = result.get('@search.facets', {})
            if 'repository' in facets:
                repo_facets = facets['repository']
                print(f"✅ Found {len(repo_facets)} unique repository values via facets:")
                for facet in repo_facets[:10]:
                    print(f"   '{facet['value']}': {facet['count']} documents")
            else:
                print("⚠️  No facet data returned")
                
        except Exception as e:
            print(f"❌ Error getting facets: {e}")
    
    # ============================================
    # FINAL DIAGNOSIS
    # ============================================
    print("\n" + "=" * 70)
    print("DIAGNOSIS")
    print("=" * 70)
    
    if not repo_field:
        print("\n❌ ROOT CAUSE: Repository field does not exist in index schema")
        print("\nSOLUTION:")
        print("1. Recreate the index with a 'repository' field")
        print("2. Make sure it's marked as 'filterable': true")
        print("3. Re-index all documents with repository values populated")
        
    elif not repo_field.get('filterable'):
        print("\n❌ ROOT CAUSE: Repository field exists but is NOT filterable")
        print("\nSOLUTION:")
        print("1. Update the field definition to set 'filterable': true")
        print("2. This may require recreating the index if Azure doesn't allow updates")
        print("3. Re-index documents after schema change")
        
    elif empty_count == len(docs):
        print("\n❌ ROOT CAUSE: Repository field exists and is filterable, but NO documents have it populated")
        print("\nSOLUTION:")
        print("1. Re-index documents with repository field populated")
        print("2. Check the indexing code to ensure it's setting the repository value")
        print("3. Verify FileProcessor.process_repository() is setting the field correctly")
        
    else:
        print("\n✅ Repository filtering should work!")
        print("If you're still having issues:")
        print("1. Check the exact filter syntax being used")
        print("2. Ensure the repository value matches exactly (case-sensitive)")
        print("3. Check for any special characters that need escaping")

if __name__ == "__main__":
    asyncio.run(test_azure_search_directly())