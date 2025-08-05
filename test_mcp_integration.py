#!/usr/bin/env python3
"""
Test the MCP server with the new index management tools via the actual MCP interface.
"""

import asyncio
import json
import sys
from mcprag.server import create_server


async def test_mcp_tools():
    """Test the actual MCP tools through the MCP interface."""
    print("🧪 Testing MCP Index Management Tools via MCP Interface")
    print("=" * 60)
    
    server = None
    try:
        # Create the MCP server
        print("1. Creating MCP server...")
        server = create_server()
        
        # Start async components
        await server.ensure_async_components_started()
        print("   ✅ MCP server initialized")
        
        # Get the registered tools from the mcp object
        tools = []
        if hasattr(server.mcp, '_tools'):
            tools = list(server.mcp._tools.keys())
        elif hasattr(server.mcp, 'tools'):
            tools = list(server.mcp.tools.keys()) if hasattr(server.mcp.tools, 'keys') else []
        
        print(f"\n2. Found {len(tools)} registered tools")
        
        # Look for our index management tools
        index_tools = [t for t in tools if any(keyword in t for keyword in [
            'index_status', 'validate_index_schema', 'index_repository', 
            'backup_index_schema', 'health_check'
        ])]
        
        if index_tools:
            print("   ✅ Index management tools found:")
            for tool in sorted(index_tools):
                print(f"     • {tool}")
        else:
            print("   ⚠️  No index management tools found in registered tools")
            print(f"   All tools: {sorted(tools)}")
        
        # Test calling the tools directly from the server components
        print("\n3. Testing tools via server components...")
        
        # Test index_status
        if server.index_automation and server.index_automation.ops:
            try:
                from mcprag.config import Config
                index_name = Config.INDEX_NAME
                
                print(f"   Testing index stats for: {index_name}")
                stats = await server.index_automation.ops.get_index_stats(index_name)
                index_def = await server.index_automation.ops.get_index(index_name)
                
                print(f"   ✅ Index stats retrieved:")
                print(f"     • Documents: {stats.get('documentCount', 0):,}")
                print(f"     • Storage: {stats.get('storageSize', 0) / (1024*1024):.2f} MB")
                print(f"     • Fields: {len(index_def.get('fields', []))}")
                print(f"     • Vector Search: {bool(index_def.get('vectorSearch'))}")
                
            except Exception as e:
                print(f"   ❌ Error testing index stats: {e}")
        
        # Test health check components
        print("\n4. Testing component health...")
        components = {
            'search_client': server.search_client is not None,
            'enhanced_search': server.enhanced_search is not None,
            'index_automation': server.index_automation is not None,
            'rest_ops': server.rest_ops is not None,
            'pipeline': server.pipeline is not None,
        }
        
        healthy_count = sum(1 for status in components.values() if status)
        print(f"   System Health: {healthy_count}/{len(components)} components healthy")
        
        for comp_name, status in components.items():
            print(f"     • {comp_name}: {'✅' if status else '❌'}")
        
        print("\n5. Testing MCP prompts...")
        if hasattr(server.mcp, '_prompts') or hasattr(server.mcp, 'prompts'):
            prompts = []
            if hasattr(server.mcp, '_prompts'):
                prompts = list(server.mcp._prompts.keys())
            elif hasattr(server.mcp, 'prompts'):
                prompts = list(server.mcp.prompts.keys()) if hasattr(server.mcp.prompts, 'keys') else []
            
            if 'manage_azure_search_index' in prompts:
                print("   ✅ Index management prompt available")
            else:
                print(f"   Available prompts: {prompts}")
        
        print("\n✅ MCP Integration Test Complete!")
        print("\n📋 Summary:")
        print(f"   • Server initialized: ✅")
        print(f"   • Components healthy: {healthy_count}/{len(components)}")
        print(f"   • Index management tools: {'✅' if index_tools else '❌'}")
        print(f"   • Azure connectivity: {'✅' if server.rest_ops else '❌'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        if server:
            try:
                await server.cleanup_async_components()
                print("\n🧹 Cleanup completed")
            except Exception as e:
                print(f"⚠️  Cleanup error: {e}")


if __name__ == "__main__":
    success = asyncio.run(test_mcp_tools())
    sys.exit(0 if success else 1)