#!/usr/bin/env python3
"""
Core tests for enhanced MCP server modifications.
Tests the core functionality without the full MCP framework.
"""

import os
import sys
import pytest
from unittest.mock import Mock, patch

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock the environment before importing
os.environ["ACS_ENDPOINT"] = "https://test.search.windows.net"
os.environ["ACS_ADMIN_KEY"] = "test-key"
os.environ["ACS_INDEX_NAME"] = "test-index"

# Import after setting environment
from mcp_server_sota import (
    SearchCodeParams, SearchResult, SearchIntent, FieldMapper,
    _ok, _err, _Timer
)


class TestCoreHelpers:
    """Test core helper functions."""
    
    def test_ok_function(self):
        """Test _ok helper returns correct structure."""
        result = _ok({"key": "value", "count": 42})
        
        assert result["ok"] == True
        assert result["data"]["key"] == "value"
        assert result["data"]["count"] == 42
    
    def test_err_function(self):
        """Test _err helper returns correct structure."""
        result = _err("Something went wrong", code="test_error")
        
        assert result["ok"] == False
        assert result["error"] == "Something went wrong"
        assert result["code"] == "test_error"
    
    def test_err_function_without_code(self):
        """Test _err helper without code."""
        result = _err("Another error")
        
        assert result["ok"] == False
        assert result["error"] == "Another error"
        assert result["code"] == "error"  # Default code


class TestTimerClass:
    """Test the _Timer utility class."""
    
    def test_timer_initialization(self):
        """Test timer starts with start mark."""
        timer = _Timer()
        assert "start" in timer._marks
    
    def test_timer_marks(self):
        """Test adding marks to timer."""
        timer = _Timer()
        
        # Add marks
        timer.mark("step1")
        assert "step1" in timer._marks
        
        timer.mark("step2")
        assert "step2" in timer._marks
    
    def test_timer_durations(self):
        """Test duration calculation."""
        timer = _Timer()
        
        # Add some marks with small delays
        timer.mark("step1")
        timer.mark("step2")
        timer.mark("done")
        
        durations = timer.durations()
        
        # Check expected duration keys
        assert "start→step1" in durations
        assert "step1→step2" in durations
        assert "step2→done" in durations
        assert "total" in durations
        
        # All durations should be non-negative
        for key, duration in durations.items():
            assert duration >= 0, f"Duration {key} is negative: {duration}"
            assert isinstance(duration, float), f"Duration {key} is not a float"


class TestFieldMapper:
    """Test FieldMapper functionality."""
    
    def test_field_mapper_initialization(self):
        """Test FieldMapper initializes correctly."""
        available_fields = ["content", "function_name", "repository", "file_path"]
        mapper = FieldMapper(available_fields)
        
        assert mapper.available == set(available_fields)
        assert len(mapper.reverse_map) > 0
    
    def test_field_mapper_canonical_mapping(self):
        """Test canonical field mapping."""
        available_fields = ["content", "function_name", "repository", "path"]  # Note: 'path' not 'file_path'
        mapper = FieldMapper(available_fields)
        
        # Should map file_path to path
        assert mapper.reverse_map.get("file_path") == "path"
        assert mapper.reverse_map.get("content") == "content"
        assert mapper.reverse_map.get("repository") == "repository"
    
    def test_field_mapper_select_list(self):
        """Test select list generation."""
        available_fields = ["content", "repository", "file_path", "language"]
        mapper = FieldMapper(available_fields)
        
        select_list = mapper.select_list()
        
        # Should include available fields
        assert "content" in select_list
        assert "repository" in select_list
        assert "file_path" in select_list
        assert "language" in select_list
    
    def test_field_mapper_get_field(self):
        """Test field access with get method."""
        available_fields = ["content", "path", "repository"]
        mapper = FieldMapper(available_fields)
        
        doc = {
            "content": "test content",
            "path": "/test/file.py",
            "repository": "test-repo"
        }
        
        # Direct access
        assert mapper.get(doc, "content") == "test content"
        assert mapper.get(doc, "repository") == "test-repo"
        
        # Mapped access (file_path -> path)
        assert mapper.get(doc, "file_path") == "/test/file.py"
        
        # Missing field with default
        assert mapper.get(doc, "missing_field", "default") == "default"
    
    def test_field_mapper_validate_required(self):
        """Test required field validation."""
        # Missing content field
        available_fields = ["repository", "file_path", "language"]
        mapper = FieldMapper(available_fields)
        
        validation = mapper.validate_required()
        assert not validation["valid"]
        assert "content" in validation["missing"]
        
        # All required fields present
        available_fields = ["repository", "file_path", "language", "content"]
        mapper = FieldMapper(available_fields)
        
        validation = mapper.validate_required()
        assert validation["valid"]
        assert len(validation["missing"]) == 0


