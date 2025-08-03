#!/usr/bin/env python3
"""
Test the enhanced timing functionality in the MCP server.
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

from mcp_server_sota import search_code, _Timer


class TestTimingEnhancement:
    """Test the enhanced timing functionality."""

    def test_timer_functionality(self):
        """Test _Timer class provides accurate timing information."""
        timer = _Timer()

        # Simulate some work with marks
        timer.mark("step1")
        timer.mark("step2")
        timer.mark("step3")

        durations = timer.durations()

        # Check that all expected timing keys are present
        assert "start→step1" in durations
        assert "step1→step2" in durations
        assert "step2→step3" in durations
        assert "total" in durations

        # Check that durations are reasonable (non-negative)
        for key, duration in durations.items():
            assert duration >= 0, f"Duration for {key} should be non-negative"

        # Check that total is approximately sum of parts
        parts_sum = durations["start→step1"] + durations["step1→step2"] + durations["step2→step3"]
        assert abs(durations["total"] - parts_sum) < 10, "Total should be approximately sum of parts"

    @pytest.mark.asyncio
    async def test_search_code_basic_timings(self):
        """Test that search_code returns basic timing information."""
        with patch('mcp_server_sota.server') as mock_server:
            # Mock the server's search_code method
            mock_server.search_code = AsyncMock(return_value=[])
            mock_server._last_total_count = 0
            mock_server._query_cache = {}
            mock_server._query_cache_ts = {}
            mock_server._ttl_seconds = 60
            mock_server._cache_max_entries = 500
            mock_server._last_search_params = {}

            # Call search_code with include_timings=False (default)
            result = await search_code(
                query="test query",
                include_timings=False
            )

            # Check that basic timing info is present
            assert result["ok"] is True
            data = result["data"]
            assert "took_ms" in data
            assert "timings_ms" in data  # Always included for backwards compatibility
            assert "cache_status" in data

            # Check that detailed timings are NOT included by default
            assert "stages" not in data
            assert "server_timings_ms" not in data

    @pytest.mark.asyncio
    async def test_search_code_detailed_timings(self):
        """Test that search_code returns detailed timing information when requested."""
        with patch('mcp_server_sota.server') as mock_server:
            # Mock the server's search_code method
            mock_server.search_code = AsyncMock(return_value=[])
            mock_server._last_total_count = 0
            mock_server._query_cache = {}
            mock_server._query_cache_ts = {}
            mock_server._ttl_seconds = 60
            mock_server._cache_max_entries = 500
            mock_server._last_search_params = {}

            # Mock detailed server timings
            mock_server._last_search_timings = {
                "start→cache_check": 1.0,
                "cache_check→query_enhanced": 2.0,
                "query_enhanced→repo_resolved": 1.5,
                "repo_resolved→params_built": 0.5,
                "params_built→exact_terms_applied": 1.0,
                "exact_terms_applied→acs_search_complete": 50.0,
                "acs_search_complete→results_fetched": 5.0,
                "results_fetched→filtered_ranked": 3.0,
                "filtered_ranked→results_converted": 2.0
            }

            # Call search_code with include_timings=True
            result = await search_code(
                query="test query",
                include_timings=True
            )

            # Check that detailed timing info is present
            assert result["ok"] is True
            data = result["data"]
            assert "took_ms" in data
            assert "timings_ms" in data
            assert "server_timings_ms" in data
            assert "stages" in data
            assert "cache_status" in data

            # Check that stages are properly formatted
            stages = data["stages"]
            assert isinstance(stages, list)
            assert len(stages) > 0

            # Check that each stage has required fields
            for stage in stages:
                assert "stage" in stage
                assert "duration_ms" in stage
                assert isinstance(stage["duration_ms"], (int, float))
                assert stage["duration_ms"] >= 0

            # Check that expected stages are present
            stage_names = [stage["stage"] for stage in stages]
            expected_stages = [
                "cache_check", "query_enhancement", "repo_resolution",
                "param_building", "exact_term_filtering", "azure_search",
                "result_fetch", "filter_rank", "convert_results"
            ]
            for expected_stage in expected_stages:
                assert expected_stage in stage_names, f"Expected stage {expected_stage} not found"

    @pytest.mark.asyncio
    async def test_search_code_debug_mode_timings(self):
        """Test that search_code returns detailed timings in debug mode."""
        with patch('mcp_server_sota.server') as mock_server:
            with patch.dict(os.environ, {"MCP_DEBUG_TIMINGS": "1"}):
                # Mock the server's search_code method
                mock_server.search_code = AsyncMock(return_value=[])
                mock_server._last_total_count = 0
                mock_server._query_cache = {}
                mock_server._query_cache_ts = {}
                mock_server._ttl_seconds = 60
                mock_server._cache_max_entries = 500
                mock_server._last_search_params = {}
                mock_server._last_search_timings = {
                    "start→cache_check": 1.0,
                    "exact_terms_applied→acs_search_complete": 50.0
                }

                # Call search_code with include_timings=False but debug mode enabled
                result = await search_code(
                    query="test query",
                    include_timings=False  # Should still get detailed timings due to debug mode
                )

                # Check that detailed timing info is present due to debug mode
                assert result["ok"] is True
                data = result["data"]
                assert "server_timings_ms" in data
                assert "stages" in data

    @pytest.mark.asyncio
    async def test_cache_key_exposure_in_debug_mode(self):
        """Test that cache key is only exposed in debug/timing mode."""
        with patch('mcp_server_sota.server') as mock_server:
            # Mock the server's search_code method
            mock_server.search_code = AsyncMock(return_value=[])
            mock_server._last_total_count = 0
            mock_server._query_cache = {}
            mock_server._query_cache_ts = {}
            mock_server._ttl_seconds = 60
            mock_server._cache_max_entries = 500
            mock_server._last_search_params = {}

            # Test without detailed timings - cache key should be None
            result = await search_code(
                query="test query",
                include_timings=False
            )

            data = result["data"]
            assert data["cache_status"]["key"] is None

            # Test with detailed timings - cache key should be present
            result = await search_code(
                query="test query",
                include_timings=True
            )

            data = result["data"]
            assert data["cache_status"]["key"] is not None
            assert isinstance(data["cache_status"]["key"], str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
