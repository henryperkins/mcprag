#!/usr/bin/env python3
"""
Test MCP server directly to get full stack trace
"""

import asyncio
import sys
sys.path.insert(0, '.')

from mcp_server_sota import server, SearchCodeParams, SearchIntent

async def test():
    try:
        params = SearchCodeParams(
            query="ErrorHandler class",
            max_results=3
        )
        results = await server.search_code(params)
        print(f"Found {len(results)} results")
        for r in results:
            print(f"- {r.file_path}: {r.function_name}")
    except Exception as e:
        import traceback
        print(f"Error: {e}")
        print("\nFull traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())