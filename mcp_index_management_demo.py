#!/usr/bin/env python3
"""
Demo script showing how to use the new MCP index management tools.
"""

import asyncio
import json
from mcprag.server import MCPServer


async def demo_index_management():
    """Demonstrate the new index management MCP tools."""
    print("🚀 MCP Index Management Tools Demo")
    print("=" * 50)
    
    server = None
    try:
        # Initialize the MCP server
        print("1. Initializing MCP server...")
        server = MCPServer()
        await server.ensure_async_components_started()
        
        # Setup tools
        class MockMCP:
            def __init__(self):
                self.tools = {}
            
            def tool(self):
                def decorator(func):
                    self.tools[func.__name__] = func
                    return func
                return decorator
        
        mock_mcp = MockMCP()
        from mcprag.mcp.tools.azure_management import register_azure_tools
        register_azure_tools(mock_mcp, server)
        
        print("\n2. Getting current index status...")
        status = await mock_mcp.tools['index_status']()
        if status['ok']:
            data = status['data']
            print(f"   📊 Index: {data['index_name']}")
            print(f"   📄 Documents: {data['documents']:,}")
            print(f"   🏗️  Fields: {data['fields']}")
            print(f"   💾 Storage: {data['storage_size_mb']} MB")
            print(f"   🔍 Vector Search: {'✅' if data['vector_search'] else '❌'}")
            print(f"   🧠 Semantic Search: {'✅' if data['semantic_search'] else '❌'}")
        
        print("\n3. Validating index schema...")
        schema_result = await mock_mcp.tools['validate_index_schema']()
        if schema_result['ok']:
            data = schema_result['data']
            print(f"   Schema Valid: {'✅' if data['valid'] else '❌'}")
            if data['issues']:
                print("   Issues found:")
                for issue in data['issues']:
                    print(f"   • {issue['type'].upper()}: {issue['message']}")
        
        print("\n4. Checking system health...")
        health = await mock_mcp.tools['health_check']()
        if health['ok']:
            components = health['data']['components']
            print(f"   Overall Health: {'✅' if health['data']['healthy'] else '⚠️'}")
            print("   Component Status:")
            for comp_name, status in components.items():
                print(f"     • {comp_name}: {'✅' if status else '❌'}")
        
        print(f"\n📋 Available Index Management Tools:")
        management_tools = [
            'index_status', 'validate_index_schema', 'index_repository',
            'index_changed_files', 'backup_index_schema', 'clear_repository_documents',
            'rebuild_index', 'manage_index', 'manage_documents', 'manage_indexer'
        ]
        
        for tool in management_tools:
            if tool in mock_mcp.tools:
                print(f"   ✅ {tool}")
            else:
                print(f"   ❌ {tool}")
        
        print("\n🔧 Example Usage:")
        print("   # Get index status")
        print("   await index_status()")
        print()
        print("   # Index current repository")
        print("   await index_repository(repo_path='.', repo_name='mcprag')")
        print()
        print("   # Index specific files")
        print("   await index_changed_files(['file1.py', 'file2.js'], repo_name='mcprag')")
        print()
        print("   # Backup schema")
        print("   await backup_index_schema('backup.json')")
        print()
        print("   # Validate schema")
        print("   await validate_index_schema()")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if server:
            try:
                await server.cleanup_async_components()
            except:
                pass
    
    print("\n✅ Demo Complete!")


if __name__ == "__main__":
    asyncio.run(demo_index_management())