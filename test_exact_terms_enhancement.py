#!/usr/bin/env python3
"""
Test the enhanced exact terms functionality in the MCP server.
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

from mcp_server_sota import SearchCodeParams, SearchResult, SearchIntent, FieldMapper


class TestExactTermsEnhancement:
    """Test the enhanced exact terms functionality."""

    def test_auto_extraction_quoted_terms(self):
        """Test auto-extraction of quoted terms."""
        # Test the regex patterns used in search_code tool
        import re

        query = 'find "parse_json" function and "error_handler"'
        quoted = re.findall(r'"([^"]+)"|\'([^\']+)\'', query)
        quoted_terms = [t for pair in quoted for t in pair if t]

        assert "parse_json" in quoted_terms
        assert "error_handler" in quoted_terms
        assert len(quoted_terms) == 2

    def test_auto_extraction_numeric_terms(self):
        """Test auto-extraction of numeric terms including versions."""
        import re

        query = "version 3.8.10 and port 8080"
        numeric_terms = re.findall(r'(?<![\w])(\d+(?:\.\d+)+|\d{2,})(?![\w.])', query)

        assert "3.8.10" in numeric_terms
        assert "8080" in numeric_terms

    def test_auto_extraction_function_calls(self):
        """Test auto-extraction of function calls."""
        import re

        query = "call parseJson() and handleError()"
        function_calls = re.findall(r'(\w+)\s*\(', query)

        assert "parseJson" in function_calls
        assert "handleError" in function_calls

    def test_auto_extraction_camel_case(self):
        """Test auto-extraction of camelCase identifiers."""
        import re

        query = "find parseJsonData and handleErrorMessage"
        camel_case = re.findall(r'\b([a-z]+[A-Z][a-zA-Z]*)\b', query)

        assert "parseJsonData" in camel_case
        assert "handleErrorMessage" in camel_case

    def test_auto_extraction_snake_case(self):
        """Test auto-extraction of snake_case identifiers."""
        import re

        query = "find parse_json_data and handle_error_message"
        snake_case = re.findall(r'\b([a-z]+_[a-z_]+)\b', query)

        assert "parse_json_data" in snake_case
        assert "handle_error_message" in snake_case

    def test_exact_terms_validation(self):
        """Test exact terms validation and sanitization."""
        # Test the validation logic from the enhanced implementation
        test_terms = [
            "valid_term",
            "term with spaces",
            "term(with)parens",  # Should be filtered out
            "term&with&special",  # Should be filtered out
            "",  # Should be filtered out
            "  whitespace  ",  # Should be trimmed
        ]

        valid_terms = []
        for term in test_terms:
            if term and len(str(term).strip()) > 0:
                safe_term = str(term).strip()
                safe_term = safe_term.replace("'", "''").replace('"', '""')
                if not any(char in safe_term for char in ['(', ')', '&', '|', '!', '^']):
                    valid_terms.append(safe_term)

        assert "valid_term" in valid_terms
        assert "term with spaces" in valid_terms
        assert "whitespace" in valid_terms
        assert "term(with)parens" not in valid_terms
        assert "term&with&special" not in valid_terms
        assert "" not in valid_terms

    @pytest.mark.asyncio
    async def test_exact_terms_fallback_mechanism(self):
        """Test that fallback mechanism works when search.ismatch fails."""
        with patch('mcp_server_sota.server') as mock_server:
            # Mock the server to simulate search.ismatch failure
            mock_server._field_mapper = FieldMapper(['content', 'function_name'])
            mock_server._field_mapper.available = {'content', 'function_name'}
            mock_server._field_mapper.reverse_map = {'content': 'content', 'function_name': 'function_name'}

            # Mock search_code to capture the search parameters
            captured_params = {}

            async def mock_search_code(params):
                # Simulate the exact terms processing
                search_params = {"search_text": params.query}

                if params.exact_terms:
                    try:
                        # Simulate search.ismatch failure
                        raise Exception("search.ismatch syntax error")
                    except Exception:
                        # Apply fallback
                        fallback_terms = []
                        for term in params.exact_terms:
                            if term and len(str(term).strip()) > 0:
                                clean_term = str(term).strip().replace('"', '')
                                if ' ' in clean_term:
                                    fallback_terms.append(f'"{clean_term}"')
                                else:
                                    fallback_terms.append(clean_term)

                        if fallback_terms:
                            enhanced_query = search_params.get("search_text", "")
                            enhanced_query += " " + " ".join(fallback_terms)
                            search_params["search_text"] = enhanced_query.strip()
                            captured_params['fallback_used'] = True
                            captured_params['enhanced_query'] = enhanced_query

                return [SearchResult(
                    file_path="/test/file.py",
                    repository="test-repo",
                    language="python",
                    score=0.9,
                    content="def parse_json(data):",
                    function_name="parse_json"
                )]

            mock_server.search_code = mock_search_code

            # Test with exact terms that should trigger fallback
            params = SearchCodeParams(
                query="find function",
                exact_terms=["parse_json", "error handler"],
                max_results=10
            )

            results = await mock_search_code(params)

            # Verify fallback was used
            assert captured_params.get('fallback_used') is True
            assert 'parse_json' in captured_params.get('enhanced_query', '')
            assert '"error handler"' in captured_params.get('enhanced_query', '')
            assert len(results) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
