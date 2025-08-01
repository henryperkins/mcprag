#!/usr/bin/env python3
"""
Unit tests for LocalRepositoryIndexer
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import os
from pathlib import Path
import tempfile
import shutil


class TestLocalRepositoryIndexer:
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        mock_cfg = Mock()
        mock_cfg.azure.endpoint = "https://test.search.windows.net"
        mock_cfg.azure.admin_key = "test-key"
        mock_cfg.azure.index_name = "test-index"
        mock_cfg.embedding.provider = "none"
        return mock_cfg

    @pytest.fixture
    def temp_repo(self):
        """Create a temporary repository with test files."""
        temp_dir = tempfile.mkdtemp()
        
        # Create Python file
        py_file = Path(temp_dir) / "test.py"
        py_file.write_text("""
def hello_world():
    '''Say hello'''
    print("Hello, World!")

class TestClass:
    def method(self):
        pass
""")
        
        # Create JavaScript file
        js_file = Path(temp_dir) / "test.js"
        js_file.write_text("""
function helloJs() {
    console.log("Hello from JS");
}

const arrowFunc = () => {
    return 42;
};
""")
        
        yield temp_dir
        
        # Cleanup
        shutil.rmtree(temp_dir)

    @patch("enhanced_rag.azure_integration.indexer_integration.get_config")
    @patch("enhanced_rag.azure_integration.indexer_integration.SearchClient")
    @patch("enhanced_rag.azure_integration.indexer_integration.AzureKeyCredential")
    def test_indexer_initialization(self, mock_credential, mock_client, mock_get_config, mock_config):
        """Test LocalRepositoryIndexer initialization."""
        from enhanced_rag.azure_integration import LocalRepositoryIndexer
        
        mock_get_config.return_value = mock_config
        
        indexer = LocalRepositoryIndexer()
        
        assert indexer.endpoint == "https://test.search.windows.net"
        assert indexer.admin_key == "test-key"
        assert indexer.index_name == "test-index"
        assert indexer.provider is None  # No embedding provider for "none"
        
        mock_client.assert_called_once()
        mock_credential.assert_called_once_with("test-key")

    @patch("enhanced_rag.azure_integration.indexer_integration.get_config")
    @patch("enhanced_rag.azure_integration.indexer_integration.SearchClient")
    @patch("enhanced_rag.azure_integration.indexer_integration.AzureKeyCredential")
    def test_chunk_python_file(self, mock_credential, mock_client, mock_get_config, mock_config):
        """Test Python file chunking."""
        from enhanced_rag.azure_integration import LocalRepositoryIndexer
        
        mock_get_config.return_value = mock_config
        indexer = LocalRepositoryIndexer()
        
        python_code = """
def add(a, b):
    '''Add two numbers'''
    return a + b

class Calculator:
    '''Calculator class'''
    def multiply(self, x, y):
        return x * y
"""
        
        chunks = indexer.chunk_python_file(python_code, "test.py")
        
        assert len(chunks) == 2  # One function, one class
        
        # Check function chunk
        func_chunk = next(c for c in chunks if c["chunk_type"] == "function")
        assert func_chunk["function_name"] == "add"
        assert "def add(a, b):" in func_chunk["content"]
        assert func_chunk["docstring"] == "Add two numbers"
        
        # Check class chunk
        class_chunk = next(c for c in chunks if c["chunk_type"] == "class")
        assert class_chunk["class_name"] == "Calculator"
        assert "class Calculator:" in class_chunk["content"]

    @patch("enhanced_rag.azure_integration.indexer_integration.get_config")
    @patch("enhanced_rag.azure_integration.indexer_integration.SearchClient")
    @patch("enhanced_rag.azure_integration.indexer_integration.AzureKeyCredential")
    def test_index_repository(self, mock_credential, mock_client_class, mock_get_config, mock_config, temp_repo):
        """Test repository indexing."""
        from enhanced_rag.azure_integration import LocalRepositoryIndexer
        
        mock_get_config.return_value = mock_config
        
        # Mock search client
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.merge_or_upload_documents.return_value = None
        
        indexer = LocalRepositoryIndexer()
        indexer.index_repository(temp_repo, "test-repo")
        
        # Verify documents were uploaded
        assert mock_client.merge_or_upload_documents.called
        
        # Get the uploaded documents
        call_args = mock_client.merge_or_upload_documents.call_args_list
        all_docs = []
        for call in call_args:
            all_docs.extend(call[0][0])
        
        # Should have chunks for both files
        assert len(all_docs) > 0
        
        # Check document structure
        for doc in all_docs:
            assert "id" in doc
            assert doc["repository"] == "test-repo"
            assert "file_path" in doc
            assert "content" in doc
            assert "semantic_context" in doc

    @patch("enhanced_rag.azure_integration.indexer_integration.get_config")
    @patch("enhanced_rag.azure_integration.indexer_integration.SearchClient")
    @patch("enhanced_rag.azure_integration.indexer_integration.AzureKeyCredential")
    @patch("enhanced_rag.azure_integration.indexer_integration.AzureOpenAIEmbeddingProvider")
    def test_index_with_embeddings(self, mock_provider_class, mock_credential, mock_client_class, mock_get_config):
        """Test indexing with embeddings enabled."""
        from enhanced_rag.azure_integration import LocalRepositoryIndexer
        
        # Configure for client embeddings
        mock_config = Mock()
        mock_config.azure.endpoint = "https://test.search.windows.net"
        mock_config.azure.admin_key = "test-key"
        mock_config.azure.index_name = "test-index"
        mock_config.embedding.provider = "client"
        mock_get_config.return_value = mock_config
        
        # Mock embedding provider
        mock_provider = Mock()
        mock_provider.generate_code_embedding.return_value = [0.1, 0.2, 0.3]
        mock_provider_class.return_value = mock_provider
        
        # Mock search client
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        indexer = LocalRepositoryIndexer()
        assert indexer.provider is not None
        
        # Create a simple test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("def test(): pass")
            temp_file = f.name
        
        try:
            indexer.index_changed_files([temp_file], "test-repo")
            
            # Verify embedding was generated
            mock_provider.generate_code_embedding.assert_called()
            
            # Check uploaded documents have embeddings
            call_args = mock_client.merge_or_upload_documents.call_args
            docs = call_args[0][0]
            assert len(docs) > 0
            assert "content_vector" in docs[0]
            assert docs[0]["content_vector"] == [0.1, 0.2, 0.3]
            
        finally:
            os.unlink(temp_file)

    def test_document_id_generation(self):
        """Test document ID generation is deterministic."""
        from enhanced_rag.azure_integration.indexer_integration import LocalRepositoryIndexer
        
        id1 = LocalRepositoryIndexer.DocumentIdHelper.generate_id(
            "repo1", "file.py", "function", 0
        )
        id2 = LocalRepositoryIndexer.DocumentIdHelper.generate_id(
            "repo1", "file.py", "function", 0
        )
        id3 = LocalRepositoryIndexer.DocumentIdHelper.generate_id(
            "repo2", "file.py", "function", 0
        )
        
        assert id1 == id2  # Same inputs produce same ID
        assert id1 != id3  # Different repo produces different ID