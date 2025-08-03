#!/usr/bin/env python3
"""
Comprehensive tests for enhanced MCP server tool modifications.
Tests all the improvements made to the MCP server.
"""

import asyncio
import json
import os
import sys
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import pytest

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock the environment before importing
os.environ["ACS_ENDPOINT"] = "https://test.search.windows.net"
os.environ["ACS_ADMIN_KEY"] = "test-key"
os.environ["ACS_INDEX_NAME"] = "test-index"

# Import after setting environment
from mcp_server_sota import (
    SearchCodeParams, SearchResult, SearchIntent, FieldMapper,
    EnhancedMCPServer, _ok, _err, _Timer
)


class TestFieldMapperExactTerms:
    """Test the enhanced FieldMapper with exact terms support."""
    
    def test_field_mapper_with_available_fields(self):
        """Test FieldMapper correctly identifies available fields."""
        available = ["content", "function_name", "repository", "file_path"]
        mapper = FieldMapper(available)
        
        assert "content" in mapper.available
        assert "function_name" in mapper.available
        assert mapper.reverse_map["content"] == "content"
        assert mapper.reverse_map["function_name"] == "function_name"
    
    def test_field_mapper_with_missing_fields(self):
        """Test FieldMapper handles missing searchable fields."""
        available = ["content", "repository", "file_path"]  # missing function_name
        mapper = FieldMapper(available)
        
        assert "content" in mapper.available
        assert "function_name" not in mapper.available
        assert "function_name" not in mapper.reverse_map


class TestEnhancedMCPServerCore:
    """Test EnhancedMCPServer core functionality."""
    
    def test_timer_functionality(self):
        """Test _Timer class works correctly."""
        timer = _Timer()
        timer.mark("step1")
        timer.mark("step2")
        
        durations = timer.durations()
        assert "start→step1" in durations
        assert "step1→step2" in durations
        assert "total" in durations
    
    def test_ok_err_functions(self):
        """Test _ok and _err helper functions."""
        ok_result = _ok({"test": "data"})
        assert ok_result["status"] == "success"
        assert ok_result["data"]["test"] == "data"
        
        err_result = _err("test error", code="test_code")
        assert err_result["status"] == "error"
        assert err_result["error"]["message"] == "test error"
        assert err_result["error"]["code"] == "test_code"


class TestSearchCodeEnhancements:
    """Test search_code tool enhancements."""
    
    @pytest.mark.asyncio
    async def test_search_code_with_exact_terms(self):
        """Test search_code properly extracts and applies exact terms."""
        with patch('mcp_server_sota.server') as mock_server:
            # Mock the server's search_code method
            mock_server.search_code = AsyncMock(return_value=[
                SearchResult(
                    file_path="/test/file.py",
                    repository="test-repo",
                    language="python",
                    score=0.9,
                    content="def parse_http_header(header):",
                    function_name="parse_http_header"
                )
            ])
            mock_server._last_total_count = 1
            mock_server._query_cache = {}
            mock_server._query_cache_ts = {}
            mock_server._ttl_seconds = 60
            mock_server._cache_max_entries = 500
            mock_server._last_search_params = {"_applied_exact_terms": True}
            mock_server._last_search_timings = {
                "start→cache_check": 1.0,
                "cache_check→query_enhanced": 2.0
            }
            
            # Test with quoted phrase
            result = await search_code(
                query='parse "HTTP/1.1" headers',
                max_results=10
            )
            
            assert result["status"] == "success"
            assert result["data"]["applied_exact_terms"] == True
            assert result["data"]["exact_terms"] == ["HTTP/1.1"]
            assert "server_timings_ms" in result["data"]
    
    @pytest.mark.asyncio
    async def test_search_code_auto_extract_numeric_terms(self):
        """Test automatic extraction of numeric literals."""
        with patch('mcp_server_sota.server') as mock_server:
            mock_server.search_code = AsyncMock(return_value=[])
            mock_server._last_total_count = 0
            mock_server._query_cache = {}
            mock_server._query_cache_ts = {}
            mock_server._ttl_seconds = 60
            mock_server._cache_max_entries = 500
            mock_server._last_search_params = {"_applied_exact_terms": True}
            
            result = await search_code(
                query="dimension 3072 embedding",
                max_results=10
            )
            
            assert result["status"] == "success"
            assert result["data"]["exact_terms"] == ["3072"]


