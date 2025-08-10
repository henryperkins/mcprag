#!/usr/bin/env python3
"""Test script to diagnose repository filtering issue in Azure Search"""

import asyncio
import os
import json
from typing import Optional

# Set up environment
os.environ['MCP_LOG_LEVEL'] = 'INFO'

async def test_repository_filter():
    """Test repository filtering directly using the Azure Search REST API"""
    
    print("=" * 60)
    print("Repository Filtering Diagnostic Test")
    print("=" * 60)
    
    # Load configuration
    from enhanced_rag.azure_integration.config import AzureSearchConfig
    from enhanced_rag.azure_integration.rest.client import AzureSearchClient
    from enhanced_rag.azure_integration.rest.operations import SearchOperations
    
    config = AzureSearchConfig.from_env()
    print(f"\n1. Configuration:")
    print(f"   - Endpoint: {config.endpoint}")
    print(f"   - Index: {config.index_name}")
    
    # Initialize REST client
    client = AzureSearchClient(config.endpoint, config.api_key)
    ops = SearchOperations(client)
    
    # Test 1: Check if index exists and get schema
    print("\n2. Checking index schema...")
    try:
        index_info = await ops.get_index(config.index_name)
        
        # Look for repository field
        repository_field = None
        for field in index_info.get('fields', []):
            if field['name'] == 'repository':
                repository_field = field
                break
        
        if repository_field:
            print(f"   ✓ Repository field exists in schema")
            print(f"     - Type: {repository_field.get('type')}")
            print(f"     - Filterable: {repository_field.get('filterable', False)}")
            print(f"     - Facetable: {repository_field.get('facetable', False)}")
            print(f"     - Searchable: {repository_field.get('searchable', False)}")
        else:
            print(f"   ✗ Repository field NOT found in schema!")
            print(f"   Available fields: {[f['name'] for f in index_info.get('fields', [])][:10]}...")
            
    except Exception as e:
        print(f"   ✗ Error getting index schema: {e}")
        return
    
    # Test 2: Query without filter to check if documents have repository field
    print("\n3. Checking if documents have repository field populated...")
    try:
        # Simple search without filter
        results = await ops.search(
            index_name=config.index_name,
            query="*",
            top=5,
            select="id,file_path,repository"
        )
        
        docs = results.get('value', [])
        if docs:
            print(f"   Found {len(docs)} documents")
            for i, doc in enumerate(docs[:3], 1):
                repo = doc.get('repository', 'NOT SET')
                path = doc.get('file_path', 'unknown')
                print(f"   Doc {i}: repository='{repo}', path='{path}'")
                
            # Check if any have repository field populated
            docs_with_repo = [d for d in docs if d.get('repository')]
            if docs_with_repo:
                print(f"   ✓ {len(docs_with_repo)}/{len(docs)} documents have repository field populated")
            else:
                print(f"   ✗ No documents have repository field populated!")
        else:
            print(f"   ✗ No documents found in index!")
            
    except Exception as e:
        print(f"   ✗ Error querying documents: {e}")
    
    # Test 3: Try filtering with repository field
    print("\n4. Testing repository filter...")
    test_filters = [
        ("repository eq 'mcprag'", "Exact match filter"),
        ("search.ismatch('mcprag', 'repository')", "Search.ismatch filter"),
        ("repository eq '*'", "Wildcard filter (should fail)"),
    ]
    
    for filter_expr, description in test_filters:
        print(f"\n   Testing: {description}")
        print(f"   Filter: {filter_expr}")
        try:
            results = await ops.search(
                index_name=config.index_name,
                query="def",
                filter=filter_expr,
                top=3,
                select="id,file_path,repository"
            )
            
            docs = results.get('value', [])
            if docs:
                print(f"   ✓ Filter succeeded! Found {len(docs)} results")
                for doc in docs[:2]:
                    print(f"     - {doc.get('file_path', 'unknown')} (repo={doc.get('repository', 'NOT SET')})")
            else:
                print(f"   ⚠ Filter succeeded but returned 0 results")
                
        except Exception as e:
            error_msg = str(e)
            if 'Invalid expression' in error_msg or 'not filterable' in error_msg:
                print(f"   ✗ Filter failed: Field not filterable or invalid syntax")
            else:
                print(f"   ✗ Filter failed: {error_msg[:200]}")
    
    # Test 4: Check facets to see unique repository values
    if repository_field and repository_field.get('facetable'):
        print("\n5. Checking unique repository values via facets...")
        try:
            results = await ops.search(
                index_name=config.index_name,
                query="*",
                facets=["repository"],
                top=0  # Don't need actual results, just facets
            )
            
            facets = results.get('@search.facets', {})
            if 'repository' in facets:
                repo_facets = facets['repository']
                print(f"   Found {len(repo_facets)} unique repository values:")
                for facet in repo_facets[:5]:
                    print(f"     - '{facet['value']}': {facet['count']} documents")
            else:
                print(f"   ✗ No facet data returned for repository field")
                
        except Exception as e:
            print(f"   ✗ Error getting facets: {e}")
    
    print("\n" + "=" * 60)
    print("Diagnostic Summary:")
    print("-" * 60)
    
    if not repository_field:
        print("❌ ISSUE: Repository field does not exist in the index schema")
        print("   SOLUTION: Recreate index with repository field, or add field if possible")
    elif not repository_field.get('filterable'):
        print("❌ ISSUE: Repository field exists but is not filterable")
        print("   SOLUTION: Update field definition to make it filterable")
    elif not docs_with_repo:
        print("❌ ISSUE: Repository field exists but is not populated in documents")
        print("   SOLUTION: Re-index documents with repository field populated")
    else:
        print("✓ Repository field exists, is filterable, and has data")
        print("  The filter should work. Check filter syntax if still having issues.")
    
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_repository_filter())