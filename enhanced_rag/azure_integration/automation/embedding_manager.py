"""Embedding automation for Azure AI Search.

This module integrates embedding generation into the automation framework,
providing batch processing, caching, and quality monitoring capabilities.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple, Sequence, Callable, Awaitable
from datetime import datetime, timedelta
import hashlib
import asyncio
from collections import defaultdict

from ..rest import SearchOperations
from ..embedding_provider import IEmbeddingProvider, AzureOpenAIEmbeddingProvider, NullEmbeddingProvider

logger = logging.getLogger(__name__)


class EmbeddingAutomation:
    """Automate embedding generation and management tasks."""

    def __init__(self,
                 operations: SearchOperations,
                 embedding_provider: Optional[IEmbeddingProvider] = None,
                 cache_ttl_seconds: int = 3600):
        """Initialize embedding automation.

        Args:
            operations: SearchOperations instance
            embedding_provider: Embedding provider (auto-created if None)
            cache_ttl_seconds: Cache TTL in seconds
        """
        self.ops = operations
        self.provider = embedding_provider or self._create_default_provider()
        self.cache_ttl = cache_ttl_seconds
        self._embedding_cache: Dict[str, Tuple[List[float], datetime]] = {}
        self._stats = defaultdict(int)

    def _create_default_provider(self) -> IEmbeddingProvider:
        """Create default embedding provider."""
        try:
            return AzureOpenAIEmbeddingProvider()
        except Exception as e:
            logger.warning(f"Failed to create OpenAI provider: {e}, using null provider")
            return NullEmbeddingProvider()

    def _cache_key(self, text: str) -> str:
        """Generate cache key for text."""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    def _is_cache_valid(self, cached_time: datetime) -> bool:
        """Check if cached entry is still valid."""
        return (datetime.utcnow() - cached_time).total_seconds() < self.cache_ttl

    async def generate_embedding(
        self,
        text: str,
        use_cache: bool = True,
        context: Optional[str] = None
    ) -> Optional[List[float]]:
        """Generate embedding for text with caching.

        Args:
            text: Text to embed
            use_cache: Whether to use cache
            context: Optional context for code embeddings

        Returns:
            Embedding vector or None
        """
        # Generate cache key once (needed for both lookup and storage)
        cache_key = self._cache_key(text + (context or "")) if use_cache else None

        # Check cache
        if use_cache and cache_key:
            if cache_key in self._embedding_cache:
                embedding, cached_time = self._embedding_cache[cache_key]
                if self._is_cache_valid(cached_time):
                    self._stats["cache_hits"] += 1
                    return embedding

        # Generate embedding
        self._stats["cache_misses"] += 1
        if context:
            embedding = self.provider.generate_code_embedding(text, context)
        else:
            embedding = self.provider.generate_embedding(text)

        # Cache result
        if embedding and use_cache and cache_key:
            self._embedding_cache[cache_key] = (embedding, datetime.utcnow())
            self._stats["embeddings_generated"] += 1

        return embedding

    async def generate_embeddings_batch(
        self,
        texts: Sequence[str],
        batch_size: int = 100,
        use_cache: bool = True,
        progress_callback: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None
    ) -> List[Optional[List[float]]]:
        """Generate embeddings for multiple texts efficiently.

        Args:
            texts: Texts to embed
            batch_size: Batch size for API calls
            use_cache: Whether to use cache
            progress_callback: Optional progress callback

        Returns:
            List of embeddings (None for failures)
        """
        results = [None] * len(texts)
        uncached_indices = []
        uncached_texts = []

        # Check cache first
        if use_cache:
            for i, text in enumerate(texts):
                cache_key = self._cache_key(text)
                if cache_key in self._embedding_cache:
                    embedding, cached_time = self._embedding_cache[cache_key]
                    if self._is_cache_valid(cached_time):
                        results[i] = embedding
                        self._stats["cache_hits"] += 1
                    else:
                        uncached_indices.append(i)
                        uncached_texts.append(text)
                else:
                    uncached_indices.append(i)
                    uncached_texts.append(text)
        else:
            uncached_indices = list(range(len(texts)))
            uncached_texts = list(texts)

        # Process uncached texts in batches
        for i in range(0, len(uncached_texts), batch_size):
            batch_texts = uncached_texts[i:i + batch_size]
            batch_indices = uncached_indices[i:i + batch_size]

            # Generate embeddings
            batch_embeddings = self.provider.generate_embeddings_batch(batch_texts)

            # Store results and update cache
            for idx, text, embedding in zip(batch_indices, batch_texts, batch_embeddings):
                results[idx] = embedding
                if embedding and use_cache:
                    cache_key = self._cache_key(text)
                    self._embedding_cache[cache_key] = (embedding, datetime.utcnow())
                    self._stats["embeddings_generated"] += 1

            # Progress callback
            if progress_callback:
                if asyncio.iscoroutinefunction(progress_callback):
                    await progress_callback({
                        "processed": min(i + batch_size, len(uncached_texts)),
                        "total": len(uncached_texts),
                        "cached": len(texts) - len(uncached_texts)
                    })
                else:
                    progress_callback({
                        "processed": min(i + batch_size, len(uncached_texts)),
                        "total": len(uncached_texts),
                        "cached": len(texts) - len(uncached_texts)
                    })

        return results

    async def enrich_documents_with_embeddings(
        self,
        documents: List[Dict[str, Any]],
        text_field: str = "content",
        embedding_field: str = "content_vector",
        context_fields: Optional[List[str]] = None,
        batch_size: int = 100
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Enrich documents with embeddings.

        Args:
            documents: Documents to enrich
            text_field: Field containing text to embed
            embedding_field: Field to store embedding
            context_fields: Optional fields for context
            batch_size: Batch size for embedding generation

        Returns:
            Tuple of (enriched documents, statistics)
        """
        start_time = datetime.utcnow()

        # Extract texts and contexts
        texts = []
        contexts = []
        valid_indices = []

        for i, doc in enumerate(documents):
            if text_field in doc and doc[text_field]:
                texts.append(doc[text_field])

                # Build context from specified fields
                if context_fields:
                    context_parts = []
                    for field in context_fields:
                        if field in doc and doc[field]:
                            context_parts.append(f"{field}: {doc[field]}")
                    contexts.append("\n".join(context_parts) if context_parts else None)
                else:
                    contexts.append(None)

                valid_indices.append(i)

        # Generate embeddings
        if contexts and any(contexts):
            # Generate with context
            embeddings = []
            for text, context in zip(texts, contexts):
                if context:
                    embedding = await self.generate_embedding(text, context=context)
                else:
                    embedding = await self.generate_embedding(text)
                embeddings.append(embedding)
        else:
            # Batch generate without context
            embeddings = await self.generate_embeddings_batch(texts, batch_size=batch_size)

        # Enrich documents
        enriched_count = 0
        failed_count = 0

        for idx, embedding in zip(valid_indices, embeddings):
            if embedding:
                documents[idx][embedding_field] = embedding
                enriched_count += 1
            else:
                failed_count += 1

        elapsed = (datetime.utcnow() - start_time).total_seconds()

        stats = {
            "total_documents": len(documents),
            "processed": len(texts),
            "enriched": enriched_count,
            "failed": failed_count,
            "elapsed_seconds": round(elapsed, 2),
            "cache_stats": dict(self._stats)
        }

        return documents, stats

    async def validate_embeddings(
        self,
        index_name: str,
        sample_size: int = 100,
        expected_dimensions: int = 1536  # OpenAI text-embedding-3-large standard dimensions
    ) -> Dict[str, Any]:
        """Validate embeddings in an index.

        Args:
            index_name: Index name
            sample_size: Number of documents to sample
            expected_dimensions: Expected embedding dimensions

        Returns:
            Validation results
        """
        results = {
            "index_name": index_name,
            "expected_dimensions": expected_dimensions,
            "sample_size": sample_size,
            "validation_time": datetime.utcnow().isoformat()
        }

        try:
            # Get sample documents
            search_results = await self.ops.search(
                index_name=index_name,
                query="*",
                select=["id", "content_vector"],
                top=sample_size
            )

            documents = search_results.get("value", [])
            results["documents_checked"] = len(documents)

            # Analyze embeddings
            valid_count = 0
            invalid_count = 0
            missing_count = 0
            dimension_issues = []

            for doc in documents:
                if "content_vector" not in doc:
                    missing_count += 1
                elif not isinstance(doc["content_vector"], list):
                    invalid_count += 1
                elif len(doc["content_vector"]) != expected_dimensions:
                    invalid_count += 1
                    dimension_issues.append({
                        "id": doc["id"],
                        "actual_dimensions": len(doc["content_vector"])
                    })
                else:
                    valid_count += 1

            results["valid_embeddings"] = valid_count
            results["invalid_embeddings"] = invalid_count
            results["missing_embeddings"] = missing_count
            results["dimension_issues"] = dimension_issues[:10]  # First 10 issues
            results["validation_passed"] = (invalid_count == 0 and missing_count == 0)

        except Exception as e:
            results["error"] = str(e)
            results["validation_passed"] = False

        return results

    async def clear_embedding_cache(self) -> Dict[str, Any]:
        """Clear the embedding cache.

        Returns:
            Cache statistics before clearing
        """
        stats = {
            "entries_cleared": len(self._embedding_cache),
            "cache_stats": dict(self._stats),
            "cleared_at": datetime.utcnow().isoformat()
        }

        self._embedding_cache.clear()
        self._stats.clear()

        return stats

    async def get_embedding_stats(self) -> Dict[str, Any]:
        """Get embedding generation statistics.

        Returns:
            Current statistics
        """
        cache_size = len(self._embedding_cache)
        valid_entries = sum(
            1 for _, (_, cached_time) in self._embedding_cache.items()
            if self._is_cache_valid(cached_time)
        )

        return {
            "provider_type": type(self.provider).__name__,
            "cache_size": cache_size,
            "valid_cache_entries": valid_entries,
            "cache_ttl_seconds": self.cache_ttl,
            "stats": dict(self._stats),
            "timestamp": datetime.utcnow().isoformat()
        }
