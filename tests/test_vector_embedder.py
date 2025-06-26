#!/usr/bin/env python3
"""
Unit tests for VectorEmbedder class
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import os


class TestVectorEmbedder:
    @patch.dict(os.environ, {
        'AZURE_OPENAI_ENDPOINT': 'https://test.openai.azure.com/',
        'AZURE_OPENAI_API_KEY': 'test-key',
        'AZURE_OPENAI_EMBEDDING_MODEL': 'text-embedding-ada-002'
    })
    def test_vector_embedder_initialization(self):
        """Test VectorEmbedder initialization with Azure OpenAI."""
        from vector_embeddings import VectorEmbedder
        
        embedder = VectorEmbedder()
        assert embedder.endpoint == "https://test.openai.azure.com/"
        assert embedder.api_key == "test-key"
        assert embedder.model_name == "text-embedding-ada-002"
    
    @patch.dict(os.environ, {
        'OPENAI_API_KEY': 'sk-test-key',
        'AZURE_OPENAI_ENDPOINT': '',
        'AZURE_OPENAI_API_KEY': ''
    })
    def test_vector_embedder_openai_fallback(self):
        """Test VectorEmbedder falls back to OpenAI when Azure not configured."""
        from vector_embeddings import VectorEmbedder
        
        embedder = VectorEmbedder()
        assert embedder.use_azure is False
        assert embedder.api_key == "sk-test-key"
    
    @patch.dict(os.environ, {}, clear=True)
    def test_vector_embedder_no_keys_raises_error(self):
        """Test VectorEmbedder raises error when no API keys are provided."""
        from vector_embeddings import VectorEmbedder
        
        with pytest.raises(ValueError, match="API key"):
            VectorEmbedder()
    
    @patch('vector_embeddings.OpenAI')
    @patch.dict(os.environ, {
        'AZURE_OPENAI_ENDPOINT': 'https://test.openai.azure.com/',
        'AZURE_OPENAI_API_KEY': 'test-key',
        'AZURE_OPENAI_EMBEDDING_MODEL': 'text-embedding-ada-002'
    })
    def test_generate_embedding_success(self, mock_openai):
        """Test successful embedding generation."""
        from vector_embeddings import VectorEmbedder
        
        # Mock OpenAI client response
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1, 0.2, 0.3, 0.4])]
        mock_client.embeddings.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        embedder = VectorEmbedder()
        result = embedder.generate_embedding("test code snippet")
        
        assert result == [0.1, 0.2, 0.3, 0.4]
        mock_client.embeddings.create.assert_called_once_with(
            input="test code snippet",
            model="text-embedding-ada-002"
        )
    
    @patch('vector_embeddings.OpenAI')
    @patch.dict(os.environ, {
        'AZURE_OPENAI_ENDPOINT': 'https://test.openai.azure.com/',
        'AZURE_OPENAI_API_KEY': 'test-key'
    })
    def test_generate_embedding_api_error(self, mock_openai):
        """Test embedding generation with API error."""
        from vector_embeddings import VectorEmbedder
        
        # Mock OpenAI client to raise exception
        mock_client = Mock()
        mock_client.embeddings.create.side_effect = Exception("API Error")
        mock_openai.return_value = mock_client
        
        embedder = VectorEmbedder()
        result = embedder.generate_embedding("test code")
        
        # Should return None on error
        assert result is None
    
    @patch('vector_embeddings.OpenAI')
    @patch.dict(os.environ, {
        'AZURE_OPENAI_ENDPOINT': 'https://test.openai.azure.com/',
        'AZURE_OPENAI_API_KEY': 'test-key'
    })
    def test_generate_embeddings_batch(self, mock_openai):
        """Test batch embedding generation."""
        from vector_embeddings import VectorEmbedder
        
        # Mock OpenAI client response for batch
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = [
            Mock(embedding=[0.1, 0.2]),
            Mock(embedding=[0.3, 0.4]),
            Mock(embedding=[0.5, 0.6])
        ]
        mock_client.embeddings.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        embedder = VectorEmbedder()
        texts = ["code1", "code2", "code3"]
        results = embedder.generate_embeddings_batch(texts)
        
        assert len(results) == 3
        assert results[0] == [0.1, 0.2]
        assert results[1] == [0.3, 0.4]
        assert results[2] == [0.5, 0.6]
    
    @patch('vector_embeddings.OpenAI')
    @patch.dict(os.environ, {
        'AZURE_OPENAI_ENDPOINT': 'https://test.openai.azure.com/',
        'AZURE_OPENAI_API_KEY': 'test-key'
    })
    def test_generate_embeddings_batch_partial_failure(self, mock_openai):
        """Test batch embedding with partial failures."""
        from vector_embeddings import VectorEmbedder
        
        # Mock OpenAI client to fail on second call
        mock_client = Mock()
        responses = [
            Mock(data=[Mock(embedding=[0.1, 0.2])]),
            Exception("API Error"),
            Mock(data=[Mock(embedding=[0.5, 0.6])])
        ]
        mock_client.embeddings.create.side_effect = responses
        mock_openai.return_value = mock_client
        
        embedder = VectorEmbedder()
        texts = ["code1", "code2", "code3"]
        results = embedder.generate_embeddings_batch(texts)
        
        # Should return results for successful embeddings, None for failures
        assert len(results) == 3
        assert results[0] == [0.1, 0.2]
        assert results[1] is None
        assert results[2] == [0.5, 0.6]
    
    @patch('vector_embeddings.OpenAI')
    @patch.dict(os.environ, {
        'OPENAI_API_KEY': 'sk-test-key'
    })
    def test_openai_client_configuration(self, mock_openai):
        """Test OpenAI client configuration for non-Azure usage."""
        from vector_embeddings import VectorEmbedder
        
        embedder = VectorEmbedder()
        
        # Verify OpenAI client was configured correctly
        mock_openai.assert_called_once_with(api_key='sk-test-key')
        assert embedder.use_azure is False
    
    @patch('vector_embeddings.OpenAI')
    @patch.dict(os.environ, {
        'AZURE_OPENAI_ENDPOINT': 'https://test.openai.azure.com/',
        'AZURE_OPENAI_API_KEY': 'test-key'
    })
    def test_azure_openai_client_configuration(self, mock_openai):
        """Test Azure OpenAI client configuration."""
        from vector_embeddings import VectorEmbedder
        
        embedder = VectorEmbedder()
        
        # Verify Azure OpenAI client was configured correctly
        mock_openai.assert_called_once_with(
            api_key='test-key',
            azure_endpoint='https://test.openai.azure.com/',
            api_version='2024-02-01'
        )
        assert embedder.use_azure is True
    
    @patch('vector_embeddings.OpenAI')
    @patch.dict(os.environ, {
        'AZURE_OPENAI_ENDPOINT': 'https://test.openai.azure.com/',
        'AZURE_OPENAI_API_KEY': 'test-key'
    })
    def test_embedding_dimension_consistency(self, mock_openai):
        """Test that embeddings have consistent dimensions."""
        from vector_embeddings import VectorEmbedder
        
        # Mock consistent embedding dimensions
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1] * 1536)]  # Standard Ada-002 dimensions
        mock_client.embeddings.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        embedder = VectorEmbedder()
        
        # Test multiple embeddings have same dimension
        embedding1 = embedder.generate_embedding("code snippet 1")
        embedding2 = embedder.generate_embedding("code snippet 2")
        
        assert len(embedding1) == len(embedding2) == 1536
    
    @patch('vector_embeddings.OpenAI')
    @patch.dict(os.environ, {
        'AZURE_OPENAI_ENDPOINT': 'https://test.openai.azure.com/',
        'AZURE_OPENAI_API_KEY': 'test-key'
    })
    def test_text_preprocessing(self, mock_openai):
        """Test text preprocessing before embedding."""
        from vector_embeddings import VectorEmbedder
        
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1, 0.2, 0.3])]
        mock_client.embeddings.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        embedder = VectorEmbedder()
        
        # Test with code that might need preprocessing
        code_with_newlines = """
        def function():
            print("hello")
            return True
        """
        
        result = embedder.generate_embedding(code_with_newlines)
        
        # Verify the text was passed to the API (preprocessing handled internally)
        assert result == [0.1, 0.2, 0.3]
        mock_client.embeddings.create.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])
