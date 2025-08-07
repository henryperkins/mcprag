"""Comprehensive tests for search_code validation and fixes."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, List

from mcprag.mcp.tools._helpers.input_validation import (
    validate_query,
    validate_max_results,
    validate_skip,
    validate_language,
    validate_detail_level,
    validate_orderby,
    validate_snippet_lines,
    validate_exact_terms,
    validate_all_search_params,
    MAX_QUERY_LENGTH,
    MAX_QUERY_WORDS,
    MAX_RESULTS_LIMIT,
)

from mcprag.mcp.tools._helpers.data_consistency import (
    ensure_consistent_fields,
    ensure_consistent_response,
    fix_pagination_consistency,
    deduplicate_results,
    infer_language_from_file,
    infer_repository_from_path,
)


class TestInputValidation:
    """Test input validation functions."""
    
    def test_validate_query_empty(self):
        """Test that empty queries are rejected."""
        # Empty string
        is_valid, error, _ = validate_query("")
        assert not is_valid
        assert "empty" in error.lower()
        
        # Whitespace only
        is_valid, error, _ = validate_query("   \t\n  ")
        assert not is_valid
        assert "empty" in error.lower() or "whitespace" in error.lower()
        
        # None
        is_valid, error, _ = validate_query(None)
        assert not is_valid
        assert "none" in error.lower()
    
    def test_validate_query_length_limits(self):
        """Test query length validation."""
        # Too long
        long_query = "a" * (MAX_QUERY_LENGTH + 1)
        is_valid, error, sanitized = validate_query(long_query)
        assert not is_valid
        assert "exceeds maximum length" in error
        assert len(sanitized) == MAX_QUERY_LENGTH
        
        # At limit
        query_at_limit = "a" * MAX_QUERY_LENGTH
        is_valid, error, sanitized = validate_query(query_at_limit)
        assert is_valid
        assert error is None
        assert sanitized == query_at_limit
        
        # Valid length
        valid_query = "search for python functions"
        is_valid, error, sanitized = validate_query(valid_query)
        assert is_valid
        assert error is None
        assert sanitized == valid_query
    
    def test_validate_query_word_limit(self):
        """Test query word count validation."""
        # Too many words
        many_words_query = " ".join(["word"] * (MAX_QUERY_WORDS + 1))
        is_valid, error, _ = validate_query(many_words_query)
        assert not is_valid
        assert f"exceeds maximum of {MAX_QUERY_WORDS} words" in error
    
    def test_validate_query_dangerous_patterns(self):
        """Test that dangerous patterns are sanitized."""
        dangerous_queries = [
            "test; DROP TABLE users",
            "search <script>alert('xss')</script>",
            "query'; DELETE FROM data--",
            "javascript:alert(1)",
            "onclick=alert('test')",
            "${malicious_code}",
            "{{evil_template}}"
        ]
        
        for query in dangerous_queries:
            is_valid, error, sanitized = validate_query(query)
            # Should either reject or sanitize
            if is_valid:
                assert sanitized != query  # Must be sanitized
                assert "DROP" not in sanitized
                assert "<script>" not in sanitized
                assert "javascript:" not in sanitized
    
    def test_validate_max_results(self):
        """Test max_results validation."""
        # Negative value
        is_valid, error, value = validate_max_results(-5)
        assert not is_valid
        assert "at least" in error
        assert value == 1
        
        # Zero
        is_valid, error, value = validate_max_results(0)
        assert not is_valid
        assert value == 1
        
        # Valid value
        is_valid, error, value = validate_max_results(10)
        assert is_valid
        assert error is None
        assert value == 10
        
        # Over limit - should clamp
        is_valid, error, value = validate_max_results(50)
        assert is_valid  # Clamped, not rejected
        assert value == MAX_RESULTS_LIMIT
        
        # String input
        is_valid, error, value = validate_max_results("15")
        assert is_valid
        assert value == 15
        
        # Invalid type
        is_valid, error, value = validate_max_results("invalid")
        assert not is_valid
        assert "must be an integer" in error
    
    def test_validate_skip(self):
        """Test skip parameter validation."""
        # Negative
        is_valid, error, value = validate_skip(-10)
        assert not is_valid
        assert "cannot be negative" in error
        assert value == 0
        
        # Valid
        is_valid, error, value = validate_skip(100)
        assert is_valid
        assert value == 100
        
        # None (default)
        is_valid, error, value = validate_skip(None)
        assert is_valid
        assert value == 0
        
        # Too large
        is_valid, error, value = validate_skip(10000)
        assert not is_valid
        assert "exceeds maximum" in error
    
    def test_validate_language(self):
        """Test language validation."""
        # Valid language
        is_valid, error, value = validate_language("python")
        assert is_valid
        assert value == "python"
        
        # Invalid language
        is_valid, error, value = validate_language("brainfuck")
        assert not is_valid
        assert "Invalid language" in error
        
        # Case insensitive
        is_valid, error, value = validate_language("PYTHON")
        assert is_valid
        assert value == "python"
        
        # None/empty (valid)
        is_valid, error, value = validate_language(None)
        assert is_valid
        assert value is None
        
        is_valid, error, value = validate_language("")
        assert is_valid
        assert value is None
    
    def test_validate_detail_level(self):
        """Test detail_level validation."""
        # Valid levels
        for level in ["full", "compact", "ultra"]:
            is_valid, error, value = validate_detail_level(level)
            assert is_valid
            assert value == level
        
        # Invalid level
        is_valid, error, value = validate_detail_level("invalid")
        assert not is_valid
        assert "must be one of" in error
        assert value == "full"  # Default
        
        # Case insensitive
        is_valid, error, value = validate_detail_level("FULL")
        assert is_valid
        assert value == "full"
        
        # Empty/None defaults to full
        is_valid, error, value = validate_detail_level("")
        assert is_valid
        assert value == "full"
    
    def test_validate_snippet_lines(self):
        """Test snippet_lines validation."""
        # Valid
        is_valid, error, value = validate_snippet_lines(5)
        assert is_valid
        assert value == 5
        
        # Negative
        is_valid, error, value = validate_snippet_lines(-5)
        assert not is_valid
        assert "cannot be negative" in error
        assert value == 0
        
        # Too large - should clamp
        is_valid, error, value = validate_snippet_lines(200)
        assert is_valid
        assert value == 100  # Clamped
        
        # None defaults to 0
        is_valid, error, value = validate_snippet_lines(None)
        assert is_valid
        assert value == 0
    
    def test_validate_exact_terms(self):
        """Test exact_terms validation."""
        # Valid list
        is_valid, error, value = validate_exact_terms(["term1", "term2"])
        assert is_valid
        assert value == ["term1", "term2"]
        
        # None is valid
        is_valid, error, value = validate_exact_terms(None)
        assert is_valid
        assert value is None
        
        # Empty list becomes None
        is_valid, error, value = validate_exact_terms([])
        assert is_valid
        assert value is None
        
        # Non-string items filtered
        is_valid, error, value = validate_exact_terms(["valid", 123, None, "another"])
        assert is_valid
        assert value == ["valid", "another"]
        
        # Not a list
        is_valid, error, value = validate_exact_terms("not a list")
        assert not is_valid
        assert "must be a list" in error
    
    def test_validate_all_search_params(self):
        """Test comprehensive parameter validation."""
        # All valid params
        is_valid, error, params = validate_all_search_params(
            query="search query",
            intent="find functions",
            language="python",
            repository="test/repo",
            max_results=10,
            skip=0,
            orderby="relevance",
            detail_level="full",
            snippet_lines=5,
            exact_terms=["exact", "terms"]
        )
        assert is_valid
        assert params["query"] == "search query"
        assert params["language"] == "python"
        assert params["max_results"] == 10
        
        # Mixed valid/invalid - should handle gracefully
        is_valid, warnings, params = validate_all_search_params(
            query="valid query",
            intent="x" * 200,  # Too long, will be truncated
            language="invalid_lang",
            repository="test/repo",
            max_results=100,  # Over limit, will be clamped
            skip=-5,  # Negative, will be set to 0
            orderby="invalid",
            detail_level="invalid",
            snippet_lines=-10,
            exact_terms=None
        )
        assert is_valid  # Should still work with warnings
        assert params["query"] == "valid query"
        assert params["max_results"] == MAX_RESULTS_LIMIT
        assert params["skip"] == 0
        assert params["detail_level"] == "full"
        assert params["snippet_lines"] == 0


class TestDataConsistency:
    """Test data consistency functions."""
    
    def test_ensure_consistent_fields(self):
        """Test field consistency enforcement."""
        # Empty item
        item = {}
        result = ensure_consistent_fields(item)
        assert result["id"] != ""
        assert result["file"] == "unknown"
        assert result["repository"] == ""
        assert result["language"] == ""
        assert result["relevance"] == 0.0
        assert result["highlights"] == {}
        
        # Item with None values
        item = {
            "id": None,
            "file": None,
            "language": None,
            "start_line": None,
            "relevance": None
        }
        result = ensure_consistent_fields(item)
        assert result["id"] != ""
        assert result["file"] == "unknown"
        assert result["start_line"] is None
        assert result["relevance"] == 0.0
        
        # Item with invalid line numbers
        item = {
            "file": "test.py",
            "start_line": -5,
            "end_line": 0
        }
        result = ensure_consistent_fields(item)
        assert result["start_line"] == 1
        assert result["end_line"] == 1
        
        # Item with end_line < start_line
        item = {
            "file": "test.py",
            "start_line": 10,
            "end_line": 5
        }
        result = ensure_consistent_fields(item)
        assert result["end_line"] == result["start_line"]
    
    def test_infer_language_from_file(self):
        """Test language inference from file extension."""
        test_cases = [
            ("test.py", "python"),
            ("app.js", "javascript"),
            ("main.ts", "typescript"),
            ("Main.java", "java"),
            ("program.cs", "csharp"),
            ("code.cpp", "cpp"),
            ("script.rb", "ruby"),
            ("index.html", "html"),
            ("style.css", "css"),
            ("data.json", "json"),
            ("config.yaml", "yaml"),
            ("README.md", "markdown"),
            ("unknown.xyz", ""),
            ("", ""),
            (None, ""),
        ]
        
        for file_path, expected_language in test_cases:
            result = infer_language_from_file(file_path)
            assert result == expected_language
    
    def test_infer_repository_from_path(self):
        """Test repository inference from file path."""
        test_cases = [
            ("github.com/user/repo/src/file.py", "user/repo"),
            ("github.com:user/repo/file.py", "user/repo"),
            ("project/src/main.py", "project/src"),  # Actual behavior
            ("mylib/lib/utils.js", "mylib/lib"),      # Actual behavior
            ("/src/app.py", ""),
            ("file.py", ""),
            ("", ""),
            (None, ""),
        ]
        
        for file_path, expected_repo in test_cases:
            result = infer_repository_from_path(file_path)
            assert result == expected_repo
    
    def test_ensure_consistent_response(self):
        """Test response consistency enforcement."""
        # Empty response
        response = {}
        result = ensure_consistent_response(response)
        assert "items" in result
        assert result["items"] == []
        assert result["count"] == 0
        assert result["total"] == 0
        assert result["query"] == ""
        
        # Response with inconsistent count/total
        response = {
            "items": [{"file": "a.py"}, {"file": "b.py"}],
            "count": 5,  # Wrong
            "total": 1   # Wrong
        }
        result = ensure_consistent_response(response)
        assert result["count"] == 2  # Fixed
        assert result["total"] == 2  # Fixed
        
        # Response with empty exact_terms list
        response = {
            "items": [],
            "exact_terms": []
        }
        result = ensure_consistent_response(response)
        assert result["exact_terms"] is None  # Normalized
        
        # Response with pagination
        response = {
            "items": [{"file": f"file{i}.py"} for i in range(10)],
            "total": 25,
            "skip": 10
        }
        result = ensure_consistent_response(response)
        assert result["has_more"] is True
        assert result["next_skip"] == 20
    
    def test_fix_pagination_consistency(self):
        """Test pagination consistency fixes."""
        # Normal case
        items = [{"id": i} for i in range(10)]
        items, total, has_more, next_skip = fix_pagination_consistency(
            items, skip=0, max_results=10, total=25
        )
        assert len(items) == 10
        assert total == 25
        assert has_more is True
        assert next_skip == 10
        
        # Too many items returned
        items = [{"id": i} for i in range(30)]
        items, total, has_more, next_skip = fix_pagination_consistency(
            items, skip=0, max_results=10, total=25
        )
        assert len(items) == 10  # Clamped
        assert total == 25
        assert has_more is True
        
        # Last page
        items = [{"id": i} for i in range(5)]
        items, total, has_more, next_skip = fix_pagination_consistency(
            items, skip=20, max_results=10, total=25
        )
        assert len(items) == 5
        assert total == 25
        assert has_more is False
        assert next_skip is None
        
        # Total less than what we've seen
        items = [{"id": i} for i in range(10)]
        items, total, has_more, next_skip = fix_pagination_consistency(
            items, skip=20, max_results=10, total=15
        )
        assert total == 30  # Corrected
    
    def test_deduplicate_results(self):
        """Test result deduplication."""
        items = [
            {"file": "a.py", "start_line": 10, "relevance": 0.8},
            {"file": "a.py", "start_line": 10, "relevance": 0.9},  # Duplicate, higher score
            {"file": "b.py", "start_line": 20, "relevance": 0.7},
            {"file": "a.py", "start_line": 30, "relevance": 0.6},  # Different line
            {"file": "a.py", "start_line": 10, "relevance": 0.5},  # Duplicate, lower score
        ]
        
        result = deduplicate_results(items)
        
        # Should keep highest relevance for duplicates
        assert len(result) == 3
        
        # Check that highest relevance was kept for duplicate
        duplicate_item = next(
            item for item in result 
            if item["file"] == "a.py" and item["start_line"] == 10
        )
        assert duplicate_item["relevance"] == 0.9
        
        # Check sorting by relevance
        assert result[0]["relevance"] >= result[1]["relevance"]
        assert result[1]["relevance"] >= result[2]["relevance"]


class TestIntegrationScenarios:
    """Test complete scenarios with all validations."""
    
    @pytest.mark.asyncio
    async def test_empty_query_rejection(self):
        """Test that empty queries are properly rejected."""
        from mcprag.mcp.tools._helpers.search_impl import search_code_impl
        
        # Mock server
        server = Mock()
        server.enhanced_search = None
        server.search_client = None
        server.ensure_async_components_started = AsyncMock()
        
        # Test with empty query
        result = await search_code_impl(
            server=server,
            query="",
            intent=None,
            language=None,
            repository=None,
            max_results=10,
            include_dependencies=False,
            skip=0,
            orderby=None,
            highlight_code=False,
            bm25_only=False,
            exact_terms=None,
            disable_cache=False,
            include_timings=False,
            dependency_mode="auto",
            detail_level="full",
            snippet_lines=0
        )
        
        assert not result["ok"]
        assert "empty" in result["error"].lower()
    
    @pytest.mark.asyncio
    async def test_parameter_clamping(self):
        """Test that invalid parameters are clamped to valid ranges."""
        from mcprag.mcp.tools._helpers.search_impl import search_code_impl
        
        # Mock server with mock search
        server = Mock()
        server.ensure_async_components_started = AsyncMock()
        
        # Mock enhanced search
        mock_search = AsyncMock()
        mock_search.search = AsyncMock(return_value={
            "results": [
                {"file": f"file{i}.py", "relevance": 0.5}
                for i in range(50)  # More than requested
            ],
            "total": 100
        })
        server.enhanced_search = mock_search
        server.search_client = None
        
        # Test with over-limit max_results
        result = await search_code_impl(
            server=server,
            query="valid query",
            intent=None,
            language=None,
            repository=None,
            max_results=100,  # Over limit
            include_dependencies=False,
            skip=0,
            orderby=None,
            highlight_code=False,
            bm25_only=False,
            exact_terms=None,
            disable_cache=False,
            include_timings=False,
            dependency_mode="auto",
            detail_level="full",
            snippet_lines=0
        )
        
        # Should succeed with clamped value
        assert result["ok"]
        assert result["data"]["count"] <= MAX_RESULTS_LIMIT
    
    @pytest.mark.asyncio
    async def test_data_consistency_enforcement(self):
        """Test that data consistency is enforced on results."""
        from mcprag.mcp.tools._helpers.search_impl import search_code_impl
        
        # Mock server
        server = Mock()
        server.ensure_async_components_started = AsyncMock()
        
        # Mock enhanced search with inconsistent data
        mock_search = AsyncMock()
        mock_search.search = AsyncMock(return_value={
            "results": [
                {
                    "file": "test.py",
                    "language": "",  # Empty language
                    "repository": None,  # None repository
                    "relevance": None,  # None relevance
                    "start_line": -5,  # Invalid line
                },
                {
                    "file": None,  # None file
                    "language": "python",
                    "highlights": None,  # None highlights
                }
            ],
            "total": 2
        })
        server.enhanced_search = mock_search
        server.search_client = None
        
        result = await search_code_impl(
            server=server,
            query="test query",
            intent=None,
            language=None,
            repository=None,
            max_results=10,
            include_dependencies=False,
            skip=0,
            orderby=None,
            highlight_code=False,
            bm25_only=False,
            exact_terms=None,
            disable_cache=False,
            include_timings=False,
            dependency_mode="auto",
            detail_level="full",
            snippet_lines=0
        )
        
        assert result["ok"]
        items = result["data"]["items"]
        
        # Check that fields were fixed
        for item in items:
            assert item["file"] != "" and item["file"] is not None
            assert item["relevance"] >= 0
            assert isinstance(item["highlights"], dict)
            if item["start_line"] is not None:
                assert item["start_line"] >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])