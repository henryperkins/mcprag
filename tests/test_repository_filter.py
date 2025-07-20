#!/usr/bin/env python3
"""Test script for repository filtering functionality."""

import asyncio
import json
import os
from pathlib import Path
from mcp_server_sota import MCPServer
from dotenv import load_dotenv

load_dotenv()

async def test_repository_filtering():
    """Test the repository filtering functionality."""
    server = MCPServer()
    
    print("🧪 Testing Repository Filtering\n")
    
    # Test 1: Auto-detect current repository
    print("1️⃣ Testing auto-detection of current repository:")
    current_repo = server.detect_current_repository()
    print(f"   Current repository detected: {current_repo}")
    
    # Test 2: Search with auto-detected repository
    print("\n2️⃣ Testing search with auto-detected repository:")
    results = await server.search_code_enhanced(
        query="function",
        repository=None  # Should auto-detect
    )
    print(f"   Found {len(results)} results")
    if results:
        print(f"   First result from repo: {results[0].get('repo_name')}")
    
    # Test 3: Search specific repository
    print("\n3️⃣ Testing search with specific repository:")
    results = await server.search_code_enhanced(
        query="function",
        repository="example-project"
    )
    print(f"   Found {len(results)} results in example-project")
    
    # Test 4: Search all repositories
    print("\n4️⃣ Testing search across all repositories:")
    results = await server.search_code_enhanced(
        query="function",
        repository="*"
    )
    print(f"   Found {len(results)} results across all repos")
    
    # Test 5: Search with repository and language filter
    print("\n5️⃣ Testing search with repository + language filter:")
    results = await server.search_code_enhanced(
        query="class",
        repository="example-project",
        language="python"
    )
    print(f"   Found {len(results)} Python classes in example-project")
    
    # Test 6: MCP protocol test
    print("\n6️⃣ Testing MCP protocol with repository parameter:")
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "search_code",
            "arguments": {
                "query": "import",
                "repository": "example-project"
            }
        }
    }
    
    response = await server.handle_request(request)
    if "result" in response:
        content = response["result"]["content"][0]["text"]
        print(f"   MCP response received (truncated): {content[:200]}...")
    else:
        print(f"   Error: {response}")

if __name__ == "__main__":
    asyncio.run(test_repository_filtering())