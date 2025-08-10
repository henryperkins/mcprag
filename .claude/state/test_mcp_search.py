#!/usr/bin/env python3
"""Test MCP search_code with repository filter"""

import asyncio
import sys
import os
import json

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def main():
    # Import after path is set
    from mcprag.mcp.tools._helpers import search_code_impl
    
    # Create a mock server object for testing
    class MockServer:
        def __init__(self):
            self.enhanced_search = True  # Assume component is available
            
    server = MockServer()
    
    print("Testing MCP search_code tool with repository filter")
    print("=" * 60)
    
    # Test 1: Without repository filter
    print("\n1. Search without repository filter:")
    try:
        result = await search_code_impl(
            server=server,
            query="def __init__",
            max_results=3,
            detail_level="compact"
        )
        
        if result.get("results"):
            print(f"   ✓ Found {len(result['results'])} results")
            for i, r in enumerate(result['results'][:2], 1):
                print(f"   Result {i}:")
                print(f"     - File: {r.get('file', 'unknown')}")
                print(f"     - Repository: {r.get('repository', 'NOT SET')}")
        else:
            print(f"   ⚠ No results found")
            
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test 2: With repository filter
    print("\n2. Search WITH repository filter (repository='mcprag'):")
    try:
        result = await search_code_impl(
            server=server,
            query="def __init__",
            repository="mcprag",
            max_results=3,
            detail_level="compact"
        )
        
        if result.get("results"):
            print(f"   ✓ Found {len(result['results'])} results with filter")
            for i, r in enumerate(result['results'][:2], 1):
                print(f"   Result {i}:")
                print(f"     - File: {r.get('file', 'unknown')}")
                print(f"     - Repository: {r.get('repository', 'NOT SET')}")
        elif "error" in result:
            print(f"   ✗ Error with filter: {result['error']}")
        else:
            print(f"   ⚠ No results found with filter")
            
    except Exception as e:
        print(f"   ✗ Error with filter: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 3: Check what's actually in the documents
    print("\n3. Checking document repository values:")
    try:
        # Do a wildcard search to get some documents
        result = await search_code_impl(
            server=server,
            query="*",
            max_results=10,
            detail_level="compact",
            bm25_only=True  # Use BM25 to avoid complexity
        )
        
        if result.get("results"):
            repos = set()
            empty_repos = 0
            for r in result['results']:
                repo = r.get('repository', '')
                if repo:
                    repos.add(repo)
                else:
                    empty_repos += 1
            
            print(f"   Found {len(repos)} unique repository values:")
            for repo in list(repos)[:5]:
                print(f"     - '{repo}'")
            
            if empty_repos:
                print(f"   ⚠ {empty_repos}/{len(result['results'])} documents have empty repository field")
                
    except Exception as e:
        print(f"   ✗ Error checking documents: {e}")
    
    print("\n" + "=" * 60)
    print("Summary:")
    print("-" * 60)
    print("If the repository filter fails, check:")
    print("1. Is the 'repository' field in the index schema?")
    print("2. Is the 'repository' field marked as filterable?")
    print("3. Are documents indexed with repository values?")
    print("4. Is the filter syntax correct in FilterManager?")

if __name__ == "__main__":
    asyncio.run(main())