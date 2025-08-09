#!/usr/bin/env python3
"""
Test script for the remote MCP server.
"""

import asyncio
import json
import sys
from mcprag_client.client import MCPRAGClient

async def test_dev_mode():
    """Test the server in dev mode (no auth required)."""
    # Server is running on port 8002 with dev mode enabled
    async with MCPRAGClient(base_url="http://localhost:8002") as client:
        print("=" * 60)
        print("Testing Remote MCP Server (Dev Mode)")
        print("=" * 60)
        
        # 1. Health check
        print("\n1. Health Check:")
        try:
            health = await client.health_check()
            print(f"   Status: {health['status']}")
            print(f"   Version: {health['version']}")
            print(f"   Components: {json.dumps(health['components'], indent=6)}")
            print(f"   Authentication: {health.get('authentication', 'none')}")
        except Exception as e:
            print(f"   ERROR: {e}")
        
        # 2. List tools (in dev mode, should work without auth)
        print("\n2. List Available Tools:")
        try:
            # In dev mode, we might need to bypass auth check
            # Let's try without token first
            client.session_token = "dev-mode-token"  # Fake token for dev mode
            tools = await client.list_tools()
            print(f"   Total tools: {tools.get('total', 0)}")
            if tools.get('tools'):
                for tool in tools['tools']:
                    print(f"   - {tool['name']}")
            else:
                print("   No tools found (might need to check server initialization)")
        except Exception as e:
            print(f"   ERROR: {e}")
        
        # 3. Try a simple tool execution
        print("\n3. Test Tool Execution (search_code):")
        try:
            result = await client.execute_tool("search_code", {
                "query": "server",
                "max_results": 2,
                "detail_level": "compact"
            })
            print(f"   Result: {json.dumps(result, indent=6)[:500]}...")
        except Exception as e:
            print(f"   ERROR: {e}")

async def test_direct_api():
    """Test the API directly without the client."""
    import aiohttp
    
    print("\n" + "=" * 60)
    print("Direct API Testing")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        # Test the root endpoint
        print("\n1. Root Endpoint:")
        try:
            async with session.get("http://localhost:8002/") as resp:
                data = await resp.json()
                print(f"   Service: {data.get('service')}")
                print(f"   Version: {data.get('version')}")
                print(f"   Endpoints: {json.dumps(data.get('endpoints', {}), indent=6)}")
        except Exception as e:
            print(f"   ERROR: {e}")
        
        # Test listing tools directly
        print("\n2. List Tools (Direct):")
        try:
            # In dev mode, might not need auth header
            headers = {}
            async with session.get("http://localhost:8002/mcp/tools", headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"   Status: {resp.status}")
                    print(f"   Tools: {data}")
                else:
                    print(f"   Status: {resp.status}")
                    print(f"   Response: {await resp.text()}")
        except Exception as e:
            print(f"   ERROR: {e}")

async def main():
    """Main test function."""
    print("Testing Remote MCP Server Connection")
    print("Server: http://localhost:8002")
    print("Mode: Development (MCP_DEV_MODE=true)")
    
    # Test with the client
    await test_dev_mode()
    
    # Test direct API calls
    await test_direct_api()
    
    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())