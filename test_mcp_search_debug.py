#!/usr/bin/env python3
"""
Debug the MCP search error
"""
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_server_sota import EnhancedMCPServer, SearchCodeParams

async def test_search():
    server = EnhancedMCPServer()
    
    # Test search
    params = SearchCodeParams(
        query="test",
        repository="mcprag",
        max_results=1
    )
    
    try:
        results = await server.search_code(params)
        print("✅ Search successful!")
        for result in results:
            print(f"  - {result.file_path}")
    except Exception as e:
        print(f"❌ Search failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_search())