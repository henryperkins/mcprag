"""
Test suite to verify remediation fixes from the security audit.
Tests each of the implemented fixes to ensure they work correctly.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestRemediationFixes(unittest.TestCase):
    """Test suite for verifying remediation fixes."""

    def test_issue_01_auth_validation(self):
        """Test Issue 01: Auth breakage and silent degradation fix."""
        from mcprag.server import MCPServer
        
        # Test with empty/whitespace credentials
        with patch.dict(os.environ, {
            'ACS_ADMIN_KEY': '   ',  # Whitespace only
            'ACS_ENDPOINT': 'https://test.search.windows.net'
        }):
            # Should not create search_client with invalid key
            server = MCPServer()
            self.assertIsNone(server.search_client)
    
    def test_issue_02_venv_path_portability(self):
        """Test Issue 02: Hard-coded venv path fix."""
        from mcprag.mcp.tools import azure_management
        
        # Check that sys.executable is used instead of hardcoded path
        self.assertTrue(hasattr(azure_management, 'sys'))
        
        # Verify no hardcoded venv paths remain
        with open('mcprag/mcp/tools/azure_management.py', 'r') as f:
            content = f.read()
            self.assertNotIn('/home/azureuser/mcprag/venv/bin/python', content)
    
    def test_issue_03_async_components_startup(self):
        """Test Issue 03: Async components startup fix."""
        from mcprag.server import MCPServer
        
        # Check that stdio mode starts components synchronously
        with patch('mcprag.server.asyncio.run') as mock_run:
            server = MCPServer()
            # Mock the mcp.run to prevent actual server start
            with patch.object(server.mcp, 'run'):
                server.run(transport='stdio')
            
            # Verify asyncio.run was called for stdio mode
            mock_run.assert_called_once()
    
    def test_issue_04_azure_client_pool(self):
        """Test Issue 04: Azure Client Pool singleton implementation."""
        from mcprag.enhanced_rag.azure_integration.rest.client_pool import (
            AzureSearchClientPool, get_azure_search_client
        )
        
        # Test singleton pattern
        pool1 = AzureSearchClientPool()
        pool2 = AzureSearchClientPool()
        self.assertIs(pool1, pool2)
        
        # Test client reuse
        with patch('mcprag.enhanced_rag.azure_integration.rest.client_pool.AzureSearchClient') as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client
            
            # Get same client twice
            client1 = get_azure_search_client('https://test.search.windows.net', 'key1', 'index1')
            client2 = get_azure_search_client('https://test.search.windows.net', 'key1', 'index1')
            
            # Should only create one client
            MockClient.assert_called_once()
            
            # Different config should create new client
            client3 = get_azure_search_client('https://test2.search.windows.net', 'key2', 'index2')
            self.assertEqual(MockClient.call_count, 2)
    
    def test_issue_05_embedding_provider_lazy_init(self):
        """Test Issue 05: Embedding provider import crash fix."""
        # Test that missing API key doesn't crash on import
        with patch.dict(os.environ, clear=True):
            # Should not raise during import
            from enhanced_rag.azure_integration.embedding_provider import AzureOpenAIEmbeddingProvider
            
            provider = AzureOpenAIEmbeddingProvider()
            # Should be created but disabled
            self.assertIsNotNone(provider)
            
            # First call should validate and disable
            result = provider.generate_embedding("test")
            self.assertIsNone(result)
            self.assertFalse(provider.enabled)
    
    def test_issue_07_filter_injection_protection(self):
        """Test Issue 07: Exact-term filter injection risk mitigation."""
        from enhanced_rag.retrieval.hybrid_searcher import HybridSearcher
        
        # Test that suspicious terms are handled safely
        searcher = HybridSearcher()
        
        # Mock the search operation
        with patch.object(searcher, 'rest_ops') as mock_ops:
            mock_ops.search = AsyncMock(return_value={'value': []})
            
            # Try injection attack patterns
            malicious_terms = [
                "foo') or 1 eq 1",
                "'; DROP TABLE users; --",
                "\" or \"1\"=\"1",
            ]
            
            async def test_search():
                # Should handle malicious terms safely
                result = await searcher.search(
                    query="test",
                    exact_terms=malicious_terms,
                    top_k=10
                )
                
                # Check that the filter was called
                mock_ops.search.assert_called()
                # Get the filter argument
                call_args = mock_ops.search.call_args
                if call_args and 'filter' in call_args.kwargs:
                    filter_str = call_args.kwargs['filter']
                    # Should have escaped quotes
                    self.assertIn("''", filter_str)  # Escaped quotes
            
            asyncio.run(test_search())
    
    def test_issue_08_lru_cache_implementation(self):
        """Test Issue 08: LRU cache for dependencies."""
        from enhanced_rag.utils.cache_manager import CacheManager
        
        cache = CacheManager(max_size=3)
        
        # Add items to cache
        cache.set('key1', 'value1')
        cache.set('key2', 'value2')
        cache.set('key3', 'value3')
        
        # Access key1 to make it recently used
        self.assertEqual(cache.get('key1'), 'value1')
        
        # Add new item, should evict key2 (least recently used)
        cache.set('key4', 'value4')
        
        # key2 should be evicted
        self.assertIsNone(cache.get('key2'))
        # Others should still be there
        self.assertEqual(cache.get('key1'), 'value1')
        self.assertEqual(cache.get('key3'), 'value3')
        self.assertEqual(cache.get('key4'), 'value4')


class TestAsyncComponentHealth(unittest.TestCase):
    """Test async component health checks."""
    
    async def test_health_check_with_components(self):
        """Test that health check works with async components."""
        from mcprag.mcp.tools.core import check_component
        from mcprag.server import MCPServer
        
        server = MCPServer()
        
        # Mock components
        server.pipeline = MagicMock()
        server.pipeline.hybrid_searcher = MagicMock()
        server.rest_client = MagicMock()
        server.rest_client.is_closed = False
        
        # Check component should work
        result = await check_component(server, 'pipeline')
        self.assertTrue(result['available'])
        
        result = await check_component(server, 'rest_client')
        self.assertTrue(result['available'])


def run_tests():
    """Run all remediation tests."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestRemediationFixes))
    suite.addTests(loader.loadTestsFromTestCase(TestAsyncComponentHealth))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)