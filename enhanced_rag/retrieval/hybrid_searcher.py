"""
Hybrid search implementation combining vector and keyword search
"""

import logging
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass

from azure.search.documents import SearchClient
from azure.search.documents.models import (
    VectorizedQuery,
    VectorizableTextQuery,
    QueryType,
)
from azure.core.credentials import AzureKeyCredential
from enhanced_rag.utils.error_handler import with_retry

from ..core.config import get_config
from enhanced_rag.utils.performance_monitor import PerformanceMonitor

logger = logging.getLogger(__name__)


@dataclass
class HybridSearchResult:
    """Result from hybrid search"""
    id: str
    score: float
    content: str
    metadata: Dict[str, Any]


class HybridSearcher:
    """
    Implements hybrid search combining vector similarity and keyword matching
    """

    def _sanitize_search_kwargs(self, params: dict) -> dict:
        """
        Compatibility shim:
        - Map legacy 'count' -> 'include_total_count'
        - Whitelist only supported SDK kwargs
        - Drop unknown keys to avoid passing unexpected HTTP params
        """
        if not params:
            return {}
        out = {}
        for k, v in params.items():
            if k == "count":
                out["include_total_count"] = bool(v)
            elif k in {
                "search_text",
                "query_type",
                "semantic_configuration_name",
                "query_caption",
                "query_answer",
                "filter",
                "top",
                "include_total_count",
                "disable_randomization",
                "timeout",
                "vector_queries",
                "facets",
                "highlight_fields",
                "highlight_pre_tag",
                "highlight_post_tag",
                "scoring_profile",
                "scoring_parameters",
                "search_fields",
            }:
                if v is not None:
                    out[k] = v
        return out

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        performance_monitor: Optional[PerformanceMonitor] = None
    ):
        self.performance_monitor = performance_monitor or PerformanceMonitor()
        self.config = config or get_config()
        self._initialize_client()
        self.embedder = None
        self._setup_embedder()

    def _initialize_client(self):
        """Initialize Azure Search client"""
        try:
            # Support both Config object and dict-like config
            if hasattr(self.config, "azure"):
                endpoint = getattr(self.config.azure, "endpoint", None)
                admin_key = getattr(self.config.azure, "admin_key", None)
                index_name = getattr(self.config.azure, "index_name", None) or "codebase-mcp-sota"
            else:
                fallback = get_config()
                endpoint = getattr(fallback.azure, "endpoint", None)
                admin_key = getattr(fallback.azure, "admin_key", None)
                index_name = getattr(fallback.azure, "index_name", None) or "codebase-mcp-sota"

            credential = AzureKeyCredential(admin_key)
            self.search_client = SearchClient(
                endpoint=endpoint,
                index_name=index_name,
                credential=credential
            )
        except Exception as e:
            logger.error(f"Failed to initialize search client: {e}")
            self.search_client = None

    def _setup_embedder(self):
        """Setup vector embedder if available"""
        try:
            from enhanced_rag.azure_integration import AzureOpenAIEmbeddingProvider
            self.embedder = AzureOpenAIEmbeddingProvider()
            logger.info("✅ Vector embedder initialized")
        except ImportError:
            logger.warning(
                "Vector embeddings not available, falling back to keyword search only"
            )
            self.embedder = None
        except Exception as e:
            logger.error(f"Failed to initialize embedder: {e}")
            self.embedder = None

    # ------------------------------------------------------------------ #
    #  NEW  – unified hybrid entry-point with semantic + vector + keyword
    # ------------------------------------------------------------------ #

    async def search(
        self,
        query: str,
        filter_expr: Optional[str] = None,
        top_k: int = 20,
        *,
        include_total_count: bool = True,
        vector_weight: float = 0.4,
        semantic_weight: float = 0.4,
        keyword_weight: float = 0.2,
        deadline_ms: Optional[int] = None,
        exact_boost: float = 0.35,
    ) -> List[HybridSearchResult]:
        """
        Full hybrid search (semantic + keyword + vector) with
        deterministic pagination and weighted score fusion.

        Adds exact-term fallback boosting for numeric tokens and quoted phrases.
        """
        # Detect exact-match tokens: quoted phrases and numeric literals
        import re as _re
        quoted = _re.findall(r'"([^"]+)"|\'([^\']+)\'', query)
        quoted_terms = [q for pair in quoted for q in pair if q]
        numeric_terms = _re.findall(r'(?<![\w.])(\d{2,})(?![\w.])', query)
        exact_terms = [t.strip() for t in (quoted_terms + numeric_terms) if t.strip()]

        # ------------------------------------------------------------------
        # 1.  Build keyword/semantic request
        # ------------------------------------------------------------------
        kw_sem_results: List[HybridSearchResult] = []
        try:
            kw_sem_kwargs = self._sanitize_search_kwargs({
                "search_text": query,
                "query_type": QueryType.SEMANTIC,
                "semantic_configuration_name": "semantic-config",
                "query_caption": "extractive",
                "query_answer": "extractive",
                "filter": filter_expr,
                "top": top_k * 2,
                "include_total_count": include_total_count,
                "disable_randomization": True,  # deterministic
                "timeout": (deadline_ms / 1000) if deadline_ms else None,
            })
            kw_sem = self.search_client.search(**kw_sem_kwargs)
            kw_sem_results = self._process_results(kw_sem)
        except Exception as e:
            logger.warning("Keyword/Semantic path failed – %s", e)

        # ------------------------------------------------------------------
        # 1b. Exact lexical fallback pass (if exact_terms present)
        # ------------------------------------------------------------------
        exact_results: List[HybridSearchResult] = []
        if exact_terms:
            try:
                # Build a strict filter using search.ismatch for each term over key text fields
                # We OR the fields for a term and AND across terms to enforce presence of all exact terms.
                def _term_filter(term: str) -> str:
                    safe = term.replace("'", "''")
                    return "(" + " or ".join([
                        f"search.ismatch('{safe}', 'content')",
                        f"search.ismatch('{safe}', 'function_name')",
                        f"search.ismatch('{safe}', 'class_name')",
                        f"search.ismatch('{safe}', 'docstring')",
                    ]) + ")"
                combined_exact = " and ".join([_term_filter(t) for t in exact_terms])
                combined_filter = combined_exact if not filter_expr else f"({filter_expr}) and {combined_exact}"

                exact_kwargs = self._sanitize_search_kwargs({
                    "search_text": "",  # rely on filter to force must-have terms
                    "query_type": QueryType.SIMPLE,
                    "filter": combined_filter,
                    "top": top_k * 2,
                    "include_total_count": False,
                    "disable_randomization": True,
                    "timeout": (deadline_ms / 1000) if deadline_ms else None,
                })
                ex = self.search_client.search(**exact_kwargs)
                exact_results = self._process_results(ex)
            except Exception as e:
                logger.warning("Exact-match fallback pass failed – %s", e)

        # ------------------------------------------------------------------
        # 2.  Build vector request  (server-side TextVectorization if possible)
        # ------------------------------------------------------------------
        vec_results: List[HybridSearchResult] = []
        try:
            vq = VectorizedQuery(
                vector=self.embedder.generate_embedding(query)
                if self.embedder
                else None,
                k_nearest_neighbors=top_k * 2,
                fields="content_vector",
            )
            vec_kwargs = self._sanitize_search_kwargs({
                "search_text": "",
                "vector_queries": [vq],
                "filter": filter_expr,
                "top": top_k * 2,
                "include_total_count": False,
                "timeout": (deadline_ms / 1000) if deadline_ms else None,
            })
            vec = self.search_client.search(**vec_kwargs)
            vec_results = self._process_results(vec)
        except Exception as e:
            logger.warning("Vector path failed – %s", e)

        # ------------------------------------------------------------------
        # 3.  Fuse scores  (linear-weighted) + exact boost
        # ------------------------------------------------------------------
        by_id: Dict[str, HybridSearchResult] = {}

        def _update(result: HybridSearchResult, weight: float):
            if result.id not in by_id:
                by_id[result.id] = HybridSearchResult(
                    id=result.id,
                    score=result.score * weight,
                    content=result.content,
                    metadata=result.metadata,
                )
            else:
                by_id[result.id].score += result.score * weight

        for r in kw_sem_results:
            _update(r, semantic_weight if "@search.rerankerScore" in r.metadata else keyword_weight)
        for r in vec_results:
            _update(r, vector_weight)
        # Apply exact boost as an additive weight to already seen ids; if new, create with small base
        if exact_results:
            for r in exact_results:
                if r.id in by_id:
                    by_id[r.id].score += max(r.score, 1.0) * exact_boost
                else:
                    # Seed unseen exact hits so they can surface
                    by_id[r.id] = HybridSearchResult(
                        id=r.id,
                        score=max(r.score, 1.0) * exact_boost,
                        content=r.content,
                        metadata=r.metadata,
                    )

        fused = sorted(by_id.values(), key=lambda x: x.score, reverse=True)[:top_k]
        return fused