class TestSearchCodeParams:
    """Test SearchCodeParams model."""
    
    def test_search_code_params_basic(self):
        """Test basic SearchCodeParams creation."""
        params = SearchCodeParams(
            query="test query",
            max_results=20
        )
        
        assert params.query == "test query"
        assert params.max_results == 20
        assert params.include_dependencies == False  # Default
        assert params.bm25_only == False  # Default
    
    def test_search_code_params_with_intent(self):
        """Test SearchCodeParams with intent."""
        params = SearchCodeParams(
            query="implement auth",
            intent=SearchIntent.IMPLEMENT,
            language="python"
        )
        
        assert params.query == "implement auth"
        assert params.intent == SearchIntent.IMPLEMENT
        assert params.language == "python"
    
    def test_search_code_params_with_exact_terms(self):
        """Test SearchCodeParams with exact terms."""
        params = SearchCodeParams(
            query="search query",
            exact_terms=["HTTP/1.1", "404"]
        )
        
        assert params.exact_terms == ["HTTP/1.1", "404"]
    
    def test_search_code_params_validation(self):
        """Test SearchCodeParams validation."""
        # Test max_results bounds
        with pytest.raises(ValueError):
            SearchCodeParams(query="test", max_results=0)  # Too small
        
        with pytest.raises(ValueError):
            SearchCodeParams(query="test", max_results=100)  # Too large


class TestSearchResult:
    """Test SearchResult model."""
    
    def test_search_result_creation(self):
        """Test SearchResult creation."""
        result = SearchResult(
            file_path="/path/to/file.py",
            repository="test-repo",
            language="python",
            score=0.95,
            content="def test_function():\n    pass"
        )
        
        assert result.file_path == "/path/to/file.py"
        assert result.repository == "test-repo"
        assert result.language == "python"
        assert result.score == 0.95
        assert result.content == "def test_function():\n    pass"
    
    def test_search_result_optional_fields(self):
        """Test SearchResult optional fields."""
        result = SearchResult(
            file_path="/test.py",
            repository="repo",
            language="python",
            score=1.0,
            content="code",
            function_name="my_func",
            signature="def my_func(x):",
            line_range="10-20",
            imports=["os", "sys"],
            dependencies=["helper", "utils"]
        )
        
        assert result.function_name == "my_func"
        assert result.signature == "def my_func(x):"
        assert result.line_range == "10-20"
        assert result.imports == ["os", "sys"]
        assert result.dependencies == ["helper", "utils"]
    
    def test_search_result_model_dump(self):
        """Test SearchResult serialization."""
        result = SearchResult(
            file_path="/test.py",
            repository="repo",
            language="python",
            score=1.0,
            content="code"
        )
        
        dumped = result.model_dump()
        
        assert isinstance(dumped, dict)
        assert dumped["file_path"] == "/test.py"
        assert dumped["repository"] == "repo"
        assert dumped["score"] == 1.0


class TestSearchIntent:
    """Test SearchIntent enum."""
    
    def test_search_intent_values(self):
        """Test SearchIntent enum values."""
        assert SearchIntent.IMPLEMENT.value == "implement"
        assert SearchIntent.DEBUG.value == "debug"
        assert SearchIntent.UNDERSTAND.value == "understand"
        assert SearchIntent.REFACTOR.value == "refactor"
    
    def test_search_intent_from_string(self):
        """Test creating SearchIntent from string."""
        intent = SearchIntent("implement")
        assert intent == SearchIntent.IMPLEMENT
        
        intent = SearchIntent("debug")
        assert intent == SearchIntent.DEBUG


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])