class TestMicrosoftDocsNormalization:
    """Test Microsoft Docs search I/O normalization."""
    
    @pytest.mark.asyncio
    async def test_search_microsoft_docs_returns_structured_json(self):
        """Test search_microsoft_docs returns structured JSON instead of string."""
        with patch('mcp_server_sota.MicrosoftDocsMCPClient') as MockClient:
            # Mock the client
            mock_client = AsyncMock()
            mock_client.search_docs = AsyncMock(return_value=[
                {
                    "title": "Azure Search Guide",
                    "url": "https://docs.microsoft.com/azure-search",
                    "content": "This is a guide to Azure Search..."
                }
            ])
            MockClient.return_value.__aenter__.return_value = mock_client
            
            # Enable docs support
            with patch('mcp_server_sota.DOCS_SUPPORT', True):
                result = await search_microsoft_docs("Azure Search", max_results=5)
            
            assert result["status"] == "success"
            assert "results" in result["data"]
            assert "formatted" in result["data"]
            assert result["data"]["count"] == 1
            assert result["data"]["results"][0]["title"] == "Azure Search Guide"
    
    @pytest.mark.asyncio
    async def test_search_microsoft_docs_unavailable(self):
        """Test search_microsoft_docs when docs support is unavailable."""
        with patch('mcp_server_sota.DOCS_SUPPORT', False):
            result = await search_microsoft_docs("Azure Search", max_results=5)
        
        assert result["status"] == "error"
        assert result["error"]["code"] == "enhanced_unavailable"


class TestDiagnoseQueryEnhancements:
    """Test enhanced diagnostics in diagnose_query."""
    
    @pytest.mark.asyncio
    async def test_diagnose_query_detailed_stages(self):
        """Test diagnose_query returns detailed stage timings."""
        with patch('mcp_server_sota.server') as mock_server:
            mock_server.search_code = AsyncMock(return_value=[])
            mock_server._query_cache = {}
            mock_server._query_cache_ts = {}
            mock_server._ttl_seconds = 60
            mock_server._last_search_timings = {
                "start→cache_check": 1.0,
                "cache_check→query_enhanced": 2.0,
                "query_enhanced→repo_resolved": 1.5,
                "repo_resolved→params_built": 0.5,
                "params_built→exact_terms_applied": 0.3,
                "exact_terms_applied→acs_search_complete": 50.0,
                "acs_search_complete→results_fetched": 5.0,
                "results_fetched→filtered_ranked": 3.0,
                "filtered_ranked→results_converted": 2.0
            }
            mock_server._last_search_params = {"_applied_exact_terms": True}
            
            result = await diagnose_query(
                query="test query",
                mode="base"
            )
            
            assert result["status"] == "success"
            data = result["data"]
            assert "stages" in data
            assert len(data["stages"]) > 5  # Should have detailed stages
            assert "server_timings_ms" in data
            assert data["applied_exact_terms"] == True
            
            # Check stage names
            stage_names = [s["stage"] for s in data["stages"]]
            assert "cache_check" in stage_names
            assert "azure_search" in stage_names
            assert "filter_rank" in stage_names


class TestHybridSearchEnhancements:
    """Test actual hybrid scoring implementation."""
    
    @pytest.mark.asyncio
    async def test_search_code_hybrid_actual_scoring(self):
        """Test hybrid search performs actual BM25/semantic blending."""
        with patch('mcp_server_sota.server') as mock_server:
            # Mock BM25 results
            bm25_results = [
                SearchResult(
                    file_path="/test/file1.py",
                    repository="repo",
                    language="python",
                    score=10.0,
                    content="BM25 match",
                    line_range="1-10"
                ),
                SearchResult(
                    file_path="/test/file2.py",
                    repository="repo",
                    language="python",
                    score=8.0,
                    content="Another BM25 match",
                    line_range="20-30"
                )
            ]
            
            # Mock semantic results (overlapping with BM25)
            semantic_results = [
                SearchResult(
                    file_path="/test/file1.py",
                    repository="repo",
                    language="python",
                    score=0.95,
                    content="BM25 match",
                    line_range="1-10"
                ),
                SearchResult(
                    file_path="/test/file3.py",
                    repository="repo",
                    language="python",
                    score=0.90,
                    content="Semantic only match",
                    line_range="5-15"
                )
            ]
            
            # Set up mock to return different results based on params
            async def mock_search(params):
                if params.bm25_only:
                    return bm25_results
                else:
                    return semantic_results
            
            mock_server.search_code = mock_search
            mock_server._semantic_available = True
            
            # Disable enhanced RAG
            with patch('mcp_server_sota.ENHANCED_RAG_SUPPORT', False):
                result = await search_code_hybrid(
                    query="test query",
                    bm25_weight=0.6,
                    vector_weight=0.4,
                    max_results=3
                )
            
            assert result["status"] == "success"
            data = result["data"]
            
            # Check weights are recorded
            assert data["weights"]["bm25"] == 0.6
            assert data["weights"]["vector"] == 0.4
            
            # Check results are merged and scored
            assert len(data["final_results"]) <= 3
            
            # First result should be file1 (appears in both)
            first = data["final_results"][0]
            assert first["file_path"] == "/test/file1.py"
            assert "hybrid_score" in first
            assert "bm25_score" in first
            assert "semantic_score" in first
            
            # Check hybrid score calculation
            # file1: BM25 normalized = 1.0, semantic normalized = 1.0
            # hybrid = 1.0 * 0.6 + 1.0 * 0.4 = 1.0
            assert abs(first["hybrid_score"] - 1.0) < 0.01
            
            # Check stages if requested
            assert data["stages"] is not None
            stage_names = [s["stage"] for s in data["stages"]]
            assert "bm25_search" in stage_names
            assert "semantic_search" in stage_names
            assert "merge_rerank" in stage_names


