"""
Multi-stage retrieval pipeline orchestrating different search strategies
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
# from ..utils.performance_monitor import PerformanceMonitor  # currently unused

from azure.search.documents import SearchClient
from azure.search.documents.models import QueryType
from azure.core.credentials import AzureKeyCredential
from enhanced_rag.utils.error_handler import with_retry

from ..core.interfaces import Retriever
from ..core.models import SearchQuery, SearchResult, SearchIntent, CodeContext
from ..core.config import get_config, Config
from .hybrid_searcher import HybridSearcher
from .dependency_resolver import DependencyResolver
from ..pattern_registry import get_pattern_registry
from ..ranking.filter_manager import FilterManager

logger = logging.getLogger(__name__)


class SearchStage(Enum):
    VECTOR = "vector"
    KEYWORD = "keyword"
    SEMANTIC = "semantic"
    PATTERN = "pattern"
    DEPENDENCY = "dependency"


class MultiStageRetriever(Retriever):
    """
    Orchestrates multiple search strategies in parallel and fuses results
    """

    def __init__(self, config: Optional[Config | Dict[str, Any]] = None):
        # Normalize incoming config so self.config is always a Config instance
        cfg: Config
        if config is None:
            cfg = get_config()
        elif isinstance(config, Config):
            cfg = config
        elif isinstance(config, dict):
            try:
                cfg = Config(**config)
            except Exception as e:
                logger.warning("Invalid config dict passed to MultiStageRetriever; falling back to get_config(): %s", e)
                cfg = get_config()
        else:
            # Unknown type; fall back to environment-based config
            cfg = get_config()

        self.config: Config = cfg

        self.search_clients = self._initialize_clients()
        self.hybrid_searcher = HybridSearcher(self.config.model_dump())
        self.dependency_resolver = DependencyResolver(self.config.model_dump())
        self.pattern_registry = get_pattern_registry()
        self._cache = {}
        # Stage-level metadata captured during retrieval to preserve highlights and original scores
        self._candidate_metadata: Dict[str, Dict[str, Any]] = {}
        # Per-call warnings to surface config mismatches or fallbacks to clients
        self._warnings: List[str] = []

    def _initialize_clients(self) -> Dict[str, SearchClient]:
        """Initialize search clients for different indexes"""
        clients: Dict[str, SearchClient] = {}

        try:
            endpoint = self.config.azure.endpoint
            admin_key = self.config.azure.admin_key

            if not endpoint or not admin_key:
                logger.warning("Azure Search credentials not configured")
                return clients

            credential = AzureKeyCredential(admin_key)
        except Exception as e:
            logger.warning("Failed to get Azure Search configuration: %s", e)
            return clients

        main_index_name: str = self.config.azure.index_name or "codebase-mcp-sota"

        index_names = {
            "main": main_index_name,
            "patterns": "codebase-patterns",
            "dependencies": "codebase-dependencies",
        }

        for key, index_name in index_names.items():
            try:
                clients[key] = SearchClient(
                    endpoint=endpoint,
                    index_name=index_name,
                    credential=credential,
                    api_version="2024-07-01",
                )
            except Exception as e:
                logger.warning(
                    "Failed to initialize client for %s: %s",
                    index_name,
                    e,
                    extra={
                        "endpoint_host": (endpoint or "").split("://")[-1],
                        "index_name": index_name,
                        "component": "enhanced_rag.retrieval.multi_stage_pipeline",
                    },
                )

        return clients

    async def retrieve(
        self,
        query: SearchQuery,
        stages: Optional[List[SearchStage]] = None,
        *,
        token_budget_ctx: int = 3500,
        deadline_ms: Optional[int] = None,
    ) -> List[SearchResult]:
        """
        Execute multi-stage retrieval pipeline
        """
        # Reset per-call candidate metadata store and warnings
        self._candidate_metadata = {}
        self._warnings = []
        # Fast path: BM25-only (keyword) – preserve BM25 scores from Azure
        if getattr(query, "bm25_only", False):
            try:
                logger.info("Using BM25-only retrieval path")
                pairs = await self._execute_keyword_search(query)  # List[Tuple[id, score]]
                max_k = getattr(query, "top_k", 20)
                final_results: List[SearchResult] = []
                for doc_id, score in pairs[:max_k]:
                    result = await self._fetch_document(doc_id)
                    if result:
                        result.score = score  # Keep original BM25 score
                        final_results.append(result)
                return final_results
            except Exception as bm25_err:
                logger.error(f"BM25-only retrieval failed, falling back to normal: {bm25_err}")
                # Fall through to normal pipeline

        if stages is None:
            stages = self._select_stages_by_intent(
                query.intent or SearchIntent.IMPLEMENT
            )

        # Execute stages in parallel with timeouts
        stage_tasks = []
        stage_timeout = 5.0  # 5 seconds per stage

        for stage in stages:
            # Wrap each stage execution with a timeout
            stage_task = asyncio.create_task(
                asyncio.wait_for(
                    self._execute_stage(stage, query),
                    timeout=stage_timeout
                )
            )
            stage_tasks.append(stage_task)

        # Gather with return_exceptions to handle failures gracefully
        stage_results_raw = await asyncio.gather(*stage_tasks, return_exceptions=True)

        # Filter out failed stages and log warnings
        stage_results = []
        for idx, result in enumerate(stage_results_raw):
            if isinstance(result, Exception):
                stage_name = stages[idx] if idx < len(stages) else f"stage_{idx}"
                if isinstance(result, asyncio.TimeoutError):
                    logger.warning(f"Stage {stage_name} timed out after {stage_timeout}s")
                else:
                    logger.warning(f"Stage {stage_name} failed: {result}")
                # Add empty result for failed stage
                stage_results.append([])
            else:
                stage_results.append(result)

        # Fuse results using Reciprocal Rank Fusion (RRF)

        # Budget-pruning: trim candidate pool to fit context tokens
        # Count total documents across all stages, not number of stages
        total_docs = sum(len(stage_result) for stage_result in stage_results)
        approx_tokens_per_doc = 200

        if token_budget_ctx and total_docs * approx_tokens_per_doc > token_budget_ctx:
            # Calculate max docs we can keep
            max_docs = int(token_budget_ctx / approx_tokens_per_doc)

            # Trim each stage proportionally
            trimmed_stage_results = []
            for stage_result in stage_results:
                if max_docs <= 0:
                    break
                # Keep proportional number of docs from each stage
                stage_proportion = len(stage_result) / total_docs if total_docs > 0 else 0
                stage_max = max(1, int(max_docs * stage_proportion))
                trimmed_stage_results.append(stage_result[:stage_max])
                max_docs -= len(trimmed_stage_results[-1])

            stage_results = trimmed_stage_results

        fused_results = await self._fuse_results(stage_results, query)

        return fused_results

    def _select_stages_by_intent(self, intent: SearchIntent) -> List[SearchStage]:
        """Select appropriate search stages based on intent"""
        intent_stages = {
            SearchIntent.IMPLEMENT: [SearchStage.VECTOR, SearchStage.KEYWORD],  # Removed PATTERN as it returns fake IDs
            SearchIntent.DEBUG: [SearchStage.KEYWORD, SearchStage.VECTOR],  # Removed SEMANTIC due to missing scoring profile
            SearchIntent.UNDERSTAND: [SearchStage.KEYWORD, SearchStage.VECTOR],  # Simplified to working stages
            SearchIntent.REFACTOR: [SearchStage.KEYWORD, SearchStage.VECTOR],  # Simplified to working stages
            SearchIntent.TEST: [SearchStage.KEYWORD, SearchStage.VECTOR],  # Simplified to working stages
            SearchIntent.DOCUMENT: [SearchStage.SEMANTIC, SearchStage.KEYWORD]
        }
        return intent_stages.get(intent, [SearchStage.VECTOR, SearchStage.KEYWORD])

    async def _execute_stage(
        self,
        stage: SearchStage,
        query: SearchQuery
    ) -> List[Tuple[str, float]]:
        """Execute a single search stage"""
        try:
            if stage == SearchStage.VECTOR:
                return await self._execute_vector_search(query)
            elif stage == SearchStage.KEYWORD:
                return await self._execute_keyword_search(query)
            elif stage == SearchStage.SEMANTIC:
                return await self._execute_semantic_search(query)
            elif stage == SearchStage.PATTERN:
                return await self._execute_pattern_search(query)
            elif stage == SearchStage.DEPENDENCY:
                return await self._execute_dependency_search(query)
            else:
                logger.warning(f"Unknown search stage: {stage}")
                return []
        except Exception as e:
            logger.error(f"Error executing {stage} stage: {e}")
            return []

    async def _execute_vector_search(self, query: SearchQuery) -> List[Tuple[str, float]]:
        """Execute vector similarity search"""
        results = await self.hybrid_searcher.vector_search(
            query.query,
            filter_expr=self._build_filter(query),
            top_k=50
        )
        # Preserve vector scores and any metadata provided by HybridSearcher
        for r in results or []:
            meta = self._candidate_metadata.setdefault(r.id, {})
            meta['vector_score'] = r.score
            # Fill in content and basic metadata if not already captured
            if 'content' not in meta and getattr(r, 'content', None):
                meta['content'] = r.content
            md = getattr(r, 'metadata', {}) or {}
            for key in ('file_path', 'repository', 'language', 'function_name', 'class_name', 'start_line', 'end_line', 'highlights'):
                if key in md and md[key] is not None and key not in meta:
                    meta[key] = md[key]
        return [(r.id, r.score) for r in results]

    async def _execute_keyword_search(self, query: SearchQuery) -> List[Tuple[str, float]]:
        """Execute keyword-based search"""
        if 'main' not in self.search_clients:
            return []

        # Use enhanced queries if available, otherwise fall back to original
        queries_to_search = query.queries if query.queries else [query.query]

        def _do_keyword(search_text):
            return with_retry(op_name="acs.keyword")(self.search_clients["main"].search)(
                search_text=search_text,
                query_type=QueryType.SIMPLE,
                filter=self._build_filter(query),
                include_total_count=True,
                top=50,
                search_fields=["content", "function_name", "class_name", "docstring"],
            )

        # Execute searches for all query variants and merge results
        all_docs = []
        seen_ids = set()

        for search_text in queries_to_search[:3]:  # Limit to first 3 variants for performance
            try:
                # Run blocking SDK call in a thread to avoid blocking the event loop
                results = await asyncio.to_thread(_do_keyword, search_text)
                # Materialize results to allow multiple passes and capture metadata
                docs = list(results)

                # Merge unique results
                for doc in docs:
                    doc_id = doc.get('id')
                    if doc_id and doc_id not in seen_ids:
                        all_docs.append(doc)
                        seen_ids.add(doc_id)
            except Exception as e:
                logger.warning(f"Failed to search with query variant '{search_text}': {e}")

        docs = all_docs

        # Capture original BM25 score and any snippet/highlights for later enrichment
        for r in docs:
            try:
                doc_id = r['id']
            except Exception:
                # Skip entries without an id
                continue
            meta = self._candidate_metadata.setdefault(doc_id, {})
            # Preserve original keyword/BM25 score
            try:
                meta['bm25_score'] = r.get('@search.score')  # type: ignore[attr-defined]
            except Exception:
                # Best-effort: Azure SDK may expose as attribute-less mapping
                try:
                    meta['bm25_score'] = r['@search.score']
                except Exception:
                    pass
            # Preserve content and metadata if present
            for key in ('content', 'file_path', 'repository', 'language',
                        'function_name', 'class_name', 'start_line', 'end_line'):
                try:
                    val = r.get(key)
                except Exception:
                    try:
                        val = r[key]
                    except Exception:
                        val = None
                if val is not None and key not in meta:
                    meta[key] = val
            # Preserve highlights if available
            try:
                hl = r.get('@search.highlights')  # type: ignore[attr-defined]
            except Exception:
                try:
                    hl = r['@search.highlights']
                except Exception:
                    hl = None
            if hl:
                meta['highlights'] = hl
            else:
                # Fallback: synthesize a simple snippet when highlights are missing
                try:
                    content = r.get('content') or ""
                except Exception:
                    try:
                        content = r['content']
                    except Exception:
                        content = ""
                snippet = (content or "")[:120]
                if snippet:
                    meta['highlights'] = {"content": [snippet]}

        return [(r['id'], r['@search.score']) for r in docs]

    async def _execute_semantic_search(self, query: SearchQuery) -> List[Tuple[str, float]]:
        """Execute semantic search with query understanding"""
        if 'main' not in self.search_clients:
            return []

        # Enrich semantic search with facets, captions/answers, highlights, total count, search_fields and retries
        def _do_semantic():
            # Get semantic config from config (prefer azure.semantic_config_name)
            sem_cfg = (
                getattr(getattr(self.config, "azure", object()), "semantic_config_name", None)
                or getattr(self.config, "semantic_config_name", None)
                or "semantic-config"
            )

            return with_retry(op_name="acs.semantic")(self.search_clients["main"].search)(
                search_text=query.query,
                query_type=QueryType.SEMANTIC,
                semantic_configuration_name=sem_cfg,  # Use config value
                # scoring_profile="code_quality_boost",  # Commented out - profile doesn't exist
                filter=self._build_filter(query),
                facets=["language,count:20", "repository,count:20", "tags,count:20"],
                query_caption="extractive",
                query_answer="extractive",
                highlight_fields="content,docstring",
                include_total_count=True,
                top=50,
                search_fields=["content", "function_name", "class_name", "docstring"],
            )

        try:
            results = await asyncio.to_thread(_do_semantic)
            docs = list(results)
        except Exception as e:
            # Fallback: semantic configuration missing or disabled – degrade to SIMPLE query
            self._warnings.append("semantic_search_fallback_simple")
            logger.warning(f"Semantic search unavailable, falling back to keyword SIMPLE: {e}")

            def _do_simple():
                return with_retry(op_name="acs.semantic.fallback")(self.search_clients["main"].search)(
                    search_text=query.query,
                    query_type=QueryType.SIMPLE,
                    filter=self._build_filter(query),
                    include_total_count=True,
                    top=50,
                    search_fields=["content", "function_name", "class_name", "docstring"],
                    highlight_fields="content,docstring",
                )

            results = await asyncio.to_thread(_do_simple)
            docs = list(results)

        # Capture semantic reranker score, content, and highlights for enrichment
        for r in docs:
            try:
                doc_id = r['id']
            except Exception:
                continue
            meta = self._candidate_metadata.setdefault(doc_id, {})

            # Prefer reranker score; fall back to @search.score
            sem_score = None
            try:
                sem_score = r.get('@search.rerankerScore')  # type: ignore[attr-defined]
            except Exception:
                try:
                    sem_score = r['@search.rerankerScore']
                except Exception:
                    try:
                        sem_score = r.get('@search.score')  # type: ignore[attr-defined]
                    except Exception:
                        try:
                            sem_score = r['@search.score']
                        except Exception:
                            sem_score = None
            if sem_score is not None and 'semantic_score' not in meta:
                meta['semantic_score'] = sem_score

            # Preserve content and core metadata
            for key in ('content', 'file_path', 'repository', 'language',
                        'function_name', 'class_name', 'start_line', 'end_line'):
                try:
                    val = r.get(key)  # type: ignore[attr-defined]
                except Exception:
                    try:
                        val = r[key]
                    except Exception:
                        val = None
                if val is not None and key not in meta:
                    meta[key] = val

            # Preserve highlights if available
            hl = None
            try:
                hl = r.get('@search.highlights')  # type: ignore[attr-defined]
            except Exception:
                try:
                    hl = r['@search.highlights']
                except Exception:
                    hl = None
            if hl and 'highlights' not in meta:
                meta['highlights'] = hl
            elif 'highlights' not in meta:
                # Fallback: synthesize snippet when highlights are missing
                try:
                    content = r.get('content')  # type: ignore[attr-defined]
                except Exception:
                    try:
                        content = r['content']
                    except Exception:
                        content = None
                snippet = (content or "")[:120]
                if snippet:
                    meta['highlights'] = {"content": [snippet]}

        return [(r['id'], r['@search.score']) for r in docs]

    async def _execute_pattern_search(self, query: SearchQuery) -> List[Tuple[str, float]]:
        """Execute architectural pattern search"""
        patterns = self.pattern_registry.recognize_patterns(
            query.query,
            context={'task_context': query.task_context}
        )
        # Convert patterns to file_id, confidence pairs
        # For now, use pattern type + name as file_id (simplified)
        return [(f"{p.pattern_type.value}_{p.pattern_name}", p.confidence) for p in patterns]

    async def _execute_dependency_search(self, query: SearchQuery) -> List[Tuple[str, float]]:
        """Execute dependency-aware search"""
        deps = await self.dependency_resolver.resolve_dependencies(
            query.query,
            current_file=query.current_file
        )
        return [(d.file_id, d.relevance_score) for d in deps]

    def _build_filter(self, query: SearchQuery) -> Optional[str]:
        """Build Azure Search filter expression using FilterManager"""
        # Use FilterManager for safe, consistent filter building
        filters = []

        # Repository filter
        repo_filter = FilterManager.repository(getattr(query, "repository", None))
        if repo_filter:
            filters.append(repo_filter)

        # Language filter
        lang_filter = FilterManager.language(query.language)
        if lang_filter:
            filters.append(lang_filter)

        # Framework filter
        framework_filter = FilterManager.framework(query.framework)
        if framework_filter:
            filters.append(framework_filter)

        # Exclusion filters
        exclude_filter = FilterManager.exclude_terms(getattr(query, "exclude_terms", []))
        if exclude_filter:
            filters.append(exclude_filter)

        # Exact term filters
        exact_filter = FilterManager.exact_terms(getattr(query, "exact_terms", []))
        if exact_filter:
            filters.append(exact_filter)

        return FilterManager.combine_and(*filters)

    async def _fuse_results(
        self,
        stage_results: List[List[Tuple[str, float]]],
        query: SearchQuery
    ) -> List[SearchResult]:
        """Fuse results from multiple stages using stage-aware RRF with weighted scoring"""
        # RRF implementation with stage weights
        k = 60  # RRF constant
        doc_scores = {}
        doc_stage_scores = {}  # Track best score per stage for hybrid scoring

        # Define stage weights based on quality/relevance
        # These weights can be adjusted based on intent or learned from feedback
        stage_weights = {
            0: 1.0,   # First stage (e.g., vector) - high weight
            1: 0.8,   # Second stage (e.g., keyword) - medium-high weight
            2: 0.6,   # Third stage (e.g., semantic) - medium weight
            3: 0.4,   # Fourth stage (e.g., pattern) - lower weight
            4: 0.3,   # Fifth stage (e.g., dependency) - lowest weight
        }

        for stage_idx, results in enumerate(stage_results):
            stage_weight = stage_weights.get(stage_idx, 0.5)

            # Normalize scores within each stage for hybrid scoring
            max_score = max((score for _, score in results), default=1.0)

            for rank, (doc_id, score) in enumerate(results):
                if doc_id not in doc_scores:
                    doc_scores[doc_id] = 0
                    doc_stage_scores[doc_id] = {}

                # Weighted RRF formula: weight * 1/(k+rank)
                rrf_score = stage_weight * (1 / (k + rank + 1))

                # Hybrid scoring: combine RRF with normalized original score
                normalized_score = score / max_score if max_score > 0 else 0
                hybrid_score = 0.7 * rrf_score + 0.3 * stage_weight * normalized_score

                doc_scores[doc_id] += hybrid_score
                doc_stage_scores[doc_id][f'stage_{stage_idx}_score'] = score

        # Sort by fused score
        sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)

        # Convert to SearchResult objects
        final_results = []
        top_k = getattr(query, 'top_k', 20)

        for doc_id, fused_score in sorted_docs[:top_k]:
            # Fetch full document details
            result = await self._fetch_document(doc_id)
            if result:
                # Attach fused score
                result.score = fused_score

                # Enrich with stage-captured metadata (content, highlights, original scores)
                meta = self._candidate_metadata.get(doc_id, {})

                # Preserve original BM25 / semantic / vector scores for downstream use and display
                if 'bm25_score' in meta:
                    try:
                        setattr(result, 'bm25_score', float(meta['bm25_score']))
                    except Exception:
                        setattr(result, 'bm25_score', meta['bm25_score'])
                if 'semantic_score' in meta:
                    try:
                        setattr(result, 'semantic_score', float(meta['semantic_score']))
                    except Exception:
                        setattr(result, 'semantic_score', meta['semantic_score'])
                if 'vector_score' in meta:
                    try:
                        setattr(result, 'vector_score', float(meta['vector_score']))
                    except Exception:
                        setattr(result, 'vector_score', meta['vector_score'])

                # Original search score used for tie-breaking in ranker
                # Prioritize: bm25_score > semantic_score > vector_score > fused_score
                orig = (meta.get('bm25_score') or
                       meta.get('semantic_score') or
                       meta.get('vector_score') or
                       getattr(result, '_original_score', None) or
                       fused_score)
                if orig is not None:
                    try:
                        setattr(result, '_original_score', float(orig))
                    except Exception:
                        setattr(result, '_original_score', orig)

                # Fill missing fields from metadata to fix "No content" and missing context
                if (not getattr(result, 'code_snippet', None)) and meta.get('content'):
                    result.code_snippet = meta['content']  # type: ignore[attr-defined]
                if meta.get('highlights'):
                    result.highlights = meta.get('highlights')  # type: ignore[attr-defined]
                for key in ('file_path', 'repository', 'language', 'function_name', 'class_name', 'start_line', 'end_line'):
                    if getattr(result, key, None) in (None, "", []):
                        if key in meta and meta[key] is not None:
                            setattr(result, key, meta[key])

                # Drop entries with no usable content to avoid blank snippets downstream
                text_content = getattr(result, 'code_snippet', None) or getattr(result, 'content', None) or ""
                if isinstance(text_content, str) and text_content.strip():
                    final_results.append(result)
                else:
                    logger.debug(f"Skipping empty-content document id={doc_id}")

        # Assemble bounded context with dedup and citations
        try:
            context_text, citations = self._assemble_context(
                final_results,
                max_context_tokens=getattr(query, "max_context_tokens", 3000),
                safety_margin=getattr(query, "context_safety_margin", 200),
                tokenizer=getattr(query, "tokenizer", None),
            )
            # Attach assembled context and citations to results metadata if model supports it
            for r in final_results:
                if not hasattr(r, "citations"):
                    setattr(r, "citations", [])
            # Store on retriever for downstream generation stage if needed
            self._last_context_text = context_text
            self._last_citations = citations
        except Exception as assemble_err:
            logger.warning(f"Context assembly failed: {assemble_err}")

        return final_results

    async def search(
        self,
        queries: List[str],
        context: Optional[CodeContext] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """Execute multi-stage retrieval pipeline (interface implementation)"""
        # Convert to SearchQuery format and use retrieve method
        if not queries:
            return []

        # Use the first query as primary, combine others
        primary_query = queries[0]
        combined_query = " ".join(queries) if len(queries) > 1 else primary_query

        # Create SearchQuery object
        search_query = SearchQuery(
            query=combined_query,
            current_file=context.current_file if context else None,
            language=context.language if context else None,
            framework=context.framework if context else None,
            user_id=context.session_id if context else None
        )

        return await self.retrieve(search_query)

    def _assemble_context(
        self,
        results: List[SearchResult],
        max_context_tokens: int = 3000,
        safety_margin: int = 200,
        tokenizer=None,
    ) -> tuple[str, List[dict]]:
        """
        Assemble deduplicated, token-bounded context from ranked results.
        - Deduplicate by doc id and normalized content hash
        - Sort by fused score (already applied) and accumulate within budget
        - Return context text and citations with file_path and line ranges
        """
        def norm_text(t: str) -> str:
            return " ".join((t or "").split()).lower()

        def approx_tokens(t: str) -> int:
            # fallback heuristic: ~4 chars per token
            return max(1, len(t) // 4)

        seen_ids = set()
        seen_hashes = set()
        unique: List[SearchResult] = []

        for r in results or []:
            doc_id = getattr(r, "id", None)
            text = getattr(r, "code_snippet", None) or getattr(r, "content", None) or ""
            h = hash(norm_text(text))
            if (doc_id and doc_id in seen_ids) or h in seen_hashes:
                continue
            if doc_id:
                seen_ids.add(doc_id)
            seen_hashes.add(h)
            unique.append(r)

        # unique list is already in fused order due to earlier sorting/slicing
        budget = max(1, max_context_tokens - max(0, safety_margin))
        used = 0
        parts: List[str] = []
        citations: List[dict] = []

        for r in unique:
            text = getattr(r, "code_snippet", None) or getattr(r, "content", None) or ""
            if tokenizer:
                try:
                    est_tokens = len(tokenizer.encode(text))
                except Exception:
                    est_tokens = approx_tokens(text)
            else:
                est_tokens = approx_tokens(text)
            if used + est_tokens > budget:
                break
            parts.append(text)
            used += est_tokens
            citations.append(
                {
                    "id": getattr(r, "id", None),
                    "file_path": getattr(r, "file_path", None),
                    "range": (
                        f"{getattr(r, 'start_line', None)}-"
                        f"{getattr(r, 'end_line', None)}"
                    ),
                    "score": getattr(r, "score", None),
                }
            )

        return ("\n\n".join(parts), citations)

    async def get_dependencies(
        self,
        code_chunk: str,
        language: str
    ) -> List[SearchResult]:
        """Resolve code dependencies (interface implementation)"""
        try:
            # Use dependency resolver to find dependencies
            deps = await self.dependency_resolver.resolve_dependencies(
                code_chunk,
                current_file=None  # No specific file context
            )

            # Convert dependencies to SearchResult objects
            results = []
            for dep in deps:
                # Fetch full document details for each dependency
                result = await self._fetch_document(dep.file_id)
                if result:
                    result.score = dep.relevance_score
                    results.append(result)

            return results

        except Exception as e:
            logger.error(f"Error resolving dependencies: {e}")
            return []

    async def _fetch_document(self, doc_id: str) -> Optional[SearchResult]:
        """Fetch full document details from Azure Search"""
        try:
            if 'main' not in self.search_clients:
                return None

            # Try to get from cache first
            if doc_id in self._cache:
                return self._cache[doc_id]

            # Fetch from Azure Search
            def _do_get():
                return with_retry(op_name="acs.get_document")(self.search_clients['main'].get_document)(key=doc_id)

            # Offload blocking get_document to thread pool
            doc = await asyncio.to_thread(_do_get)

            # Convert to SearchResult
            result = SearchResult(
                id=doc_id,
                score=0.0,  # Will be updated by caller
                file_path=doc.get('file_path', ''),
                repository=doc.get('repository', ''),
                function_name=doc.get('function_name'),
                class_name=doc.get('class_name'),
                code_snippet=doc.get('content', ''),
                language=doc.get('language', ''),
                start_line=doc.get('start_line'),
                end_line=doc.get('end_line'),
                dependencies=doc.get('imports', []),
                tags=doc.get('tags', []),
                complexity_score=doc.get('complexity_score'),
                test_coverage=doc.get('test_coverage'),
                last_modified=doc.get('last_modified')
            )

            # Cache the result
            self._cache[doc_id] = result

            return result

        except Exception as e:
            logger.error(f"Error fetching document {doc_id}: {e}")
            return None
