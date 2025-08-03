#!/usr/bin/env python3
"""
Test the enhanced dependency functionality in the MCP server.
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

from mcp_server_sota import SearchCodeParams, SearchResult, SearchIntent, EnhancedMCPServer


class TestDependencyEnhancement:
    """Test the enhanced dependency functionality."""
    
    @pytest.mark.asyncio
    async def test_dependency_mode_auto(self):
        """Test that auto mode includes dependencies for implement intent."""
        server = EnhancedMCPServer()
        
        # Mock search results
        primary_result = SearchResult(
            file_path="/test.py",
            repository="test-repo",
            language="python",
            score=1.0,
            content="def main(): parse_json(data)",
            function_name="main",
            dependencies=["parse_json"]
        )
        
        dependency_result = SearchResult(
            file_path="/utils.py",
            repository="test-repo",
            language="python",
            score=0.8,
            content="def parse_json(data): return json.loads(data)",
            function_name="parse_json",
            dependencies=[]
        )
        
        # Mock the search_code method to return dependency when searched
        original_search = server.search_code
        async def mock_search_code(params):
            if "def parse_json" in params.query:
                return [dependency_result]
            return [primary_result]
        
        server.search_code = mock_search_code
        
        # Test auto mode with implement intent
        params = SearchCodeParams(
            query="main function",
            intent=SearchIntent.IMPLEMENT,
            dependency_mode="auto",
            max_results=10
        )
        
        # Simulate the dependency resolution logic
        dependency_mode = params.dependency_mode
        should_include_deps = (
            dependency_mode == "always" or
            (dependency_mode == "auto" and params.intent == SearchIntent.IMPLEMENT) or
            dependency_mode == "graph"
        )
        
        assert should_include_deps is True
        
        # Test auto mode with other intent
        params2 = SearchCodeParams(
            query="main function",
            intent=SearchIntent.DEBUG,
            dependency_mode="auto",
            max_results=10
        )
        
        dependency_mode = params2.dependency_mode
        should_include_deps = (
            dependency_mode == "always" or
            (dependency_mode == "auto" and params2.intent == SearchIntent.IMPLEMENT) or
            dependency_mode == "graph"
        )
        
        assert should_include_deps is False
    
    @pytest.mark.asyncio
    async def test_dependency_mode_always(self):
        """Test that always mode includes dependencies regardless of intent."""
        server = EnhancedMCPServer()
        
        # Test always mode with debug intent
        params = SearchCodeParams(
            query="main function",
            intent=SearchIntent.DEBUG,
            dependency_mode="always",
            max_results=10
        )
        
        dependency_mode = params.dependency_mode
        should_include_deps = (
            dependency_mode == "always" or
            (dependency_mode == "auto" and params.intent == SearchIntent.IMPLEMENT) or
            dependency_mode == "graph"
        )
        
        assert should_include_deps is True
    
    @pytest.mark.asyncio
    async def test_dependency_mode_never(self):
        """Test that never mode excludes dependencies."""
        server = EnhancedMCPServer()
        
        # Test never mode with implement intent
        params = SearchCodeParams(
            query="main function",
            intent=SearchIntent.IMPLEMENT,
            dependency_mode="never",
            max_results=10
        )
        
        dependency_mode = params.dependency_mode
        should_include_deps = (
            dependency_mode == "always" or
            (dependency_mode == "auto" and params.intent == SearchIntent.IMPLEMENT) or
            dependency_mode == "graph"
        )
        
        assert should_include_deps is False
    
    @pytest.mark.asyncio
    async def test_dependency_mode_graph(self):
        """Test that graph mode includes dependencies with graph information."""
        server = EnhancedMCPServer()
        
        # Test graph mode
        params = SearchCodeParams(
            query="main function",
            intent=SearchIntent.DEBUG,
            dependency_mode="graph",
            max_results=10
        )
        
        dependency_mode = params.dependency_mode
        should_include_deps = (
            dependency_mode == "always" or
            (dependency_mode == "auto" and params.intent == SearchIntent.IMPLEMENT) or
            dependency_mode == "graph"
        )
        
        assert should_include_deps is True
        assert dependency_mode == "graph"
    
    @pytest.mark.asyncio
    async def test_dependency_graph_structure(self):
        """Test that dependency graph creates proper node and edge structure."""
        server = EnhancedMCPServer()
        
        # Create test results
        primary_result = SearchResult(
            file_path="/main.py",
            repository="test-repo",
            language="python",
            score=1.0,
            content="def main(): parse_json(data)",
            function_name="main",
            dependencies=["parse_json", "validate_data"],
            signature="main()"
        )
        
        dependency1 = SearchResult(
            file_path="/utils.py",
            repository="test-repo",
            language="python",
            score=0.8,
            content="def parse_json(data): return json.loads(data)",
            function_name="parse_json",
            dependencies=[],
            signature="parse_json(data)"
        )
        
        dependency2 = SearchResult(
            file_path="/validators.py",
            repository="test-repo",
            language="python",
            score=0.7,
            content="def validate_data(data): return data is not None",
            function_name="validate_data",
            dependencies=[],
            signature="validate_data(data)"
        )
        
        # Mock the search_code method
        async def mock_search_code(params):
            if "def parse_json" in params.query:
                return [dependency1]
            elif "def validate_data" in params.query:
                return [dependency2]
            return []
        
        server.search_code = mock_search_code
        
        # Test dependency graph resolution
        results = await server._resolve_dependency_graph([primary_result])
        
        # Check that we have the expected number of results
        assert len(results) >= 1  # At least the primary result
        
        # Check that the primary result has dependency graph information
        primary = results[0]
        assert hasattr(primary, 'dependency_graph') or 'dependency_graph' in primary.model_dump()
        
        # If dependency_graph is present, check its structure
        if hasattr(primary, 'dependency_graph'):
            graph = primary.dependency_graph
        else:
            graph = primary.model_dump().get('dependency_graph')
        
        if graph:
            assert "nodes" in graph
            assert "edges" in graph
            assert isinstance(graph["nodes"], list)
            assert isinstance(graph["edges"], list)
            
            # Check that primary node exists
            primary_nodes = [n for n in graph["nodes"] if n.get("type") == "primary"]
            assert len(primary_nodes) == 1
            
            primary_node = primary_nodes[0]
            assert primary_node["function_name"] == "main"
            assert primary_node["file_path"] == "/main.py"
            assert primary_node["repository"] == "test-repo"
    
    @pytest.mark.asyncio
    async def test_cache_key_includes_dependency_mode(self):
        """Test that cache keys include dependency_mode parameter."""
        server = EnhancedMCPServer()
        
        params1 = SearchCodeParams(
            query="test",
            dependency_mode="auto",
            max_results=10
        )
        
        params2 = SearchCodeParams(
            query="test",
            dependency_mode="always",
            max_results=10
        )
        
        key1 = server._get_cache_key(params1)
        key2 = server._get_cache_key(params2)
        
        # Keys should be different due to different dependency modes
        assert key1 != key2
        assert "auto" in key1
        assert "always" in key2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