class TestExplainRankingEnhancements:
    """Test explain_ranking hardening."""
    
    @pytest.mark.asyncio
    async def test_explain_ranking_fallback_on_enhanced_failure(self):
        """Test explain_ranking falls back to base when enhanced fails."""
        with patch('mcp_server_sota.ENHANCED_RAG_SUPPORT', True):
            with patch('mcp_server_sota.enhanced_search_tool') as mock_tool:
                # Make enhanced search fail
                mock_tool.search = AsyncMock(side_effect=Exception("Enhanced failed"))
                
                with patch('mcp_server_sota.server') as mock_server:
                    mock_server.search_code = AsyncMock(return_value=[
                        SearchResult(
                            file_path="/test/file.py",
                            repository="repo",
                            language="python",
                            score=0.8,
                            content="test content",
                            signature="def test():"
                        )
                    ])
                    
                    result = await explain_ranking(
                        query="test query",
                        mode="enhanced"
                    )
                    
                    assert result["status"] == "success"
                    # Should fall back to base mode
                    assert result["data"]["mode"] == "base"
                    assert "timings_ms" in result["data"]
    
    @pytest.mark.asyncio
    async def test_explain_ranking_includes_timings(self):
        """Test explain_ranking includes timing information."""
        with patch('mcp_server_sota.server') as mock_server:
            mock_server.search_code = AsyncMock(return_value=[])
            
            result = await explain_ranking(
                query="test query",
                mode="base"
            )
            
            assert result["status"] == "success"
            assert "timings_ms" in result["data"]
            assert "total" in result["data"]["timings_ms"]


class TestIndexRebuildGuard:
    """Test index_rebuild method guarding."""
    
    @pytest.mark.asyncio
    async def test_index_rebuild_guards_missing_method(self):
        """Test index_rebuild handles missing run_indexer_on_demand gracefully."""
        with patch('mcp_server_sota._is_admin', return_value=True):
            with patch('mcp_server_sota.AZURE_ADMIN_SUPPORT', True):
                with patch('mcp_server_sota.IndexerIntegration') as MockIndexer:
                    # Create mock without run_indexer_on_demand
                    mock_indexer = Mock()
                    # Remove the method if it exists
                    if hasattr(mock_indexer, 'run_indexer_on_demand'):
                        delattr(mock_indexer, 'run_indexer_on_demand')
                    
                    MockIndexer.return_value = mock_indexer
                    
                    result = await index_rebuild(repository="test-repo")
                    
                    assert result["status"] == "error"
                    assert "not_supported_by_integration" in result["error"]["code"]
    
    @pytest.mark.asyncio
    async def test_index_rebuild_tries_alternative_methods(self):
        """Test index_rebuild tries alternative method names."""
        with patch('mcp_server_sota._is_admin', return_value=True):
            with patch('mcp_server_sota.AZURE_ADMIN_SUPPORT', True):
                with patch('mcp_server_sota.IndexerIntegration') as MockIndexer:
                    # Create mock with run_indexer instead
                    mock_indexer = Mock()
                    if hasattr(mock_indexer, 'run_indexer_on_demand'):
                        delattr(mock_indexer, 'run_indexer_on_demand')
                    mock_indexer.run_indexer = AsyncMock(return_value={"status": "started"})
                    
                    MockIndexer.return_value = mock_indexer
                    
                    result = await index_rebuild(repository="test-repo")
                    
                    assert result["status"] == "success"
                    assert result["data"]["result"]["status"] == "started"
                    mock_indexer.run_indexer.assert_called_once()


class TestTimerClass:
    """Test the _Timer utility class."""
    
    def test_timer_basic_functionality(self):
        """Test timer marks and duration calculation."""
        timer = _Timer()
        
        # Should start with "start" mark
        assert "start" in timer._marks
        
        # Add some marks
        timer.mark("step1")
        timer.mark("step2")
        timer.mark("done")
        
        durations = timer.durations()
        
        # Check expected duration keys
        assert "start→step1" in durations
        assert "step1→step2" in durations
        assert "step2→done" in durations
        assert "total" in durations
        
        # All durations should be positive
        for duration in durations.values():
            assert duration >= 0


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])