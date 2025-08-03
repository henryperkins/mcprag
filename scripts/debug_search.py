#!/usr/bin/env python3
"""
Debug search to find where None is coming from
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
        
        # Check each result for None values
        for i, r in enumerate(results):
            print(f"\nResult {i+1}:")
            print(f"  file_path: {repr(r.file_path)}")
            print(f"  repository: {repr(r.repository)}")
            print(f"  language: {repr(r.language)}")
            print(f"  function_name: {repr(r.function_name)}")
            print(f"  signature: {repr(r.signature)}")
            print(f"  line_range: {repr(r.line_range)}")
            print(f"  score: {repr(r.score)}")
            print(f"  context: {repr(r.context)}")
            
        # Try formatting
        print("\nTrying format_results...")
        try:
            formatted = server.format_results(results, "ErrorHandler class")
            print("Format succeeded!")
        except Exception as e:
            import traceback
            print(f"Format error: {e}")
            traceback.print_exc()
            
    except Exception as e:
        import traceback
        print(f"Error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())