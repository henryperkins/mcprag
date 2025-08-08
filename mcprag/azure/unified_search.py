"""Unified Azure AI Search client for all transports."""

from __future__ import annotations

import logging
import asyncio
from typing import Any, Dict, List, Optional

from ..config import Config

# Optional REST client/ops from enhanced_rag
try:
    from enhanced_rag.azure_integration.rest import AzureSearchClient as RestAzureSearchClient, SearchOperations as RestSearchOperations
    _REST_AVAILABLE = True
except Exception:
    RestAzureSearchClient = None  # type: ignore
    RestSearchOperations = None  # type: ignore
    _REST_AVAILABLE = False

# Optional embedding provider
try:
    from enhanced_rag.azure_integration.embedding_provider import AzureOpenAIEmbeddingProvider
    _EMBED_AVAILABLE = True
except Exception:
    AzureOpenAIEmbeddingProvider = None  # type: ignore
    _EMBED_AVAILABLE = False

# Optional Azure SDK fallback
try:
    from azure.search.documents import SearchClient as SdkSearchClient
    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents.models import VectorizedQuery
    _SDK_AVAILABLE = True
except Exception:
    SdkSearchClient = None  # type: ignore
    AzureKeyCredential = None  # type: ignore
    VectorizedQuery = None  # type: ignore
    _SDK_AVAILABLE = False

logger = logging.getLogger(__name__)


class UnifiedSearchClient:
    """Unified Azure AI Search client with consistent behavior across transports."""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        index_name: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.endpoint = (endpoint or Config.ENDPOINT or "").rstrip("/")
        self.index_name = index_name or Config.INDEX_NAME
        self.api_key = api_key or (Config.ADMIN_KEY or Config.QUERY_KEY)

        self.rest_ops: Optional[RestSearchOperations] = None  # type: ignore
        self.rest_client: Optional[RestAzureSearchClient] = None  # type: ignore
        self.sdk_client: Optional[SdkSearchClient] = None  # type: ignore

        if _REST_AVAILABLE and self.endpoint and self.api_key:
            try:
                self.rest_client = RestAzureSearchClient(
                    endpoint=self.endpoint, api_key=self.api_key
                )  # type: ignore[call-arg]
                self.rest_ops = RestSearchOperations(self.rest_client)  # type: ignore[call-arg]
                logger.info("UnifiedSearchClient using REST SearchOperations")
            except Exception as e:
                logger.warning("REST SearchOperations init failed: %s", e)
                self.rest_client = None
                self.rest_ops = None

        if not self.rest_ops and _SDK_AVAILABLE and self.endpoint and self.api_key:
            try:
                cred = AzureKeyCredential(self.api_key)  # type: ignore[call-arg]
                self.sdk_client = SdkSearchClient(
                    endpoint=self.endpoint,
                    index_name=self.index_name,
                    credential=cred,
                )  # type: ignore[call-arg]
                logger.info("UnifiedSearchClient using Azure SDK SearchClient")
            except Exception as e:
                logger.warning("Azure SDK SearchClient init failed: %s", e)
                self.sdk_client = None

        self.embedding = None
        if _EMBED_AVAILABLE:
            try:
                self.embedding = AzureOpenAIEmbeddingProvider()  # type: ignore[call-arg]
            except Exception as e:
                logger.info("Embedding provider not available: %s", e)
                self.embedding = None

    async def search(
        self,
        query: str,
        use_vector: bool = True,
        use_bm25: bool = True,
        filter_expression: Optional[str] = None,
        top: int = 10,
        skip: int = 0,
    ) -> List[Dict[str, Any]]:
        """Perform unified search across transports."""
        vector: Optional[List[float]] = None
        if use_vector and self.embedding:
            vector = await self._get_embedding_async(query)

        if self.rest_ops:
            options: Dict[str, Any] = {
                "top": top,
                "skip": skip,
                "filter": filter_expression,
                "count": True,
            }
            if vector:
                options["vectorQueries"] = [
                    {
                        "kind": "vector",
                        "vector": vector,
                        "k": top,
                        "fields": ["contentVector"],
                    }
                ]
            # REST API: use "*" when BM25 disabled
            safe_query = query if use_bm25 else "*"
            resp = await self.rest_ops.search(  # type: ignore[arg-type]
                self.index_name, safe_query, **options
            )
            return self._format_rest_results(resp)

        if self.sdk_client:
            loop = asyncio.get_running_loop()

            def _do_search() -> List[Dict[str, Any]]:
                kwargs: Dict[str, Any] = {}
                if filter_expression:
                    kwargs["filter"] = filter_expression
                if vector and VectorizedQuery is not None:
                    try:
                        vq = VectorizedQuery(  # type: ignore[call-arg]
                            vector=vector,
                            k_nearest_neighbors=top,
                            fields="contentVector",
                        )
                        kwargs["vector_queries"] = [vq]
                    except Exception:
                        # ignore vector if SDK does not support this version
                        pass
                # search_text can be None for vector-only queries
                search_text = query if use_bm25 else None
                results = self.sdk_client.search(  # type: ignore[call-arg]
                    search_text=search_text, top=top, skip=skip, **kwargs
                )
                items: List[Dict[str, Any]] = []
                for r in results:
                    if isinstance(r, dict):
                        doc = r
                        score = r.get("@search.score")
                    else:
                        try:
                            doc = dict(r)  # type: ignore[arg-type]
                        except Exception:
                            doc = {}
                        score = doc.get("@search.score")
                    items.append(self._format_doc(doc, score))
                return items

            return await loop.run_in_executor(None, _do_search)

        logger.error(
            "UnifiedSearchClient has no available backend client; check configuration."
        )
        return []

    def _format_rest_results(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        values = response.get("value", []) if isinstance(response, dict) else []
        items: List[Dict[str, Any]] = []
        for v in values:
            score = None
            if isinstance(v, dict):
                score = v.get("@search.score")
            items.append(self._format_doc(v if isinstance(v, dict) else {}, score))
        return items

    def _format_doc(self, doc: Dict[str, Any], score: Optional[float]) -> Dict[str, Any]:
        return {
            "id": doc.get("id") or doc.get("key") or doc.get("documentId"),
            "file": doc.get("file") or doc.get("path") or doc.get("filepath"),
            "content": doc.get("content") or doc.get("text") or doc.get("body"),
            "relevance": score if score is not None else doc.get("@search.score") or 0,
            "repository": doc.get("repository") or doc.get("repo"),
            "language": doc.get("language") or doc.get("lang"),
        }

    async def _get_embedding_async(self, text: str) -> Optional[List[float]]:
        if not self.embedding:
            return None
        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(
                None, lambda: self.embedding.generate_embedding(text)  # type: ignore[call-arg]
            )
        except Exception as e:
            logger.debug("Embedding generation failed: %s", e)
            return None