# ------------------------------------------------------------------ #
#  (legacy) vector_search / keyword_search wrappers kept for callers
# ------------------------------------------------------------------ #

    async def vector_search(
        self,
        query: str,
        vector_queries: Optional[List[Union[VectorizedQuery, VectorizableTextQuery]]] = None,
        filter_expr: Optional[str] = None,
        top_k: int = 50
    ) -> List[HybridSearchResult]:
        """Execute vector similarity search (wrapper keeps old API)"""
        if not self.search_client:
            logger.warning(
                "Vector search not available, search client not initialized."
            )
            return []

        vector_query = self._build_vector_query(query, top_k)
        if not vector_query:
            logger.warning("Could not build vector query for: %s", query)
            return []

        try:
            # Execute vector search with retries
            results = with_retry(
                self.search_client.search,
                search_text=None,
                vector_queries=[vector_query],
                filter=filter_expr,
                top=top_k
            )
            return self._process_results(results)
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    async def keyword_search(
        self,
        query: str,
        filter_expr: Optional[str] = None,
        top_k: int = 50
    ) -> List[HybridSearchResult]:
        """Execute keyword-based search"""
        if not self.search_client:
            logger.warning("Keyword search not available")
            return []

        try:
            # Execute keyword/semantic search with advanced params and retries
            # Select scoring profile with safe defaults
            scoring_profile = "code_quality_boost"
            try:
                if hasattr(self.config, "azure") and getattr(self.config, "azure"):
                    scoring_profile = getattr(
                        self.config.azure,
                        "default_scoring_profile",
                        "code_quality_boost",
                    )
            except Exception:
                scoring_profile = "code_quality_boost"
            enable_semantic = True
            kw_kwargs = self._sanitize_search_kwargs({
                "search_text": query,
                "query_type": QueryType.SEMANTIC if enable_semantic else QueryType.SIMPLE,
                "semantic_configuration_name": "semantic-config" if enable_semantic else None,
                "scoring_profile": scoring_profile,
                "filter": filter_expr,
                "facets": ["language,count:20", "repository,count:20", "tags,count:20"],
                "query_caption": "extractive" if enable_semantic else None,
                "query_answer": "extractive" if enable_semantic else None,
                "highlight_fields": "content,docstring",
                "include_total_count": True,
                "top": top_k,
                "search_fields": ["content", "function_name", "class_name", "docstring"],
            })
            results = with_retry(self.search_client.search, **kw_kwargs)
            return self._process_results(results)
        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return []

    async def hybrid_search(
        self,
        query: str,
        filter_expr: Optional[str] = None,
        top_k: int = 50,
        vector_weight: float = 0.5
    ) -> List[HybridSearchResult]:
        """Execute hybrid search combining vector and keyword results"""

        # Execute both searches in parallel
        vector_results = await self.vector_search(query, filter_expr, top_k * 2)
        keyword_results = await self.keyword_search(query, filter_expr, top_k * 2)

        # Combine results with weighted scoring
        combined_results = self._combine_results(
            vector_results,
            keyword_results,
            vector_weight
        )

        # Sort by combined score and return top-k
        combined_results.sort(key=lambda x: x.score, reverse=True)
        return combined_results[:top_k]

    def _combine_results(
        self,
        vector_results: List[HybridSearchResult],
        keyword_results: List[HybridSearchResult],
        vector_weight: float
    ) -> List[HybridSearchResult]:
        """Combine vector and keyword results with weighted scoring"""
        combined = {}
        keyword_weight = 1 - vector_weight

        # Add vector results
        for result in vector_results:
            combined[result.id] = HybridSearchResult(
                id=result.id,
                score=result.score * vector_weight,
                content=result.content,
                metadata=result.metadata
            )

        # Add or update with keyword results
        for result in keyword_results:
            if result.id in combined:
                combined[result.id].score += result.score * keyword_weight
            else:
                combined[result.id] = HybridSearchResult(
                    id=result.id,
                    score=result.score * keyword_weight,
                    content=result.content,
                    metadata=result.metadata
                )

        return list(combined.values())

    def _process_results(self, results) -> List[HybridSearchResult]:
        """Process Azure Search results into HybridSearchResult objects"""
        processed = []

        for result in results:
            try:
                processed.append(HybridSearchResult(
                    id=result.get('id', ''),
                    score=result.get('@search.score', 0.0),
                    content=result.get('content', ''),
                    metadata={
                        'file_path': result.get('file_path'),
                        'repository': result.get('repository'),
                        'language': result.get('language'),
                        'function_name': result.get('function_name'),
                        'class_name': result.get('class_name'),
                        'highlights': result.get('@search.highlights', {})
                    }
                ))
            except Exception as e:
                logger.error(f"Error processing result: {e}")
                continue

        return processed

    def _build_vector_query(self, query: str, k: int) -> Optional[Any]:
        """Build vector query, preferring server-side vectorization."""
        try:
            # Prefer server-side vectorization with VectorizableTextQuery
            return VectorizableTextQuery(
                text=query, k_nearest_neighbors=k, fields="content_vector"
            )
        except Exception:
            # Fallback to client-side vectorization if the above is not supported
            # or if an embedder is explicitly available.
            if self.embedder:
                try:
                    embedding = self.embedder.generate_embedding(query)
                    if embedding:
                        return VectorizedQuery(
                            vector=embedding, k_nearest_neighbors=k, fields="content_vector"
                        )
                except Exception as e:
                    logger.error(f"Client-side embedding failed: {e}")
        return None
