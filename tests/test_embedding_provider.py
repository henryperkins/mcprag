#!/usr/bin/env python3
"""
Unit tests for embedding provider abstraction
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import os


class TestAzureOpenAIEmbeddingProvider:
    @patch.dict(
        os.environ,
        {
            "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
            "AZURE_OPENAI_API_KEY": "test-key",
            "AZURE_OPENAI_EMBEDDING_MODEL": "text-embedding-ada-002",
        },
    )
    def test_provider_initialization(self):
        """Test AzureOpenAIEmbeddingProvider initialization with Azure OpenAI."""
        from enhanced_rag.azure_integration import AzureOpenAIEmbeddingProvider

        provider = AzureOpenAIEmbeddingProvider()
        assert provider.endpoint == "https://test.openai.azure.com/"
        assert provider.api_key == "test-key"
        assert provider.model_name == "text-embedding-ada-002"
        assert provider.use_azure is True

    @patch.dict(
        os.environ,
        {
            "OPENAI_API_KEY": "sk-test-key",
            "AZURE_OPENAI_ENDPOINT": "",
            "AZURE_OPENAI_API_KEY": "",
        },
    )
    def test_provider_openai_fallback(self):
        """Test AzureOpenAIEmbeddingProvider falls back to OpenAI when Azure not configured."""
        from enhanced_rag.azure_integration import AzureOpenAIEmbeddingProvider

        provider = AzureOpenAIEmbeddingProvider()
        assert provider.use_azure is False
        assert provider.api_key == "sk-test-key"

    @patch.dict(os.environ, {}, clear=True)
    def test_provider_no_keys_raises_error(self):
        """Test AzureOpenAIEmbeddingProvider raises error when no API keys are provided."""
        from enhanced_rag.azure_integration import AzureOpenAIEmbeddingProvider

        with pytest.raises(ValueError, match="API key"):
            AzureOpenAIEmbeddingProvider()

    @patch.dict(
        os.environ,
        {
            "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
            "AZURE_OPENAI_API_KEY": "test-key",
        },
    )
    @patch("enhanced_rag.azure_integration.embedding_provider.AzureOpenAI")
    def test_generate_embedding(self, mock_azure_openai):
        """Test generate_embedding method."""
        from enhanced_rag.azure_integration import AzureOpenAIEmbeddingProvider

        # Mock the client and response
        mock_client = Mock()
        mock_azure_openai.return_value = mock_client
        
        # Create mock response
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1, 0.2, 0.3])]
        mock_client.embeddings.create.return_value = mock_response

        provider = AzureOpenAIEmbeddingProvider()
        result = provider.generate_embedding("test text")

        assert result == [0.1, 0.2, 0.3]
        mock_client.embeddings.create.assert_called_once()

    @patch.dict(
        os.environ,
        {
            "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
            "AZURE_OPENAI_API_KEY": "test-key",
        },
    )
    @patch("enhanced_rag.azure_integration.embedding_provider.AzureOpenAI")
    def test_generate_code_embedding(self, mock_azure_openai):
        """Test generate_code_embedding method."""
        from enhanced_rag.azure_integration import AzureOpenAIEmbeddingProvider

        # Mock the client and response
        mock_client = Mock()
        mock_azure_openai.return_value = mock_client
        
        # Create mock response
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.4, 0.5, 0.6])]
        mock_client.embeddings.create.return_value = mock_response

        provider = AzureOpenAIEmbeddingProvider()
        result = provider.generate_code_embedding("def foo():", "Function definition")

        assert result == [0.4, 0.5, 0.6]
        # Check that context and code were combined
        call_args = mock_client.embeddings.create.call_args[1]
        assert "Function definition" in call_args["input"]
        assert "def foo():" in call_args["input"]


class TestNullEmbeddingProvider:
    def test_null_provider_returns_none(self):
        """Test NullEmbeddingProvider always returns None."""
        from enhanced_rag.azure_integration.embedding_provider import NullEmbeddingProvider

        provider = NullEmbeddingProvider()
        assert provider.generate_embedding("test") is None
        assert provider.generate_code_embedding("code", "context") is None
        assert provider.generate_embeddings_batch(["a", "b", "c"]) == [None, None, None]