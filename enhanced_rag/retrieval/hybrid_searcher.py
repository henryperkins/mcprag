"""
Hybrid search implementation combining vector and keyword search
"""

import logging
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from ..ranking.filter_manager import FilterManager

from enhanced_rag.azure_integration.rest.operations import SearchOperations
from enhanced_rag.azure_integration.rest.client import AzureSearchClient
from azure.search.documents.models import (
    VectorizedQuery,
    VectorizableTextQuery,
    QueryType,
)
# Note: Azure SDK SearchClient and AzureKeyCredential removed - using REST API only

from ..core.config import get_config, Config
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
        config: Optional[Config | Dict[str, Any]] = None,
        performance_monitor: Optional[PerformanceMonitor] = None,
        rest_ops: Optional[SearchOperations] = None
    ):
        self.performance_monitor = performance_monitor or PerformanceMonitor()
        self.config = config or get_config()
        self.rest_ops = rest_ops
        self._initialize_client()
        self.embedder = None
        self._setup_embedder()

    def _initialize_client(self):
        """Initialize Azure Search client"""
        endpoint: Optional[str] = None
        admin_key: Optional[str] = None
        index_name: Optional[str] = None
        try:
            # --------------------------------------------------------------
            # Resolve Azure Search connection details from the supplied
            # configuration. We support 3 shapes:
            #   1. EnhancedConfig / BaseModel instance – has ``azure`` attr
            #   2. ``dict`` produced by ``Config.model_dump()`` – contains an
            #      ``{"azure": { ... }}`` mapping
            #   3. Fallback to global singleton ``get_config()``.
            # Keeping the logic here avoids duplicating a helper module-wide
            # and ensures **exactly one** place determines the active index
            # name, which is critical for index-stability across the codebase.
            # --------------------------------------------------------------

            # Case 1 – Pydantic config object or object with `.azure`
            def _get_attr_or_key(obj: Any, key: str) -> Optional[Any]:
                """
                Safely get a configuration field from either:
                - an object via attribute access
                - a mapping via key access
                Returns None if missing.
                """
                if obj is None:
                    return None
                # Mapping first, to avoid accidental attribute masking
                try:
                    if isinstance(obj, dict):
                        return obj.get(key)
                except Exception:
                    pass
                try:
                    return getattr(obj, key, None)
                except Exception:
                    return None

            azure_cfg = None
            if hasattr(self.config, "azure"):
                azure_cfg = getattr(self.config, "azure", None)
                endpoint = ((_get_attr_or_key(azure_cfg, "endpoint") or "").strip()) or None
                admin_key = ((_get_attr_or_key(azure_cfg, "admin_key") or "").strip()) or None
                index_name = ((_get_attr_or_key(azure_cfg, "index_name") or "").strip()) or None

            # Case 2 – dict coming from ``model_dump`` or handcrafted
            elif isinstance(self.config, dict):
                azure_section = self.config.get("azure", {})
                endpoint = ((azure_section.get("endpoint") or "").strip()) or None
                admin_key = ((azure_section.get("admin_key") or "").strip()) or None
                index_name = ((azure_section.get("index_name") or "").strip()) or None

            # Case 3 – final fallback to singleton env-driven config
            if not all([endpoint, admin_key, index_name]):
                fallback = get_config()
                azure_fb = getattr(fallback, "azure", None)
                endpoint = endpoint or (((_get_attr_or_key(azure_fb, "endpoint") or "").strip()) or None)
                admin_key = admin_key or (((_get_attr_or_key(azure_fb, "admin_key") or "").strip()) or None)
                index_name = index_name or (((_get_attr_or_key(azure_fb, "index_name") or "").strip()) or None)

            # Absolute last-chance default to preserve historical behaviour
            index_name = index_name or "codebase-mcp-sota"

            # Validate required values and fail fast with clear error
            if not endpoint or not admin_key:
                raise ValueError("Azure Search endpoint/admin_key not configured (empty or missing)")

            self._endpoint = endpoint
            self._index_name = index_name
            self.search_client = None
            if self.rest_ops is None:
                self._rest_client = AzureSearchClient(endpoint=endpoint, api_key=admin_key)
                self.rest_ops = SearchOperations(self._rest_client)

            # Log successful initialization with connection details for debugging
            logger.info(
                "Azure Search client initialized successfully",
                extra={
                    "endpoint_host": self._endpoint.split('://')[-1] if hasattr(self, "_endpoint") else None,
                    "index_name": self._index_name,
                    "component": "enhanced_rag.retrieval.hybrid_searcher",
                },
            )
        except Exception as e:
            try:
                ep = (endpoint or "").split("://")[-1]
            except Exception:
                ep = None
            logger.error(
                "Failed to initialize Azure Search client for HybridSearcher",
                exc_info=True,
                extra={
                    "endpoint_host": ep,
                    "index_name": index_name,
                    "has_admin_key": bool(admin_key),
                    "component": "enhanced_rag.retrieval.hybrid_searcher",
                },
            )
            self.search_client = None
            self._rest_client = None
            self.rest_ops = None

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
        if not self.rest_ops:
            logger.error(
                "REST SearchOperations not initialized; hybrid search unavailable",
                extra={"endpoint_host": getattr(self, "_endpoint", None), "index_name": getattr(self, "_index_name", None)}
            )
            return []

        # Detect exact-match tokens: quoted phrases and numeric literals
        import re as _re
        quoted = _re.findall(r'"([^"]+)"|\'([^\']+)\'', query)
        quoted_terms = [q for pair in quoted for q in pair if q]
        numeric_terms = _re.findall(r'(?<![\w.])(\d{2,})(?![\w.])', query)
        exact_terms = [t.strip() for t in (quoted_terms + numeric_terms) if t.strip()]

        # Clamp length and ASCII range to avoid malformed filters
        def _clamp_term(t: str) -> str:
            t = t[:200]
            return "".join(ch for ch in t if 32 <= ord(ch) <= 126)
        exact_terms = [_clamp_term(t) for t in exact_terms]

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
            body = {
                "queryType": "semantic",
                "semanticConfiguration": "semantic-config",
                "queryCaption": "extractive",
                "queryAnswer": "extractive",
                "filter": kw_sem_kwargs.get("filter"),
                "top": kw_sem_kwargs.get("top", top_k * 2),
                "includeTotalCount": kw_sem_kwargs.get("include_total_count", include_total_count),
            }
            resp = await self.rest_ops.search(self._index_name, query=kw_sem_kwargs.get("search_text", query), **body)
            kw_sem_results = self._process_results(resp.get("value", []))
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
                    # Properly escape and validate the term to prevent injection
                    # First, escape single quotes for OData string literals
                    safe = term.replace("'", "''")

                    # Additional validation to detect and reject suspicious patterns
                    suspicious_patterns = [
                        ' or ', ' and ', ' eq ', ' ne ', ' gt ', ' lt ',
                        ' ge ', ' le ', '(', ')', '--', '/*', '*/', ';'
                    ]
                    for pattern in suspicious_patterns:
                        if pattern in safe.lower():
                            logger.warning(f"Suspicious term detected and rejected: {term}")
                            # Return a safe no-op filter that matches nothing
                            return "(1 eq 0)"

                    # Limit term length to prevent buffer-based attacks
                    if len(safe) > 200:
                        safe = safe[:200]

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
                resp = await self.rest_ops.search(self._index_name, query="*", filter=combined_filter, top=exact_kwargs.get("top", top_k * 2))
                exact_results = self._process_results(resp.get("value", []))
            except Exception as e:
                logger.warning("Exact-match fallback pass failed – %s", e)

        # ------------------------------------------------------------------
        # 2.  Build vector request  (server-side TextVectorization if possible)
        # ------------------------------------------------------------------
        vec_results: List[HybridSearchResult] = []
        try:
            emb = None
            if self.embedder:
                try:
                    emb = self.embedder.generate_embedding(query)
                except Exception:
                    emb = None
            vq = VectorizedQuery(vector=emb, k_nearest_neighbors=top_k * 2, fields="content_vector") if emb else None
            vec_kwargs = self._sanitize_search_kwargs({
                "search_text": "",
                "vector_queries": [vq] if vq else None,
                "filter": filter_expr,
                "top": top_k * 2,
                "include_total_count": False,
                "timeout": (deadline_ms / 1000) if deadline_ms else None,
            })
            options: Dict[str, Any] = {"top": vec_kwargs.get("top", top_k * 2)}
            if vq and emb:
                options["vectorQueries"] = [{"vector": emb, "k": top_k * 2, "fields": "content_vector"}]
            if filter_expr:
                options["filter"] = filter_expr
            resp = await self.rest_ops.search(self._index_name, query="", **options)
            vec_results = self._process_results(resp.get("value", []))
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
                    # Mark that this item received exact boost
                    by_id[r.id].metadata["exact_boost"] = True
                else:
                    # Seed unseen exact hits so they can surface
                    metadata_with_boost = r.metadata.copy()
                    metadata_with_boost["exact_boost"] = True
                    by_id[r.id] = HybridSearchResult(
                        id=r.id,
                        score=max(r.score, 1.0) * exact_boost,
                        content=r.content,
                        metadata=metadata_with_boost,
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
        if not self.rest_ops:
            logger.warning(
                "Vector search not available, REST client not initialized."
            )
            return []

        vector_query = self._build_vector_query(query, top_k)
        if not vector_query:
            logger.warning("Could not build vector query for: %s", query)
            return []

        try:
            # Execute vector search using REST API
            options: Dict[str, Any] = {"top": top_k}
            if isinstance(vector_query, VectorizedQuery) and getattr(vector_query, "vector", None):
                options["vectorQueries"] = [{"vector": vector_query.vector, "k": top_k, "fields": "content_vector"}]
            if filter_expr:
                options["filter"] = filter_expr
            resp = await self.rest_ops.search(self._index_name, query="", **options)
            return self._process_results(resp.get("value", []))
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
        if not self.rest_ops:
            logger.warning("Keyword search not available")
            return []

        try:
            body: Dict[str, Any] = {
                "queryType": "simple",
                "top": top_k,
                "includeTotalCount": True,
            }
            if filter_expr:
                body["filter"] = filter_expr
            resp = await self.rest_ops.search(self._index_name, query=query, **body)
            return self._process_results(resp.get("value", []))
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
        """
        Back-compat wrapper for hybrid search combining vector and keyword results.
        This delegates to the newer 'search' method but preserves the vector_weight knob.
        """
        # Map legacy two-weight model onto the newer three-weight fusion:
        # allocate remaining weight to "semantic", leave keyword weight minimal (still non-zero).
        semantic_weight = max(0.0, 1.0 - vector_weight)
        keyword_weight = 0.0

        return await self.search(
            query=query,
            filter_expr=filter_expr,
            top_k=top_k,
            include_total_count=True,
            vector_weight=vector_weight,
            semantic_weight=semantic_weight,
            keyword_weight=keyword_weight,
            deadline_ms=None,
            exact_boost=0.35,
        )

    def _combine_results(
        self,
        vector_results: List[HybridSearchResult],
        keyword_results: List[HybridSearchResult],
        vector_weight: float
    ) -> List[HybridSearchResult]:
        """
        Combine vector and keyword results with weighted scoring.
        Note: This helper is retained for reference but the preferred path is 'search()'.
        """
        combined: Dict[str, HybridSearchResult] = {}
        keyword_weight = max(0.0, 1.0 - vector_weight)

        for result in vector_results:
            combined[result.id] = HybridSearchResult(
                id=result.id,
                score=result.score * vector_weight,
                content=result.content,
                metadata=dict(result.metadata),
            )

        for result in keyword_results:
            if result.id in combined:
                combined[result.id].score += result.score * keyword_weight
            else:
                combined[result.id] = HybridSearchResult(
                    id=result.id,
                    score=result.score * keyword_weight,
                    content=result.content,
                    metadata=dict(result.metadata),
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
                        'highlights': result.get('@search.highlights', {}),
                        'docstring': result.get('docstring'),
                        'signature': result.get('signature'),
                        'imports': result.get('imports'),
                        'semantic_context': result.get('semantic_context')
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
