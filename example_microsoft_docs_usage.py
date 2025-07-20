"""
Example usage of Microsoft Docs MCP integration with your MCP server

This demonstrates how to use both search capabilities:
1. Search your codebase (Azure Cognitive Search)
2. Search Microsoft documentation
"""

import asyncio
import json
from mcp_server_sota import MCPServer


async def demonstrate_dual_search():
    """Demonstrate searching both codebase and Microsoft docs"""
    
    server = MCPServer()
    
    print("=== MCP Server Dual Search Demonstration ===\n")
    
    # 1. List available tools
    print("1. Listing available tools:")
    list_request = {
        "jsonrpc": "2.0",
        "method": "tools/list",
        "id": 1
    }
    
    response = await server.handle_request(list_request)
    tools = response.get("result", {}).get("tools", [])
    
    for tool in tools:
        print(f"   - {tool['name']}: {tool['description']}")
    
    print("\n" + "="*50 + "\n")
    
    # 2. Search your codebase for vector search implementation
    print("2. Searching codebase for 'vector search implementation':")
    code_search_request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "search_code",
            "arguments": {
                "query": "vector search implementation",
                "intent": "understand",
                "language": "python"
            }
        },
        "id": 2
    }
    
    response = await server.handle_request(code_search_request)
    if "result" in response:
        content = response["result"]["content"][0]["text"]
        print(content[:500] + "..." if len(content) > 500 else content)
    
    print("\n" + "="*50 + "\n")
    
    # 3. Search Microsoft Docs for Azure Cognitive Search
    print("3. Searching Microsoft Docs for 'Azure Cognitive Search vector search':")
    docs_search_request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "search_microsoft_docs",
            "arguments": {
                "query": "Azure Cognitive Search vector search tutorial",
                "max_results": 3
            }
        },
        "id": 3
    }
    
    response = await server.handle_request(docs_search_request)
    if "result" in response:
        content = response["result"]["content"][0]["text"]
        print(content[:500] + "..." if len(content) > 500 else content)
    elif "error" in response:
        print(f"Error: {response['error']['message']}")
    
    print("\n" + "="*50 + "\n")
    
    # 4. Combined search example - understanding a concept
    print("4. Combined search - Understanding Azure OpenAI embeddings:")
    
    # First search your code
    print("   a) Your codebase implementation:")
    code_request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "search_code",
            "arguments": {
                "query": "Azure OpenAI embeddings generate_embedding",
                "intent": "understand"
            }
        },
        "id": 4
    }
    
    response = await server.handle_request(code_request)
    if "result" in response:
        content = response["result"]["content"][0]["text"]
        print(content[:300] + "..." if len(content) > 300 else content)
    
    print("\n   b) Microsoft documentation:")
    docs_request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "search_microsoft_docs",
            "arguments": {
                "query": "Azure OpenAI embeddings API",
                "max_results": 2
            }
        },
        "id": 5
    }
    
    response = await server.handle_request(docs_request)
    if "result" in response:
        content = response["result"]["content"][0]["text"]
        print(content[:300] + "..." if len(content) > 300 else content)


async def search_scenario(query: str, context: str):
    """Example of a real-world search scenario"""
    server = MCPServer()
    
    print(f"\n=== Search Scenario: {context} ===")
    print(f"Query: {query}\n")
    
    # Search both sources
    tasks = []
    
    # Code search
    code_request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "search_code",
            "arguments": {
                "query": query,
                "intent": "implement"
            }
        },
        "id": 10
    }
    tasks.append(server.handle_request(code_request))
    
    # Docs search
    docs_request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "search_microsoft_docs",
            "arguments": {
                "query": query,
                "max_results": 3
            }
        },
        "id": 11
    }
    tasks.append(server.handle_request(docs_request))
    
    # Execute both searches in parallel
    code_response, docs_response = await asyncio.gather(*tasks)
    
    print("From your codebase:")
    if "result" in code_response:
        content = code_response["result"]["content"][0]["text"]
        print(content[:400] + "..." if len(content) > 400 else content)
    
    print("\nFrom Microsoft Docs:")
    if "result" in docs_response:
        content = docs_response["result"]["content"][0]["text"]
        print(content[:400] + "..." if len(content) > 400 else content)


async def main():
    """Run all demonstrations"""
    
    # Basic demonstration
    await demonstrate_dual_search()
    
    # Real-world scenarios
    await search_scenario(
        "semantic search configuration",
        "Setting up semantic search in Azure Cognitive Search"
    )
    
    await search_scenario(
        "vector embeddings dimension size",
        "Understanding vector dimensions for embeddings"
    )


if __name__ == "__main__":
    asyncio.run(main())