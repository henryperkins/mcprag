#!/usr/bin/env python3
"""Test script to verify improved chunking functionality."""

import sys
import tempfile
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from enhanced_rag.code_understanding import CodeChunker


def test_python_chunking():
    """Test enhanced Python chunking with type annotations."""
    test_code = '''
from typing import List, Dict, Optional
import asyncio
import json

class BaseProcessor(object):
    """Base class for processors."""
    pass

class DataProcessor(BaseProcessor):
    """Process data with type annotations."""
    
    def __init__(self, config: Dict[str, any]) -> None:
        self.config = config
    
    async def process_items(self, items: List[str]) -> Dict[str, int]:
        """Process a list of items asynchronously.
        
        Args:
            items: List of items to process
            
        Returns:
            Dictionary with processing results
        """
        results = {}
        for item in items:
            results[item] = len(item)
        return results
    
    def validate_input(self, data: Optional[str] = None) -> bool:
        """Validate input data."""
        if data is None:
            return False
        return len(data) > 0
'''

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(test_code)
        temp_file = f.name

    try:
        chunker = CodeChunker()
        chunks = chunker.chunk_python_file(test_code, temp_file)

        print("=== Python Chunking Results ===")
        for i, chunk in enumerate(chunks):
            print(f"\nChunk {i+1}:")
            print(f"Type: {chunk['chunk_type']}")
            print(f"Signature: {chunk['signature']}")
            print(f"Line Range: {chunk['start_line']}-{chunk['end_line']}")
            print(f"Semantic Context:\n{chunk['semantic_context']}")
            print("-" * 50)

    finally:
        os.unlink(temp_file)


def test_js_chunking():
    """Test enhanced JavaScript/TypeScript chunking."""
    test_code = """
import React from 'react';
import { useState, useEffect } from 'react';
import axios from 'axios';

class UserManager extends React.Component {
    constructor(props) {
        super(props);
        this.state = { users: [] };
    }
    
    async fetchUsers() {
        const response = await axios.get('/api/users');
        return response.data;
    }
}

const useUserData = (userId) => {
    const [user, setUser] = useState(null);
    
    useEffect(() => {
        fetchUserById(userId).then(setUser);
    }, [userId]);
    
    return user;
};

async function fetchUserById(id) {
    const response = await fetch(`/api/users/${id}`);
    return response.json();
}

export default UserManager;
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
        f.write(test_code)
        temp_file = f.name

    try:
        chunker = CodeChunker()
        chunks = chunker.chunk_js_ts_file(test_code, temp_file)

        print("\n=== JavaScript Chunking Results ===")
        for i, chunk in enumerate(chunks):
            print(f"\nChunk {i+1}:")
            print(f"Type: {chunk['chunk_type']}")
            print(f"Signature: {chunk['signature']}")
            print(f"Line Range: {chunk['start_line']}-{chunk['end_line']}")
            print(f"Semantic Context:\n{chunk['semantic_context']}")
            print("-" * 50)

    finally:
        os.unlink(temp_file)


if __name__ == "__main__":
    print("Testing improved chunking functionality...\n")

    # Test Python chunking
    test_python_chunking()

    # Test JS chunking
    test_js_chunking()

    print("\n✅ Tests completed!")
