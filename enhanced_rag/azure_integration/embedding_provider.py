"""Embedding provider abstraction for Azure Integration.

This module provides a unified interface for generating embeddings across different
providers, migrating functionality from vector_embeddings.py.
"""

import os
import logging
from abc import ABC, abstractmethod
from typing import List, Sequence, Optional
from dotenv import load_dotenv

load_dotenv()

# Optional dependency: openai
from types import SimpleNamespace


def _build_openai_stub():
    """Build a stub module for when OpenAI SDK is not installed."""
    class _DummyEmbeddingResponse:
        """Mimic the object returned by openai.Embedding.create"""
        def __init__(self, emb):
            self.data = [SimpleNamespace(embedding=emb)]

        def __getitem__(self, key):
            if key == "data":
                return self.data
            raise KeyError(key)

    def _fake_create(*_, **__):
        return _DummyEmbeddingResponse([0.0, 0.0, 0.0, 0.0])

    embeddings_ns = SimpleNamespace(create=_fake_create)

    class FakeClient:
        def __init__(self, **kwargs):
            self.embeddings = embeddings_ns

    return FakeClient


try:
    from openai import OpenAI, AzureOpenAI  # type: ignore
except ModuleNotFoundError:
    OpenAI = _build_openai_stub()  # type: ignore
    AzureOpenAI = _build_openai_stub()  # type: ignore


def _get_env(name: str) -> Optional[str]:
    """Helper to normalise environment variables."""
    value = os.getenv(name)
    return value.strip() if value else None


class IEmbeddingProvider(ABC):
    """Interface for embedding providers."""

    @abstractmethod
    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate a single embedding vector for text.
        
        Args:
            text: The text to embed
            
        Returns:
            Embedding vector or None on error
        """
        pass

    @abstractmethod
    def generate_embeddings_batch(self, texts: Sequence[str]) -> List[Optional[List[float]]]:
        """Generate embeddings for multiple texts in a batch.
        
        Args:
            texts: Sequence of texts to embed
            
        Returns:
            List of embedding vectors (or None for failures) matching input order
        """
        pass

    @abstractmethod
    def generate_code_embedding(self, code: str, context: str) -> Optional[List[float]]:
        """Generate embedding for code with additional context.
        
        Args:
            code: The code snippet to embed
            context: Additional context (e.g., function signatures, imports)
            
        Returns:
            Embedding vector or None on error
        """
        pass


class AzureOpenAIEmbeddingProvider(IEmbeddingProvider):
    """Embedding provider using Azure OpenAI or OpenAI API.
    
    Supports both Azure-hosted and public OpenAI endpoints based on
    environment configuration.
    """

    def __init__(self):
        # Resolve credentials / endpoints
        self.endpoint: str = _get_env("AZURE_OPENAI_ENDPOINT") or ""
        # Accept both legacy and new env-var names for the API key
        self.api_key: str = (
            _get_env("AZURE_OPENAI_API_KEY")
            or _get_env("AZURE_OPENAI_KEY")
            or _get_env("OPENAI_API_KEY")
            or ""
        )

        if not self.api_key:
            raise ValueError(
                "API key for OpenAI or Azure OpenAI must be provided via environment variables"
            )

        self.api_version = _get_env("AZURE_OPENAI_API_VERSION") or "2024-10-21"

        # Detect whether we should use Azure-specific parameters
        self.use_azure: bool = bool(self.endpoint)

        # Normalised model name / deployment id
        self.model_name: str = (
            _get_env("AZURE_OPENAI_EMBEDDING_MODEL")
            or _get_env("EMBEDDING_MODEL")
            or _get_env("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
            or _get_env("AZURE_OPENAI_DEPLOYMENT_NAME")
            or "text-embedding-3-large"
        )
        
        # Support for configurable dimensions (text-embedding-3-large supports 256-3072)
        self.dimensions: Optional[int] = None
        if "text-embedding-3" in self.model_name:
            # Default to 3072 for text-embedding-3-large
            from enhanced_rag.core.config import get_config
            self.dimensions = get_config().embedding.dimensions

        # Instantiate client
        if self.use_azure:
            # Use AzureOpenAI client for Azure endpoints
            self._client = AzureOpenAI(
                api_key=self.api_key,
                azure_endpoint=self.endpoint,
                api_version=self.api_version,
            )  # type: ignore[arg-type]
        else:
            # Use standard OpenAI client
            self._client = OpenAI(api_key=self.api_key)  # type: ignore[arg-type]

        self.logger = logging.getLogger(__name__)

    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate a single embedding vector for text."""
        try:
            kwargs = {
                "input": text,
                "model": self.model_name,
            }
            # Add dimensions parameter for text-embedding-3 models
            if self.dimensions is not None:
                kwargs["dimensions"] = self.dimensions
                
            response = self._client.embeddings.create(**kwargs)
            return response.data[0].embedding  # type: ignore[attr-defined]
        except Exception as exc:
            self.logger.warning("Embedding API error: %s", exc)
            return None

    def generate_embeddings_batch(self, texts: Sequence[str]) -> List[Optional[List[float]]]:
        """Generate embeddings for texts in a single batch request."""
        if not texts:
            return []

        try:
            kwargs = {
                "input": list(texts),
                "model": self.model_name,
            }
            # Add dimensions parameter for text-embedding-3 models
            if self.dimensions is not None:
                kwargs["dimensions"] = self.dimensions
                
            response = self._client.embeddings.create(**kwargs)
            # Sort embeddings by original index to handle out-of-order responses
            embeddings = sorted(response.data, key=lambda e: e.index)
            return [e.embedding for e in embeddings]
        except Exception as exc:
            self.logger.warning("Embedding batch API error: %s", exc)
            # On batch failure, return None for all items
            return [None] * len(texts)

    def generate_code_embedding(self, code: str, context: str) -> Optional[List[float]]:
        """Generate embedding for code with additional context."""
        # Combine context and code to improve semantic signal
        combined = f"{context}\n\nCode:\n{code}"

        MAX_INPUT_CHARS = 6000  # guard against oversized requests
        if len(combined) > MAX_INPUT_CHARS:
            combined = combined[:MAX_INPUT_CHARS] + "..."

        return self.generate_embedding(combined)


class NullEmbeddingProvider(IEmbeddingProvider):
    """Null embedding provider that returns None for all operations."""

    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Always returns None."""
        return None

    def generate_embeddings_batch(self, texts: Sequence[str]) -> List[Optional[List[float]]]:
        """Always returns None for all texts."""
        return [None] * len(texts)

    def generate_code_embedding(self, code: str, context: str) -> Optional[List[float]]:
        """Always returns None."""
        return None