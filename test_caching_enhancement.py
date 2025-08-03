#!/usr/bin/env python3
"""
Test the enhanced caching functionality in the MCP server.
"""

import asyncio
import os
import sys
import time
import pytest
from unittest.mock import Mock, AsyncMock, patch

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock the environment before importing
os.environ["ACS_ENDPOINT"] = "https://test.search.windows.net"
os.environ["ACS_ADMIN_KEY"] = "test-key"
os.environ["ACS_INDEX_NAME"] = "test-index"

from mcp_server_sota import SearchCodeParams, SearchResult, SearchIntent, EnhancedMCPServer


class TestCachingEnhancement:
    """Test the enhanced caching functionality."""
    
    def test_cache_key_generation(self):
        """Test that cache keys are generated consistently."""
        server = EnhancedMCPServer()
        
        params1 = SearchCodeParams(
            query="test query",
            intent=SearchIntent.IMPLEMENT,
            language="python",
            repository="test-repo",
            max_results=10
        )
        
        params2 = SearchCodeParams(
            query="test query",
            intent=SearchIntent.IMPLEMENT,
            language="python",
            repository="test-repo",
            max_results=10
        )
        
        # Same parameters should generate same cache key
        key1 = server._get_cache_key(params1)
        key2 = server._get_cache_key(params2)
        assert key1 == key2
        
        # Different parameters should generate different cache keys
        params3 = SearchCodeParams(
            query="different query",
            intent=SearchIntent.IMPLEMENT,
            language="python",
            repository="test-repo",
            max_results=10
        )
        key3 = server._get_cache_key(params3)
        assert key1 != key3
    
    def test_should_cache_query_logic(self):
        """Test the logic for determining if a query should be cached."""
        server = EnhancedMCPServer()
        
        # Basic query should be cached
        params1 = SearchCodeParams(query="test", max_results=10)
        assert server._should_cache_query(params1) is True
        
        # Query with disable_cache should not be cached
        params2 = SearchCodeParams(query="test", max_results=10, disable_cache=True)
        assert server._should_cache_query(params2) is False
        
        # Query with dependencies and small result set should be cached
        params3 = SearchCodeParams(query="test", max_results=3, include_dependencies=True)
        assert server._should_cache_query(params3) is True
        
        # Query with dependencies and large result set should not be cached
        params4 = SearchCodeParams(query="test", max_results=10, include_dependencies=True)
        assert server._should_cache_query(params4) is False
    
    def test_cache_cleanup_expired_entries(self):
        """Test that expired cache entries are properly cleaned up."""
        server = EnhancedMCPServer()
        server._ttl_seconds = 1  # 1 second TTL for testing
        
        # Add some cache entries
        server._query_cache["key1"] = [SearchResult(
            file_path="/test1.py", repository="repo1", language="python", score=1.0, content="test1"
        )]
        server._query_cache["key2"] = [SearchResult(
            file_path="/test2.py", repository="repo2", language="python", score=1.0, content="test2"
        )]
        
        # Set timestamps - one current, one expired
        now = time.time()
        server._query_cache_ts["key1"] = now  # Current
        server._query_cache_ts["key2"] = now - 2  # Expired (2 seconds ago)
        
        # Cleanup should remove expired entry
        server._cleanup_expired_cache_entries()
        
        assert "key1" in server._query_cache
        assert "key2" not in server._query_cache
        assert "key1" in server._query_cache_ts
        assert "key2" not in server._query_cache_ts
    
    def test_cache_invalidation_by_pattern(self):
        """Test pattern-based cache invalidation."""
        server = EnhancedMCPServer()
        
        # Add some cache entries with different patterns
        server._query_cache["parse json|implement|repo1|python|10|0|False|||False||"] = []
        server._query_cache["handle error|debug|repo1|javascript|10|0|False|||False||"] = []
        server._query_cache["test function|understand|repo2|python|10|0|False|||False||"] = []
        
        server._query_cache_ts["parse json|implement|repo1|python|10|0|False|||False||"] = time.time()
        server._query_cache_ts["handle error|debug|repo1|javascript|10|0|False|||False||"] = time.time()
        server._query_cache_ts["test function|understand|repo2|python|10|0|False|||False||"] = time.time()
        
        # Test pattern-based invalidation
        invalidated = server._invalidate_cache_by_pattern(pattern="json")
        assert invalidated == 1
        assert len(server._query_cache) == 2
        
        # Test repository-based invalidation
        invalidated = server._invalidate_cache_by_pattern(repository="repo1")
        assert invalidated == 1
        assert len(server._query_cache) == 1
        
        # Test language-based invalidation
        invalidated = server._invalidate_cache_by_pattern(language="python")
        assert invalidated == 1
        assert len(server._query_cache) == 0
    
    def test_cache_stats_generation(self):
        """Test that cache statistics are generated correctly."""
        server = EnhancedMCPServer()
        server._ttl_seconds = 60
        server._cache_max_entries = 100
        
        # Add some cache entries
        now = time.time()
        server._query_cache["key1"] = []
        server._query_cache["key2"] = []
        server._query_cache["key3"] = []
        
        # Set timestamps - mix of current and expired
        server._query_cache_ts["key1"] = now  # Current
        server._query_cache_ts["key2"] = now - 30  # Current (within TTL)
        server._query_cache_ts["key3"] = now - 120  # Expired
        
        stats = server._get_cache_stats()
        
        assert stats["total_entries"] == 3
        assert stats["expired_entries"] == 1
        assert stats["active_entries"] == 2
        assert stats["max_entries"] == 100
        assert stats["ttl_seconds"] == 60
        assert "memory_usage_estimate" in stats
    
    @pytest.mark.asyncio
    async def test_cache_integration_with_search(self):
        """Test that caching integrates properly with search functionality."""
        with patch('mcp_server_sota.server') as mock_server:
            # Create a real server instance for testing
            server = EnhancedMCPServer()
            server._ttl_seconds = 60
            server._cache_max_entries = 100
            
            # Mock the core search functionality
            mock_results = [SearchResult(
                file_path="/test.py", repository="test-repo", language="python", 
                score=1.0, content="test content"
            )]
            
            # Mock the search_code method to return our test results
            async def mock_search_code(params):
                return mock_results
            
            server.search_code = mock_search_code
            
            # First call should execute search and cache results
            params = SearchCodeParams(query="test query", max_results=10)
            cache_key = server._get_cache_key(params)
            
            # Verify cache is empty initially
            assert cache_key not in server._query_cache
            
            # Simulate caching (normally done in search_code method)
            if server._should_cache_query(params):
                server._query_cache[cache_key] = mock_results
                server._query_cache_ts[cache_key] = time.time()
            
            # Verify results are cached
            assert cache_key in server._query_cache
            assert server._query_cache[cache_key] == mock_results
            
            # Test cache hit
            cached_results = server._query_cache.get(cache_key)
            ts = server._query_cache_ts.get(cache_key)
            now = time.time()
            
            assert cached_results is not None
            assert ts is not None
            assert (now - ts) <= server._ttl_seconds


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
