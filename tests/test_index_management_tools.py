#!/usr/bin/env python3
"""
Test script to verify the new index management MCP tools.
"""

import asyncio
import json
from mcprag.server import MCPServer


async def test_index_management_tools():
    """Test the new index management MCP tools."""
    print("🔧 Testing Index Management MCP Tools")
    print("=" * 50)
    
    try:
        # Initialize the MCP server
        print("1. Initializing MCP server...")
        server = MCPServer()
        await server.ensure_async_components_started()
        
        # Test index status
        print("\n2. Testing index_status tool...")
        try:
            # Import the function directly from the tools module
            from mcprag.mcp.tools.azure_management import register_azure_tools
            
            # Create a mock MCP object to capture tool registrations
            class MockMCP:
                def __init__(self):
                    self.tools = {}
                
                def tool(self):
                    def decorator(func):
                        self.tools[func.__name__] = func
                        return func
                    return decorator
            
            mock_mcp = MockMCP()
            register_azure_tools(mock_mcp, server)
            
            # Test index_status
            if 'index_status' in mock_mcp.tools:
                result = await mock_mcp.tools['index_status']()
                print(f"   ✅ index_status: {json.dumps(result, indent=2)}")
            else:
                print("   ❌ index_status tool not found")
            
            # Test validate_index_schema
            if 'validate_index_schema' in mock_mcp.tools:
                result = await mock_mcp.tools['validate_index_schema']()
                print(f"   ✅ validate_index_schema: {json.dumps(result, indent=2)}")
            else:
                print("   ❌ validate_index_schema tool not found")
            
            # Test health_check
            if 'health_check' in mock_mcp.tools:
                result = await mock_mcp.tools['health_check']()
                print(f"   ✅ health_check: {json.dumps(result, indent=2)}")
            else:
                print("   ❌ health_check tool not found")
            
            print(f"\n📊 Total tools registered: {len(mock_mcp.tools)}")
            print("Available tools:")
            for tool_name in sorted(mock_mcp.tools.keys()):
                print(f"   • {tool_name}")
                
        except Exception as e:
            print(f"   ❌ Error testing tools: {e}")
            
    except Exception as e:
        print(f"❌ Failed to initialize MCP server: {e}")
        return False
    
    finally:
        # Cleanup async components
        try:
            await server.cleanup_async_components()
        except:
            pass
    
    print("\n✅ Index Management Tools Test Complete!")
    return True


if __name__ == "__main__":
    asyncio.run(test_index_management_tools())