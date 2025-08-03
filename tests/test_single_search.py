#!/usr/bin/env python3
"""Test a single search to see actual results"""

import asyncio
import json
from mcp_server_sota import search_code

async def test_search():
    """Test a single search and show results"""
    
    print("Testing code search...")
    
    # Test search
    result = await search_code(
        query="azure search client",
        max_results=3
    )
    
    # Debug: show what we got
    print(f"Result type: {type(result)}")
    print(f"Result: {result}")
    
    # Parse result
    if isinstance(result, str):
        try:
            result_data = json.loads(result)
        except json.JSONDecodeError:
            print("Failed to parse JSON, result was:", repr(result))
            return
    else:
        result_data = result
    
    print(f"\nSearch Status: {'Success' if result_data.get('ok') else 'Failed'}")
    
    if result_data.get('ok'):
        data = result_data.get('data', [])
        print(f"Results found: {len(data)}")
        
        for i, item in enumerate(data):
            print(f"\n--- Result {i+1} ---")
            print(f"File: {item.get('file_path', 'N/A')}")
            print(f"Repository: {item.get('repository', 'N/A')}")
            print(f"Language: {item.get('language', 'N/A')}")
            print(f"Function: {item.get('function_name', 'N/A')}")
            print(f"Score: {item.get('score', 0):.4f}")
            
            # Show snippet
            content = item.get('content', '')
            if content:
                lines = content.split('\n')
                preview = '\n'.join(lines[:5])
                if len(lines) > 5:
                    preview += '\n...'
                print(f"Content preview:\n{preview}")
    else:
        print(f"Error: {result_data.get('error', 'Unknown error')}")

if __name__ == "__main__":
    asyncio.run(test_search())