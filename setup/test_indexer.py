#!/usr/bin/env python3
"""Test script to verify the smart indexer functionality without Azure."""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock the Azure client for testing
class MockSearchClient:
    def merge_or_upload_documents(self, documents):
        print(f"Mock: Would upload {len(documents)} documents")
        for doc in documents[:2]:  # Show first 2 documents
            print(f"  - {doc['id']}: {doc['language']} file {doc['file_path']}")
        return {"status": "success"}

# Patch the CodeChunker to use mock client
from smart_indexer import CodeChunker

class TestCodeChunker(CodeChunker):
    def __init__(self):
        # Don't call super().__init__() to avoid Azure client creation
        self.client = MockSearchClient()

def test_javascript_parsing():
    """Test JavaScript file parsing."""
    print("Testing JavaScript parsing...")
    
    chunker = TestCodeChunker()
    
    # Test with the example JavaScript file
    js_file = Path("example-repo/api.js")
    if js_file.exists():
        content = js_file.read_text()
        chunks = chunker.chunk_js_ts_file(content, str(js_file))
        
        print(f"✅ Parsed {js_file}")
        print(f"   Generated {len(chunks)} chunks")
        if chunks:
            chunk = chunks[0]
            print(f"   Function signature: {chunk['function_signature']}")
            print(f"   Imports: {chunk['imports_used']}")
            print(f"   Calls: {chunk['calls_functions'][:5]}")  # First 5 calls
    else:
        print("❌ example-repo/api.js not found")

def test_python_parsing():
    """Test Python file parsing."""
    print("\nTesting Python parsing...")
    
    chunker = TestCodeChunker()
    
    # Test with a Python file
    py_file = Path("example-repo/auth.py")
    if py_file.exists():
        content = py_file.read_text()
        chunks = chunker.chunk_python_file(content, str(py_file))
        
        print(f"✅ Parsed {py_file}")
        print(f"   Generated {len(chunks)} chunks")
        if chunks:
            chunk = chunks[0]
            print(f"   Function signature: {chunk['function_signature']}")
            print(f"   Imports: {chunk['imports_used']}")
            print(f"   Calls: {chunk['calls_functions'][:5]}")  # First 5 calls
    else:
        print("❌ example-repo/auth.py not found")

def test_repository_indexing():
    """Test full repository indexing."""
    print("\nTesting repository indexing...")
    
    chunker = TestCodeChunker()
    chunker.index_repository("./example-repo", "test-repo")

if __name__ == "__main__":
    print("🧪 Testing Smart Indexer with Babel AST Support")
    print("=" * 50)
    
    test_javascript_parsing()
    test_python_parsing()
    test_repository_indexing()
    
    print("\n✅ All tests completed!")
