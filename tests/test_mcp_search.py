#!/usr/bin/env python3
"""
Test MCP server search functionality
"""

import os
import asyncio
from dotenv import load_dotenv
from mcp_server_sota import EnhancedMCPServer, SearchCodeParams, SearchIntent

load_dotenv()

async def test_search():
    server = EnhancedMCPServer()
    
    # Test different searches
    test_queries = [
        {
            "query": "enhanced index builder", 
            "intent": SearchIntent.UNDERSTAND,
            "description": "Search for EnhancedIndexBuilder class"
        },
        {
            "query": "create_enhanced_rag_index",
            "intent": SearchIntent.IMPLEMENT, 
            "description": "Find the implementation of create_enhanced_rag_index"
        },
        {
            "query": "field mappings",
            "intent": SearchIntent.UNDERSTAND,
            "description": "Understanding field mappings"
        }
    ]
    
    for test in test_queries:
        print(f"\n{'='*60}")
        print(f"Test: {test['description']}")
        print(f"Query: {test['query']}")
        print(f"Intent: {test['intent']}")
        print('-'*60)
        
        try:
            params = SearchCodeParams(
                query=test['query'],
                intent=test['intent'],
                max_results=3
            )
            results = await server.search_code(params)
            
            print(f"Found {len(results)} results:")
            for i, result in enumerate(results, 1):
                print(f"\n{i}. {result.file_path}:{result.line_range or '?'}")
                print(f"   Function: {result.function_name or 'N/A'}")
                print(f"   Score: {result.score:.2f}")
                print(f"   Content preview: {result.content[:100]}...")
                
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

# Run the test
asyncio.run(test_search())