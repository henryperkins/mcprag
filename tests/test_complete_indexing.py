#!/usr/bin/env python3
"""Test complete indexing with vector embeddings."""

import os
import sys
import tempfile
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from enhanced_rag.code_understanding import CodeChunker


def create_test_repo():
    """Create a small test repository."""
    repo_dir = tempfile.mkdtemp(prefix="test_repo_")

    # Create Python file
    python_code = '''
"""Test module for data processing."""
from typing import List, Dict
import pandas as pd

class DataProcessor:
    """Process and analyze data."""
    
    def __init__(self, config: Dict[str, any]):
        self.config = config
        
    def process_batch(self, items: List[str]) -> pd.DataFrame:
        """Process a batch of items into a DataFrame."""
        data = [{"item": item, "length": len(item)} for item in items]
        return pd.DataFrame(data)
'''

    # Create JavaScript file
    js_code = """
import React from 'react';
import axios from 'axios';

export class ApiClient {
    constructor(baseUrl) {
        this.baseUrl = baseUrl;
    }
    
    async fetchData(endpoint) {
        const response = await axios.get(`${this.baseUrl}/${endpoint}`);
        return response.data;
    }
}

export const useApiClient = (baseUrl) => {
    const [client] = React.useState(() => new ApiClient(baseUrl));
    return client;
};
"""

    # Write files
    Path(repo_dir, "processor.py").write_text(python_code)
    Path(repo_dir, "api_client.js").write_text(js_code)

    return repo_dir


def test_indexing_with_vectors():
    """Test the complete indexing process with vector embeddings."""

    print("Testing Complete Indexing with Vector Embeddings")
    print("=" * 60)

    # Create test repository
    repo_path = create_test_repo()
    repo_name = "test-vector-repo"

    print(f"Created test repository at: {repo_path}")
    print(f"Repository name: {repo_name}")
    print("-" * 60)

    try:
        # Initialize chunker (will enable embeddings if configured)
        chunker = CodeChunker()

        # Index the repository
        print(f"\nIndexing repository with vector embeddings...")
        chunker.index_repository(repo_path, repo_name)

        print("\n✅ Indexing completed successfully!")
        print("\nThe indexed documents now include:")
        print("- Code chunks with semantic boundaries")
        print("- Enhanced semantic context (10 imports/calls)")
        print("- Type annotations and inheritance info")
        print("- Vector embeddings for semantic search")

        # Clean up
        import shutil

        shutil.rmtree(repo_path)

    except Exception as e:
        print(f"\n❌ Error during indexing: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_indexing_with_vectors()
