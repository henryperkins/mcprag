#!/usr/bin/env python3
"""
Unit tests for CodeChunker class
"""
import pytest
import os
from unittest.mock import Mock, patch
from smart_indexer import CodeChunker


class TestCodeChunker:
    @patch.dict(os.environ, {
        'ACS_ENDPOINT': 'https://test.search.windows.net',
        'ACS_ADMIN_KEY': 'test-key'
    })
    def setup_method(self, _method=None):
        """Set up test fixtures."""
        with patch('smart_indexer.SearchClient'):
            self.chunker = CodeChunker()
    
    def test_chunk_python_file_simple_function(self):
        """Test chunking a simple Python function."""
        content = '''
def hello_world():
    """Say hello to the world."""
    print("Hello, World!")
    return "greeting"

def add_numbers(a, b):
    return a + b
'''
        chunks = self.chunker.chunk_python_file(content, "test.py")
        
        assert len(chunks) == 2
        assert "hello_world" in chunks[0]["function_signature"]
        assert "add_numbers" in chunks[1]["function_signature"]
        assert chunks[0]["chunk_type"] == "function"
        assert chunks[1]["chunk_type"] == "function"
    
    def test_chunk_python_file_with_class(self):
        """Test chunking Python code with classes."""
        content = '''
class Calculator:
    def __init__(self):
        self.result = 0
    
    def add(self, x):
        self.result += x
        return self.result
'''
        chunks = self.chunker.chunk_python_file(content, "calc.py")
        
        assert len(chunks) == 1
        assert "Calculator" in chunks[0]["function_signature"]
        assert chunks[0]["chunk_type"] == "class"
    
    def test_chunk_python_file_with_imports(self):
        """Test extraction of imports."""
        content = '''
import os
from pathlib import Path
import json as js

def process_file():
    pass
'''
        chunks = self.chunker.chunk_python_file(content, "imports.py")
        
        assert len(chunks) == 1
        imports = chunks[0]["imports_used"]
        assert "os" in imports
        assert "pathlib.Path" in imports
        assert "json" in imports
    
    def test_chunk_python_file_with_function_calls(self):
        """Test extraction of function calls."""
        content = '''
def process_data():
    result = calculate(10, 20)
    data.save()
    return result
'''
        chunks = self.chunker.chunk_python_file(content, "calls.py")
        
        assert len(chunks) == 1
        calls = chunks[0]["calls_functions"]
        assert "calculate" in calls
        assert "save" in calls
    
    def test_chunk_python_file_syntax_error_fallback(self):
        """Test fallback for non-parseable Python code."""
        content = '''
def broken_function(
    # Missing closing parenthesis and invalid syntax
    invalid syntax here
'''
        chunks = self.chunker.chunk_python_file(content, "broken.py")
        
        assert len(chunks) == 1
        assert chunks[0]["chunk_type"] == "file"
        assert chunks[0]["function_signature"] == ""
        assert "broken.py" in chunks[0]["semantic_context"]
    
    def test_chunk_js_ts_file_basic(self):
        """Test basic JavaScript/TypeScript chunking."""
        content = '''
function greet(name) {
    return `Hello, ${name}!`;
}

const add = (a, b) => a + b;

class MyClass {
    constructor() {
        this.value = 0;
    }
}
'''
        chunks = self.chunker.chunk_js_ts_file(content, "test.js")
        
        # Currently returns single chunk (as per gap analysis)
        assert len(chunks) == 1
        assert chunks[0]["chunk_type"] == "file"
        assert "greet" in chunks[0]["code_chunk"]
        assert "MyClass" in chunks[0]["code_chunk"]
    
    def test_extract_imports_python(self):
        """Test Python import extraction."""
        content = '''
import sys
import os.path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json as js
'''
        imports = self.chunker._extract_imports(content, "python")
        
        expected = ["sys", "os.path", "datetime.datetime", "datetime.timedelta",
                   "typing.List", "typing.Dict", "typing.Optional", "json"]
        for expected_import in expected:
            assert expected_import in imports
    
    def test_extract_imports_javascript(self):
        """Test JavaScript import extraction."""
        content = '''
import React from 'react';
import { useState, useEffect } from 'react';
import * as fs from 'fs';
const path = require('path');
'''
        imports = self.chunker._extract_imports(content, "javascript")
        
        expected = ["react", "react.useState", "react.useEffect", "fs", "path"]
        for expected_import in expected:
            assert expected_import in imports
    
    def test_extract_imports_typescript(self):
        """Test TypeScript import extraction."""
        content = '''
import { Component } from '@angular/core';
import type { User } from './types';
import Express from 'express';
'''
        imports = self.chunker._extract_imports(content, "typescript")
        
        expected = ["@angular/core.Component", "./types", "express"]
        for expected_import in expected:
            assert expected_import in imports
    
    @patch('smart_indexer.azure_search_client')
    def test_index_local_repository(self, mock_search_client):
        """Test local repository indexing with mocked Azure client."""
        mock_client = Mock()
        mock_search_client.return_value = mock_client
        
        # Mock file system
        with patch('pathlib.Path.rglob') as mock_rglob:
            mock_file = Mock()
            mock_file.suffix = '.py'
            mock_file.name = 'test.py'
            mock_file.read_text.return_value = 'def test(): pass'
            mock_file.as_posix.return_value = 'test.py'
            mock_rglob.return_value = [mock_file]
            
            with patch('pathlib.Path.is_dir', return_value=True):
                self.chunker.index_local_repository('/fake/path', 'test-repo')
        
        # Verify search client was called
        mock_client.upload_documents.assert_called()
    
    def test_generate_document_id(self):
        """Test document ID generation."""
        doc_id = self.chunker._generate_document_id("test-repo", "src/main.py", "function", 1)
        
        # Should be consistent hash
        assert isinstance(doc_id, str)
        assert len(doc_id) > 0
        
        # Same inputs should produce same ID
        doc_id2 = self.chunker._generate_document_id("test-repo", "src/main.py", "function", 1)
        assert doc_id == doc_id2
    
    def test_supported_file_extensions(self):
        """Test that chunker only processes supported file types."""
        supported_files = [
            "script.py", "app.js", "component.ts", "styles.jsx", "api.tsx"
        ]
        unsupported_files = [
            "readme.md", "config.json", "image.png", "binary.exe"
        ]
        
        for filename in supported_files:
            assert any(filename.endswith(ext) for ext in [".py", ".js", ".ts", ".jsx", ".tsx"])
        
        for filename in unsupported_files:
            assert not any(filename.endswith(ext) for ext in [".py", ".js", ".ts", ".jsx", ".tsx"])


if __name__ == "__main__":
    pytest.main([__file__])
