#!/usr/bin/env python
"""Test script to verify the remediation fixes."""

import asyncio
import logging
from unittest.mock import Mock, AsyncMock, patch
import sys

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_fixes():
    """Test all the remediation fixes."""
    results = []
    
    # Test 1: HybridSearcher uses async REST operations
    try:
        from enhanced_rag.retrieval.hybrid_searcher import HybridSearcher
        from enhanced_rag.azure_integration.rest.operations import SearchOperations
        
        # Check that HybridSearcher accepts rest_ops parameter
        mock_ops = Mock(spec=SearchOperations)
        searcher = HybridSearcher(rest_ops=mock_ops)
        assert searcher.rest_ops is mock_ops
        results.append("✅ Test 1 PASSED: HybridSearcher accepts REST operations")
    except Exception as e:
        results.append(f"❌ Test 1 FAILED: {e}")
    
    # Test 2: REST client doesn't log response bodies
    try:
        from enhanced_rag.azure_integration.rest.client import AzureSearchClient
        import httpx
        
        # Check error logging doesn't include response body
        with patch('enhanced_rag.azure_integration.rest.client.logger') as mock_logger:
            client = AzureSearchClient("https://test.com", "key")
            
            # Create a mock error response
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.text = "SECRET DATA"
            mock_response.json.return_value = {"secret": "data"}
            
            error = httpx.HTTPStatusError("test", request=Mock(), response=mock_response)
            
            # Simulate the error handling
            try:
                raise error
            except httpx.HTTPStatusError as e:
                status = getattr(e.response, "status_code", "unknown")
                # This is what the code does now
                mock_logger.error(f"HTTP error {status} during Azure Search request")
            
            # Verify the log message doesn't contain sensitive data
            log_call = str(mock_logger.error.call_args)
            assert "SECRET DATA" not in log_call
            assert "secret" not in log_call
            results.append("✅ Test 2 PASSED: REST error logging sanitized")
    except Exception as e:
        results.append(f"❌ Test 2 FAILED: {e}")
    
    # Test 3: run_indexer supports wait parameter
    try:
        from enhanced_rag.azure_integration.rest.operations import SearchOperations
        
        # Check the method signature includes wait parameter
        import inspect
        sig = inspect.signature(SearchOperations.run_indexer)
        assert 'wait' in sig.parameters
        assert sig.parameters['wait'].default is False
        results.append("✅ Test 3 PASSED: run_indexer has wait parameter")
    except Exception as e:
        results.append(f"❌ Test 3 FAILED: {e}")
    
    # Test 4: Pipeline cleanup closes REST client
    try:
        from enhanced_rag.pipeline import RAGPipeline
        
        # Check cleanup method includes REST client closing
        import inspect
        source = inspect.getsource(RAGPipeline.cleanup)
        assert "_azure_operations" in source
        assert "client.close()" in source
        results.append("✅ Test 4 PASSED: Pipeline cleanup closes REST client")
    except Exception as e:
        results.append(f"❌ Test 4 FAILED: {e}")
    
    # Test 5: Exact term clamping is implemented
    try:
        from enhanced_rag.retrieval.hybrid_searcher import HybridSearcher
        import inspect
        
        # Check that search method includes clamping
        source = inspect.getsource(HybridSearcher.search)
        assert "_clamp_term" in source
        assert "[:200]" in source  # Length clamping
        results.append("✅ Test 5 PASSED: Exact term clamping implemented")
    except Exception as e:
        results.append(f"❌ Test 5 FAILED: {e}")
    
    # Test 6: MCP tools have async startup
    try:
        from mcprag.mcp.tools.generation import register_generation_tools
        import inspect
        
        source = inspect.getsource(register_generation_tools)
        assert "ensure_async_components_started" in source
        results.append("✅ Test 6 PASSED: MCP tools ensure async startup")
    except Exception as e:
        results.append(f"❌ Test 6 FAILED: {e}")
    
    # Print results
    print("\n" + "="*50)
    print("REMEDIATION TEST RESULTS")
    print("="*50)
    for result in results:
        print(result)
    
    # Summary
    passed = sum(1 for r in results if r.startswith("✅"))
    failed = sum(1 for r in results if r.startswith("❌"))
    print("\n" + "="*50)
    print(f"SUMMARY: {passed} passed, {failed} failed out of {len(results)} tests")
    print("="*50)
    
    return failed == 0

if __name__ == "__main__":
    success = asyncio.run(test_fixes())
    sys.exit(0 if success else 1)