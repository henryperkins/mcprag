#!/usr/bin/env python3
"""
Test the Azure ranking explanation functionality in the MCP server.
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

from mcp_server_sota import EnhancedMCPServer


class TestAzureRankingEnhancement:
    """Test the Azure ranking explanation functionality."""
    
    @pytest.mark.asyncio
    async def test_azure_ranking_explanation_structure(self):
        """Test that Azure ranking explanations have proper structure."""
        server = EnhancedMCPServer()
        
        # Mock search client
        mock_search_client = Mock()
        mock_response = Mock()
        mock_response.get_count.return_value = 2
        
        # Mock detailed search results with Azure Search metadata
        mock_detailed_results = [
            {
                '@search.score': 1.5,
                '@search.features': {
                    'tf_idf_content': 0.8,
                    'tf_idf_function_name': 0.3,
                    'freshness_boost': 0.1
                },
                '@search.reranker_score': 2.1,
                'file_path': '/test1.py',
                'repository': 'test-repo',
                'content': 'def parse_json(data): return json.loads(data)',
                'function_name': 'parse_json'
            },
            {
                '@search.score': 1.2,
                '@search.features': {
                    'tf_idf_content': 0.6,
                    'tf_idf_function_name': 0.5
                },
                'file_path': '/test2.py',
                'repository': 'test-repo',
                'content': 'def handle_json_error(e): print(e)',
                'function_name': 'handle_json_error'
            }
        ]
        
        mock_search_client.search.return_value = mock_detailed_results
        server.search_client = mock_search_client
        server._semantic_available = True
        
        # Test input results
        test_results = [
            {
                'file_path': '/test1.py',
                'repository': 'test-repo',
                'score': 1.5,
                'content': 'def parse_json(data): return json.loads(data)',
                'function_name': 'parse_json'
            },
            {
                'file_path': '/test2.py',
                'repository': 'test-repo',
                'score': 1.2,
                'content': 'def handle_json_error(e): print(e)',
                'function_name': 'handle_json_error'
            }
        ]
        
        # Test Azure ranking explanation
        explanations = await server._get_azure_ranking_explanation("parse json", test_results)
        
        # Verify structure
        assert len(explanations) == 2
        
        for explanation in explanations:
            assert "file_path" in explanation
            assert "repository" in explanation
            assert "score" in explanation
            assert "factors" in explanation
            assert "summary" in explanation
            assert isinstance(explanation["factors"], list)
            
            # Check for Azure-specific factors
            factor_types = [f.get("type") for f in explanation["factors"]]
            assert "azure_feature" in factor_types or "content_analysis" in factor_types
    
    @pytest.mark.asyncio
    async def test_azure_ranking_with_semantic_features(self):
        """Test Azure ranking explanations include semantic features when available."""
        server = EnhancedMCPServer()
        
        # Mock search client with semantic features
        mock_search_client = Mock()
        mock_detailed_results = [
            {
                '@search.score': 1.8,
                '@search.reranker_score': 2.5,  # Semantic reranker score
                '@search.features': {
                    'tf_idf_content': 0.9,
                    'semantic_similarity': 0.85
                },
                'file_path': '/semantic_test.py',
                'repository': 'test-repo',
                'content': 'def process_data(input_data): return transform(input_data)',
                'function_name': 'process_data'
            }
        ]
        
        mock_search_client.search.return_value = mock_detailed_results
        server.search_client = mock_search_client
        server._semantic_available = True
        
        test_results = [
            {
                'file_path': '/semantic_test.py',
                'repository': 'test-repo',
                'score': 1.8,
                'content': 'def process_data(input_data): return transform(input_data)',
                'function_name': 'process_data'
            }
        ]
        
        explanations = await server._get_azure_ranking_explanation("process data", test_results)
        
        # Check for semantic ranking factors
        semantic_factors = []
        for explanation in explanations:
            for factor in explanation["factors"]:
                if factor.get("type") == "semantic":
                    semantic_factors.append(factor)
        
        assert len(semantic_factors) > 0
        semantic_factor = semantic_factors[0]
        assert semantic_factor["name"] == "semantic_reranker_score"
        assert semantic_factor["value"] == 2.5
    
    @pytest.mark.asyncio
    async def test_azure_ranking_fallback_to_heuristic(self):
        """Test that Azure ranking falls back to heuristic when Azure features fail."""
        server = EnhancedMCPServer()
        
        # Mock search client that raises an exception
        mock_search_client = Mock()
        mock_search_client.search.side_effect = Exception("Azure Search unavailable")
        server.search_client = mock_search_client
        
        test_results = [
            {
                'file_path': '/fallback_test.py',
                'repository': 'test-repo',
                'score': 1.0,
                'content': 'def test_function(): pass',
                'function_name': 'test_function',
                'signature': 'test_function()'
            }
        ]
        
        # Should fall back to heuristic explanations
        explanations = await server._get_azure_ranking_explanation("test function", test_results)
        
        # Verify fallback worked
        assert len(explanations) == 1
        explanation = explanations[0]
        assert "factors" in explanation
        
        # Check for heuristic factors
        factor_names = [f.get("name") for f in explanation["factors"]]
        assert "term_overlap" in factor_names
        assert "base_score" in factor_names
    
    def test_heuristic_explanations_structure(self):
        """Test that heuristic explanations have proper structure."""
        server = EnhancedMCPServer()
        
        test_results = [
            {
                'file_path': '/heuristic_test.py',
                'repository': 'test-repo',
                'score': 0.8,
                'content': 'def parse_json_data(input): return json.loads(input)',
                'function_name': 'parse_json_data',
                'signature': 'parse_json_data(input)'
            }
        ]
        
        explanations = server._get_heuristic_explanations("parse json", test_results)
        
        assert len(explanations) == 1
        explanation = explanations[0]
        
        # Check structure
        assert "file_path" in explanation
        assert "repository" in explanation
        assert "score" in explanation
        assert "factors" in explanation
        assert "summary" in explanation
        
        # Check factors
        factors = explanation["factors"]
        factor_names = [f.get("name") for f in factors]
        
        # Should have term overlap since "parse" and "json" are in content
        assert "term_overlap" in factor_names
        assert "repo_presence" in factor_names
        assert "signature_match" in factor_names
        assert "base_score" in factor_names
        
        # Check term overlap calculation
        term_overlap_factor = next(f for f in factors if f["name"] == "term_overlap")
        assert term_overlap_factor["weight"] == 0.4
        assert term_overlap_factor["contribution"] > 0  # Should have some overlap
    
    def test_content_and_function_name_analysis(self):
        """Test that content and function name analysis works correctly."""
        server = EnhancedMCPServer()
        
        # Mock search client for Azure explanation
        mock_search_client = Mock()
        mock_detailed_results = [
            {
                '@search.score': 1.0,
                'file_path': '/analysis_test.py',
                'repository': 'test-repo',
                'content': 'def parse_json_data(data): return json.loads(data)',
                'function_name': 'parse_json_data'
            }
        ]
        
        mock_search_client.search.return_value = mock_detailed_results
        server.search_client = mock_search_client
        server._semantic_available = False
        
        test_results = [
            {
                'file_path': '/analysis_test.py',
                'repository': 'test-repo',
                'score': 1.0,
                'content': 'def parse_json_data(data): return json.loads(data)',
                'function_name': 'parse_json_data'
            }
        ]
        
        # Run the test synchronously since we're mocking the async parts
        import asyncio
        explanations = asyncio.run(server._get_azure_ranking_explanation("parse json", test_results))
        
        # Check for content and function name analysis
        explanation = explanations[0]
        factors = explanation["factors"]
        
        content_factors = [f for f in factors if f.get("type") == "content_analysis"]
        function_factors = [f for f in factors if f.get("type") == "function_analysis"]
        
        # Should have content matches for "parse" and "json"
        assert len(content_factors) > 0
        content_factor = content_factors[0]
        assert content_factor["name"] == "content_term_matches"
        assert content_factor["value"] >= 2  # "parse" and "json" both match
        
        # Should have function name matches
        assert len(function_factors) > 0
        function_factor = function_factors[0]
        assert function_factor["name"] == "function_name_matches"
        assert function_factor["value"] >= 2  # "parse" and "json" both in function name


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
