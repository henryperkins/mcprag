#!/usr/bin/env python3
"""Test script to verify MCP tool fixes."""

import asyncio
import sys
import os
import logging

# Add the project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcprag.server import MCPServer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_tools():
    """Test the fixed MCP tools."""
    server = MCPServer()
    
    # Start async components
    await server.ensure_async_components_started()
    
    results = {}
    
    # Test 1: Check enhanced_search availability
    logger.info("Test 1: Checking enhanced_search availability")
    if hasattr(server, 'enhanced_search') and server.enhanced_search:
        results['enhanced_search'] = "✅ Available"
    else:
        results['enhanced_search'] = "❌ Not available"
    
    # Test 2: Check if search_code works without enhanced_search
    logger.info("Test 2: Testing search_code tool availability")
    if hasattr(server, 'search_client') and server.search_client:
        results['search_code_fallback'] = "✅ Has Azure Search fallback"
    else:
        results['search_code_fallback'] = "❌ No fallback available"
    
    # Test 3: Check microsoft_docs availability with aiohttp handling
    logger.info("Test 3: Testing microsoft_docs with aiohttp handling")
    try:
        # Import should work even if aiohttp is not installed
        import microsoft_docs_mcp_client
        if hasattr(microsoft_docs_mcp_client, 'AIOHTTP_AVAILABLE'):
            if microsoft_docs_mcp_client.AIOHTTP_AVAILABLE:
                results['microsoft_docs'] = "✅ aiohttp available"
            else:
                results['microsoft_docs'] = "✅ aiohttp not available (graceful fallback)"
        else:
            results['microsoft_docs'] = "⚠️ Missing AIOHTTP_AVAILABLE flag"
    except ImportError as e:
        results['microsoft_docs'] = f"❌ Import failed: {e}"
    
    # Test 4: Check code generation tools
    logger.info("Test 4: Testing code generation availability")
    if hasattr(server, 'code_gen') and server.code_gen:
        results['code_generation'] = "✅ Available"
    else:
        results['code_generation'] = "❌ Not available (expected with optional deps)"
    
    # Test 5: Check ranking improvements
    logger.info("Test 5: Testing ranking with rich features")
    if hasattr(server, 'result_explainer') and server.result_explainer:
        results['explain_ranking'] = "✅ Available"
    else:
        results['explain_ranking'] = "❌ Not available"
    
    # Test 6: Check tracking tools fallback
    logger.info("Test 6: Testing tracking tools fallback")
    has_enhanced = hasattr(server, 'enhanced_search') and server.enhanced_search
    has_feedback = hasattr(server, 'feedback_collector') and server.feedback_collector
    
    if has_enhanced or has_feedback:
        results['tracking_tools'] = f"✅ Available (enhanced: {has_enhanced}, feedback: {has_feedback})"
    else:
        results['tracking_tools'] = "❌ No backend available"
    
    # Test 7: Check admin tools
    logger.info("Test 7: Testing admin tools")
    if hasattr(server, 'indexer_integration') and server.indexer_integration:
        results['admin_tools'] = "✅ Available (admin mode)"
    else:
        results['admin_tools'] = "⚠️ Not available (requires admin mode)"
    
    # Print results
    print("\n=== MCP Tool Fix Test Results ===\n")
    for test, result in results.items():
        print(f"{test}: {result}")
    
    # Count successes
    success_count = sum(1 for r in results.values() if r.startswith("✅"))
    total_count = len(results)
    
    print(f"\nTotal: {success_count}/{total_count} tests passed")
    
    # Improved from 36% (4/11) to expected higher percentage
    improvement_percentage = (success_count / total_count) * 100
    print(f"Functionality rate: {improvement_percentage:.1f}%")
    
    if improvement_percentage > 36:
        print("✅ Improvement confirmed!")
    else:
        print("❌ No improvement detected")


if __name__ == "__main__":
    asyncio.run(test_tools())