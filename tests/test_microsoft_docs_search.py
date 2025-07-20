"""Test script for Microsoft Docs MCP integration"""

import asyncio
import json
from microsoft_docs_mcp_client import MicrosoftDocsMCPClient


async def test_direct_client():
    """Test the Microsoft Docs MCP client directly"""
    print("=== Testing Direct Microsoft Docs MCP Client ===\n")
    
    async with MicrosoftDocsMCPClient() as client:
        # Test 1: Search for Azure Cognitive Search
        print("Test 1: Searching for 'Azure Cognitive Search vector search'")
        results = await client.search_docs("Azure Cognitive Search vector search")
        print(f"Found {len(results)} results")
        if results:
            print(f"First result: {results[0]['title']}")
            print(f"Content preview: {results[0]['content'][:200]}...\n")
        
        # Test 2: Search for MCP documentation
        print("Test 2: Searching for 'Model Context Protocol MCP'")
        results = await client.search_docs("Model Context Protocol MCP")
        print(f"Found {len(results)} results")
        if results:
            print(f"First result: {results[0]['title']}\n")
            
        # Test 3: Search with context
        print("Test 3: Searching with context for Python Azure SDK")
        result_with_context = await client.search_with_context(
            "Azure SDK",
            context={"language": "Python", "framework": "asyncio"}
        )
        print(f"Enhanced query: {result_with_context['enhanced_query']}")
        print(f"Found {result_with_context['result_count']} results\n")


async def test_mcp_server_integration():
    """Test the MCP server integration"""
    print("=== Testing MCP Server Integration ===\n")
    
    # Simulate MCP protocol requests
    from mcp_server_sota import MCPServer
    
    server = MCPServer()
    
    # Test listing tools
    list_request = {
        "jsonrpc": "2.0",
        "method": "tools/list",
        "id": 1
    }
    
    response = await server.handle_request(list_request)
    tools = response.get("result", {}).get("tools", [])
    print(f"Available tools: {[t['name'] for t in tools]}")
    
    # Check if Microsoft Docs tool is available
    has_ms_docs = any(t['name'] == 'search_microsoft_docs' for t in tools)
    print(f"Microsoft Docs search available: {has_ms_docs}\n")
    
    if has_ms_docs:
        # Test Microsoft Docs search through MCP
        search_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "search_microsoft_docs",
                "arguments": {
                    "query": "Azure Cognitive Search semantic ranking",
                    "max_results": 5
                }
            },
            "id": 2
        }
        
        print("Testing Microsoft Docs search through MCP server...")
        response = await server.handle_request(search_request)
        
        if "result" in response:
            content = response["result"]["content"][0]["text"]
            print("Search results:")
            print(content[:500] + "..." if len(content) > 500 else content)
        else:
            print(f"Error: {response.get('error', 'Unknown error')}")


async def main():
    """Run all tests"""
    print("Microsoft Docs MCP Integration Test Suite\n")
    print("=" * 50 + "\n")
    
    try:
        # Test direct client
        await test_direct_client()
        
        print("\n" + "=" * 50 + "\n")
        
        # Test MCP server integration
        await test_mcp_server_integration()
        
    except Exception as e:
        print(f"\nError during testing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())