#!/usr/bin/env python3
"""
Test the fault-tolerant docs handling in search_code_then_docs.
"""

import asyncio
import os
import sys
import pytest
from unittest.mock import Mock, AsyncMock, patch

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock the environment before importing
os.environ["ACS_ENDPOINT"] = "https://test.search.windows.net"
os.environ["ACS_ADMIN_KEY"] = "test-key"
os.environ["ACS_INDEX_NAME"] = "test-index"

from mcp_server_sota import search_code_then_docs, SearchCodeParams, SearchResult


class TestDocsFaultTolerance:
    """Test the fault-tolerant docs handling functionality."""
    
    @pytest.mark.asyncio
    async def test_configurable_threshold(self):
        """Test that docs search threshold is configurable."""
        with patch('mcp_server_sota.server') as mock_server:
            with patch('mcp_server_sota.DOCS_SUPPORT', True):
                with patch('mcp_server_sota.MicrosoftDocsMCPClient') as mock_client_class:
                    # Mock server search_code to return few results
                    mock_server.search_code = AsyncMock(return_value=[
                        SearchResult(
                            file_path="/test.py", repository="test-repo", language="python",
                            score=1.0, content="test content"
                        )
                    ])
                    
                    # Mock docs client
                    mock_client = AsyncMock()
                    mock_client.search_docs = AsyncMock(return_value=["doc1", "doc2"])
                    mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                    mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)
                    
                    # Test with default threshold (0.5)
                    result = await search_code_then_docs(
                        query="test query",
                        max_code_results=4,  # 1 result < 4*0.5=2, should trigger docs
                        max_doc_results=5
                    )
                    
                    assert result["ok"] is True
                    data = result["data"]
                    assert data["docs_attempted"] is True
                    assert data["docs_success"] is True
                    
                    # Test with higher threshold (0.8)
                    result = await search_code_then_docs(
                        query="test query",
                        max_code_results=4,  # 1 result < 4*0.8=3.2, should trigger docs
                        docs_threshold=0.8
                    )
                    
                    data = result["data"]
                    assert data["docs_attempted"] is True
                    
                    # Test with lower threshold (0.2)
                    result = await search_code_then_docs(
                        query="test query",
                        max_code_results=4,  # 1 result > 4*0.2=0.8, should NOT trigger docs
                        docs_threshold=0.2
                    )
                    
                    data = result["data"]
                    assert data["docs_attempted"] is False
    
    @pytest.mark.asyncio
    async def test_retry_logic(self):
        """Test that retry logic works correctly."""
        with patch('mcp_server_sota.server') as mock_server:
            with patch('mcp_server_sota.DOCS_SUPPORT', True):
                with patch('mcp_server_sota.MicrosoftDocsMCPClient') as mock_client_class:
                    # Mock server search_code to return few results
                    mock_server.search_code = AsyncMock(return_value=[])
                    
                    # Mock docs client that fails twice then succeeds
                    mock_client = AsyncMock()
                    call_count = 0
                    
                    async def mock_search_docs(*args, **kwargs):
                        nonlocal call_count
                        call_count += 1
                        if call_count <= 2:
                            raise Exception("Temporary failure")
                        return ["doc1", "doc2"]
                    
                    mock_client.search_docs = mock_search_docs
                    mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                    mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)
                    
                    # Test with retry enabled
                    result = await search_code_then_docs(
                        query="test query",
                        max_code_results=5,
                        retry_docs=True
                    )
                    
                    assert result["ok"] is True
                    data = result["data"]
                    assert data["docs_attempted"] is True
                    assert data["docs_success"] is True
                    assert data["retry_attempts"] == 3  # Failed twice, succeeded on third
                    assert "docs_results" in data
    
    @pytest.mark.asyncio
    async def test_retry_disabled(self):
        """Test behavior when retry is disabled."""
        with patch('mcp_server_sota.server') as mock_server:
            with patch('mcp_server_sota.DOCS_SUPPORT', True):
                with patch('mcp_server_sota.MicrosoftDocsMCPClient') as mock_client_class:
                    # Mock server search_code to return few results
                    mock_server.search_code = AsyncMock(return_value=[])
                    
                    # Mock docs client that always fails
                    mock_client = AsyncMock()
                    mock_client.search_docs = AsyncMock(side_effect=Exception("Service unavailable"))
                    mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                    mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)
                    
                    # Test with retry disabled
                    result = await search_code_then_docs(
                        query="test query",
                        max_code_results=5,
                        retry_docs=False
                    )
                    
                    assert result["ok"] is True
                    data = result["data"]
                    assert data["docs_attempted"] is True
                    assert data["docs_success"] is False
                    assert data["retry_attempts"] == 1  # Only one attempt
                    assert "docs_error" in data
                    assert "Service unavailable" in data["docs_error"]
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test that timeout is handled correctly."""
        with patch('mcp_server_sota.server') as mock_server:
            with patch('mcp_server_sota.DOCS_SUPPORT', True):
                with patch('mcp_server_sota.MicrosoftDocsMCPClient') as mock_client_class:
                    # Mock server search_code to return few results
                    mock_server.search_code = AsyncMock(return_value=[])
                    
                    # Mock docs client that times out
                    mock_client = AsyncMock()
                    
                    async def slow_search_docs(*args, **kwargs):
                        await asyncio.sleep(2)  # Simulate slow response
                        return ["doc1"]
                    
                    mock_client.search_docs = slow_search_docs
                    mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                    mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)
                    
                    # Test with short timeout
                    result = await search_code_then_docs(
                        query="test query",
                        max_code_results=5,
                        timeout_seconds=1,  # 1 second timeout
                        retry_docs=False
                    )
                    
                    assert result["ok"] is True
                    data = result["data"]
                    assert data["docs_attempted"] is True
                    assert data["docs_success"] is False
                    assert "docs_error" in data
                    assert "Timeout" in data["docs_error"]
    
    @pytest.mark.asyncio
    async def test_recommendations_generation(self):
        """Test that recommendations are generated when few results found."""
        with patch('mcp_server_sota.server') as mock_server:
            # Mock server search_code to return few results
            mock_server.search_code = AsyncMock(return_value=[
                SearchResult(
                    file_path="/test.py", repository="test-repo", language="python",
                    score=1.0, content="test content"
                )
            ])
            
            # Test with few results
            result = await search_code_then_docs(
                query="test query",
                max_code_results=10  # 1 result < 10/2=5, should generate recommendations
            )
            
            assert result["ok"] is True
            data = result["data"]
            assert "recommendations" in data
            assert isinstance(data["recommendations"], list)
            assert len(data["recommendations"]) > 0
            
            # Check that recommendations contain useful suggestions
            recommendations_text = " ".join(data["recommendations"])
            assert "broader search terms" in recommendations_text
            assert "repository" in recommendations_text
            assert "intent" in recommendations_text
    
    @pytest.mark.asyncio
    async def test_performance_metrics(self):
        """Test that performance metrics are included in response."""
        with patch('mcp_server_sota.server') as mock_server:
            # Mock server search_code to return some results
            mock_server.search_code = AsyncMock(return_value=[
                SearchResult(
                    file_path="/test1.py", repository="test-repo", language="python",
                    score=1.0, content="test content 1"
                ),
                SearchResult(
                    file_path="/test2.py", repository="test-repo", language="python",
                    score=0.8, content="test content 2"
                )
            ])
            
            result = await search_code_then_docs(
                query="test query",
                max_code_results=5,
                docs_threshold=0.6
            )
            
            assert result["ok"] is True
            data = result["data"]
            assert "performance" in data
            
            performance = data["performance"]
            assert "code_results_count" in performance
            assert "docs_threshold_used" in performance
            assert "docs_threshold_met" in performance
            
            assert performance["code_results_count"] == 2
            assert performance["docs_threshold_used"] == 3  # 5 * 0.6 = 3
            assert performance["docs_threshold_met"] is False  # 2 < 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
