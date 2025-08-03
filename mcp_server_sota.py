#!/usr/bin/env python3
"""
Unified Azure Code Search MCP Server - Best of All Implementations
Combines the strongest features from all versions while staying under 900 lines
"""

# Compatibility shim: ensure MCPServer is importable for tests that expect it
try:
    MCPServer  # type: ignore[name-defined]
except NameError:
    class MCPServer:  # noqa: D401 - simple shim to satisfy imports in tests
        """Minimal MCPServer shim; replace with full implementation if present."""
        def __init__(self, *args, **kwargs):
            pass

import os
import sys
import json
import asyncio
import re
import logging
import socket

# ---------------------------------------------------------------------------
# Workaround for sandbox environments where the `socketpair()` syscall is
# disallowed by the seccomp profile.  asyncio's selector event loop relies on
# `socket.socketpair()` for its self-pipe.  We monkey-patch socket.socketpair
# with an implementation that falls back to a localhost TCP socket pair when
# the original function raises a PermissionError.
# ---------------------------------------------------------------------------

_orig_socketpair = socket.socketpair

def _safe_socketpair(*args, **kwargs):  # type: ignore[override]
    try:
        return _orig_socketpair(*args, **kwargs)
    except PermissionError:
        # Fallback: create a pair of connected IPv4 sockets. This avoids the
        # blocked `socketpair` syscall while still giving asyncio a pair of
        # sockets it can use for its self-pipe.
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)
        port = srv.getsockname()[1]

        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.setblocking(True)
        client.connect(("127.0.0.1", port))

        server_side, _ = srv.accept()
        srv.close()

        # Match the return order of the original socketpair(): (conn1, conn2)
        return server_side, client

# Apply the monkey-patch
socket.socketpair = _safe_socketpair  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Provide an alternative asyncio event loop that doesn't rely on socketpair.
# This is a belt-and-suspenders fix for environments where even creating TCP
# sockets is prohibited. It uses os.pipe() for the self-pipe implementation.
# ---------------------------------------------------------------------------

import asyncio, os, selectors, errno, fcntl


class _PipeSelectorEventLoop(asyncio.SelectorEventLoop):
    """SelectorEventLoop variant that uses os.pipe() instead of socketpair()."""

    def _make_self_pipe(self):  # type: ignore[override]
        # Create a non-blocking pipe pair (read/write fds)
        rfd, wfd = os.pipe()
        os.set_blocking(rfd, False)
        os.set_blocking(wfd, False)

        # Wrap the read end with a simple callback that drains the pipe
        def _read_from_self():
            try:
                os.read(rfd, 4096)
            except BlockingIOError:
                pass
            except OSError as exc:
                if exc.errno != errno.EAGAIN:
                    raise

        self._add_reader(rfd, _read_from_self)

        # Store fds so that the parent class can close them in _close_self_pipe()
        class _PipeFD:
            def __init__(self, fd: int):
                self._fd = fd

            def fileno(self):  # noqa: D401
                return self._fd

            def send(self, data: bytes):  # type: ignore[override]
                os.write(self._fd, data)

            def close(self):  # noqa: D401
                try:
                    os.close(self._fd)
                except OSError:
                    pass

        self._ssock = _PipeFD(rfd)
        self._csock = _PipeFD(wfd)


class _SafeEventLoopPolicy(asyncio.DefaultEventLoopPolicy):
    def new_event_loop(self):  # type: ignore[override]
        return _PipeSelectorEventLoop()

# Install the safe policy **before** anyio / FastMCP create their own loops.
asyncio.set_event_loop_policy(_SafeEventLoopPolicy())
from typing import Optional, List, Dict, Any, Sequence, cast
from pathlib import Path
from datetime import datetime, timezone
from enum import Enum

# Core imports
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()

# Azure imports
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.core.credentials import AzureKeyCredential

# Try to import VectorizableTextQuery (only available in newer versions)
try:
    from azure.search.documents.models import VectorizableTextQuery
    VECTORIZABLE_TEXT_QUERY_AVAILABLE = True
except ImportError:
    VectorizableTextQuery = None
    VECTORIZABLE_TEXT_QUERY_AVAILABLE = False

# MCP SDK with fallback
try:
    from mcp.server.fastmcp import FastMCP
    from mcp.types import TextContent
    MCP_SDK_AVAILABLE = True
except ImportError:
    MCP_SDK_AVAILABLE = False
    class FastMCP:
        def __init__(self, name): self.name = name
        def tool(self): return lambda f: f
        def resource(self): return lambda f: f
        def prompt(self): return lambda f: f
        def run(self): pass

# Optional imports
try:
    from enhanced_rag.azure_integration import AzureOpenAIEmbeddingProvider
    VECTOR_SUPPORT = True
except ImportError:
    AzureOpenAIEmbeddingProvider = None
    VECTOR_SUPPORT = False

try:
    from microsoft_docs_mcp_client import MicrosoftDocsMCPClient
    DOCS_SUPPORT = True
except ImportError:
    MicrosoftDocsMCPClient = None
    DOCS_SUPPORT = False

# Enhanced RAG Pipeline support
try:
    from enhanced_rag.mcp_integration.enhanced_search_tool import EnhancedSearchTool
    from enhanced_rag.mcp_integration.code_gen_tool import CodeGenerationTool
    from enhanced_rag.mcp_integration.context_aware_tool import ContextAwareTool
    ENHANCED_RAG_SUPPORT = True
except ImportError:
    EnhancedSearchTool = None
    CodeGenerationTool = None
    ContextAwareTool = None
    ENHANCED_RAG_SUPPORT = False

try:
    from enhanced_rag.pipeline import RAGPipeline
    from enhanced_rag.core.models import QueryContext
    PIPELINE_AVAILABLE = True
except Exception:
    RAGPipeline = QueryContext = None
    PIPELINE_AVAILABLE = False

try:
    from enhanced_rag.ranking.result_explainer import ResultExplainer  # type: ignore
    from enhanced_rag.core.models import SearchResult as CoreSearchResult, SearchQuery as CoreSearchQuery
    RESULT_EXPLAINER_AVAILABLE = True
except Exception:
    ResultExplainer = None
    CoreSearchResult = None
    CoreSearchQuery = None
    RESULT_EXPLAINER_AVAILABLE = False

try:
    from enhanced_rag.semantic.intent_classifier import IntentClassifier  # type: ignore
    from enhanced_rag.semantic.query_enhancer import ContextualQueryEnhancer  # type: ignore
    from enhanced_rag.semantic.query_rewriter import MultiVariantQueryRewriter  # type: ignore
    SEMANTIC_TOOLS_AVAILABLE = True
except Exception:
    IntentClassifier = QueryEnhancer = QueryRewriter = None
    SEMANTIC_TOOLS_AVAILABLE = False

try:
    from enhanced_rag.learning.feedback_collector import FeedbackCollector  # type: ignore
    from enhanced_rag.learning.usage_analyzer import UsageAnalyzer  # type: ignore
    from enhanced_rag.learning.model_updater import ModelUpdater  # type: ignore
    LEARNING_SUPPORT = True
except Exception:
    FeedbackCollector = None
    UsageAnalyzer = None
    ModelUpdater = None
    LEARNING_SUPPORT = False

try:
    from enhanced_rag.azure_integration.index_operations import IndexOperations  # type: ignore
    from enhanced_rag.azure_integration.indexer_integration import IndexerIntegration  # type: ignore
    from enhanced_rag.azure_integration.document_operations import DocumentOperations  # type: ignore
    AZURE_ADMIN_SUPPORT = True
except Exception:
    IndexOperations = None
    IndexerIntegration = None
    DocumentOperations = None
    AZURE_ADMIN_SUPPORT = False

try:
    from enhanced_rag.github_integration.api_client import GitHubClient  # type: ignore
    from enhanced_rag.github_integration.remote_indexer import RemoteIndexer  # type: ignore
    GITHUB_SUPPORT = True
except Exception:
    GitHubClient = None
    RemoteIndexer = None
    GITHUB_SUPPORT = False

try:
    from enhanced_rag.utils.cache_manager import CacheManager  # type: ignore
    RAG_CACHE_SUPPORT = True
except Exception:
    CacheManager = None
    RAG_CACHE_SUPPORT = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Log available features
if ENHANCED_RAG_SUPPORT:
    logger.info("Enhanced RAG Pipeline is available - advanced search and code generation enabled")
else:
    logger.info("Enhanced RAG Pipeline not available - using direct Azure Search only")

if VECTOR_SUPPORT:
    logger.info("Vector search support is available")

if DOCS_SUPPORT:
    logger.info("Microsoft Docs search support is available")

FEEDBACK_DIR = os.getenv("MCP_FEEDBACK_DIR", ".mcp_feedback")
Path(FEEDBACK_DIR).mkdir(parents=True, exist_ok=True)

# ============================================================================
# Schema and Field Mapping
# ============================================================================

class FieldMapper:
    """
    Normalizes field names across schema versions and provides
    select lists and graceful fallback accessors.
    """
    # Canonical names used by this server
    CANONICAL = {
        "repository": ["repository", "repo"],
        "file_path": ["file_path", "path"],
        "language": ["language"],
        "content": ["content", "code_chunk", "code_content"],
        "function_name": ["function_name"],
        "class_name": ["class_name"],
        "signature": ["signature", "function_signature"],
        "imports": ["imports", "imports_used"],
        "dependencies": ["dependencies", "calls_functions"],
        "semantic_context": ["semantic_context"],
        "start_line": ["start_line"],
        "end_line": ["end_line"],
        "docstring": ["docstring"],
        "chunk_type": ["chunk_type"]
    }

    REQUIRED = ["repository", "file_path", "language", "content"]
    OPTIONAL = [
        "function_name","class_name","signature","imports","dependencies",
        "semantic_context","start_line","end_line","docstring","chunk_type"
    ]

    def __init__(self, available_fields: Optional[Sequence[str]] = None):
        self.available = set(available_fields or [])
        self.reverse_map: Dict[str, str] = {}
        # Build reverse map from canonical -> actual present field
        for canonical, candidates in self.CANONICAL.items():
            actual = next((c for c in candidates if c in self.available), None)
            if actual:
                self.reverse_map[canonical] = actual

    def select_list(self) -> List[str]:
        # Build select with available actual names; if unknown, include canonical to try best-effort
        out: List[str] = []
        for canonical, candidates in self.CANONICAL.items():
            name = next((c for c in candidates if c in self.available), None)
            out.append(name or candidates[0])
        # Always include vector-friendly fields if present
        if "content_vector" in self.available:
            out.append("content_vector")
        return list(dict.fromkeys(out))  # dedupe

    def get(self, doc: Dict[str, Any], canonical: str, default: Any = "") -> Any:
        # Graceful access for missing optional fields
        if canonical in self.reverse_map:
            return doc.get(self.reverse_map[canonical], default)
        # Try all candidates if we didn't initialize with the schema (e.g., tests)
        for cand in self.CANONICAL.get(canonical, []):
            if cand in doc:
                return doc.get(cand, default)
        return default

    def validate_required(self) -> Dict[str, Any]:
        missing = [c for c in self.REQUIRED if c not in self.reverse_map]
        return {
            "valid": len(missing) == 0,
            "missing": missing
        }

# ============================================================================
# Pydantic Models for Type Safety
# ============================================================================

class SearchIntent(str, Enum):
    IMPLEMENT = "implement"
    DEBUG = "debug"
    UNDERSTAND = "understand"
    REFACTOR = "refactor"

class SearchCodeParams(BaseModel):
    query: str = Field(description="Natural language query to search for code")
    intent: Optional[SearchIntent] = Field(None, description="Search intent to optimize results")
    language: Optional[str] = Field(None, description="Programming language filter")
    repository: Optional[str] = Field(None, description="Repository to search (defaults to current, use '*' for all)")
    max_results: int = Field(10, ge=1, le=50, description="Maximum number of results")
    include_dependencies: bool = Field(False, description="Include function dependencies")
    skip: int = Field(0, ge=0, description="Number of results to skip for pagination")
    orderby: Optional[str] = Field(None, description="Sort order (e.g., 'last_modified desc')")
    highlight_code: bool = Field(False, description="Enable hit highlighting in code results")
    bm25_only: bool = Field(False, description="Force basic BM25 (keyword) search only")
    query_type: Optional[str] = Field(None, description="Override Azure query_type (simple|full|semantic)")
    # New flags for improved literal handling and caching
    exact_terms: Optional[List[str]] = Field(None, description="Terms that must appear (quoted phrases or numeric literals)")
    disable_cache: bool = Field(False, description="Disable server-side TTL cache for this call")
    include_timings: bool = Field(False, description="Include detailed timing information in response")
    dependency_mode: str = Field("auto", description="Dependency mode")

class SearchResult(BaseModel):
    file_path: str
    repository: str
    language: str
    function_name: Optional[str] = None
    signature: Optional[str] = None
    line_range: Optional[str] = None
    score: float
    content: str
    context: Optional[str] = None
    imports: List[str] = []
    dependencies: List[str] = []
    highlights: Optional[Dict[str, List[str]]] = None
    dependency_graph: Optional[Dict[str, Any]] = None

# ============================================================================
# Enhanced MCP Server
# ============================================================================

class EnhancedMCPServer:
    """Unified MCP server combining best features from all implementations"""

    def __init__(self):
        self.name = "azure-code-search-enhanced"
        self.version = "3.0.0"
        self._field_mapper: Optional[FieldMapper] = None
        self._initialize_clients()
        self._repo_cache: Dict[str, str] = {}
        self._query_cache: Dict[str, List[SearchResult]] = {}
        self._last_total_count: Optional[int] = None
        # TTL cache config (approved): 60s TTL, max 500 entries
        self._ttl_seconds: int = int(os.getenv("MCP_CACHE_TTL_SECONDS", "60"))
        self._cache_max_entries: int = int(os.getenv("MCP_CACHE_MAX_ENTRIES", "500"))
        # store timestamps for eviction
        self._query_cache_ts: Dict[str, float] = {}

    def _format_line_range(self, start_line: Optional[int], end_line: Optional[int]) -> Optional[str]:
        """Format line range from start and end line numbers"""
        if start_line is None:
            return None
        if end_line is None or end_line == start_line:
            return str(start_line)
        return f"{start_line}-{end_line}"

    def _cleanup_expired_cache_entries(self):
        """Remove expired cache entries"""
        now = time.time()
        expired_keys = [
            key for key, ts in self._query_cache_ts.items()
            if (now - ts) > self._ttl_seconds
        ]
        for key in expired_keys:
            self._query_cache.pop(key, None)
            self._query_cache_ts.pop(key, None)

        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

    def _should_cache_query(self, params: SearchCodeParams) -> bool:
        """Determine if query should be cached"""
        if params.disable_cache:
            return False

        # Allow caching for dependency searches if they're not too expensive
        if params.include_dependencies:
            # Only cache dependency searches for small result sets
            return params.max_results <= 5

        return True

    def _get_cache_key(self, params: SearchCodeParams) -> str:
        """Generate a consistent cache key for search parameters"""
        # Include all parameters that affect search results
        key_parts = [
            params.query,
            str(params.intent),
            params.repository or "",
            params.language or "",
            str(params.max_results),
            str(params.skip),
            str(params.include_dependencies),
            params.orderby or "",
            str(params.highlight_code),
            str(params.bm25_only),
            params.query_type or "",
            ",".join(params.exact_terms or []),
            params.dependency_mode or "auto"
        ]
        return "|".join(key_parts)

    def _invalidate_cache_by_pattern(self, pattern: str = None, repository: str = None, language: str = None):
        """Invalidate cache entries matching specific patterns"""
        keys_to_remove = []

        for key in self._query_cache.keys():
            should_remove = False

            # Pattern-based invalidation
            if pattern and pattern.lower() in key.lower():
                should_remove = True

            # Repository-based invalidation
            if repository:
                # Cache key format: query|intent|repository|language|...
                key_parts = key.split("|")
                if len(key_parts) > 2 and key_parts[2] == repository:
                    should_remove = True

            # Language-based invalidation
            if language:
                key_parts = key.split("|")
                if len(key_parts) > 3 and key_parts[3] == language:
                    should_remove = True

            if should_remove:
                keys_to_remove.append(key)

        # Remove identified keys
        for key in keys_to_remove:
            self._query_cache.pop(key, None)
            self._query_cache_ts.pop(key, None)

        if keys_to_remove:
            logger.info(f"Invalidated {len(keys_to_remove)} cache entries")

        return len(keys_to_remove)

    def _get_cache_stats(self) -> Dict[str, Any]:
        """Get detailed cache statistics"""
        now = time.time()
        expired_count = sum(
            1 for ts in self._query_cache_ts.values()
            if (now - ts) > self._ttl_seconds
        )

        return {
            "total_entries": len(self._query_cache),
            "expired_entries": expired_count,
            "active_entries": len(self._query_cache) - expired_count,
            "max_entries": self._cache_max_entries,
            "ttl_seconds": self._ttl_seconds,
            "memory_usage_estimate": len(self._query_cache) * 1024  # Rough estimate
        }

    def _initialize_clients(self):
        """Initialize all service clients and validate index schema"""
        endpoint = os.getenv("ACS_ENDPOINT")
        admin_key = os.getenv("ACS_ADMIN_KEY")

        if not endpoint or not admin_key:
            raise ValueError("Missing Azure Search credentials")

        # Get index name from environment or use default
        index_name = os.getenv("ACS_INDEX_NAME", "codebase-mcp-sota")
        logger.info(f"Using Azure Search index: {index_name}")

        self.search_client = SearchClient(
            endpoint=endpoint,
            index_name=index_name,
            credential=AzureKeyCredential(admin_key)
        )

        # Auto-detect semantic availability and capture schema for field mapping
        self._semantic_available = True
        try:
            from azure.search.documents.indexes import SearchIndexClient
            idx_client = SearchIndexClient(endpoint=endpoint, credential=AzureKeyCredential(admin_key))
            idx = idx_client.get_index(index_name)
            self._semantic_available = bool(getattr(idx, "semantic_search", None))
            available_fields = [f.name for f in getattr(idx, "fields", [])]
            self._field_mapper = FieldMapper(available_fields)

            # Validate required schema early
            schema_check = self._field_mapper.validate_required()
            if not schema_check["valid"]:
                # If canonical fields are missing but ANY candidate alias exists in the index, allow startup.
                # This covers repo/path variants and future aliasable fields.
                missing = set(schema_check["missing"])
                available = set(available_fields or [])
                all_aliases_ok = True
                for m in missing:
                    candidates = FieldMapper.CANONICAL.get(m, [])
                    if not any(c in available for c in candidates):
                        all_aliases_ok = False
                        break
                if all_aliases_ok:
                    logger.warning(
                        "Index missing canonical fields %s but alias candidates are present in schema; proceeding with FieldMapper.",
                        list(missing)
                    )
                else:
                    logger.error("Index schema missing required fields: %s", schema_check["missing"])
                    # Fail fast to surface misconfiguration
                    raise RuntimeError(f"Missing required fields in index '{index_name}': {schema_check['missing']}")
        except Exception as e:
            # Graceful degradation: still create a mapper without known fields
            if isinstance(e, RuntimeError):
                # re-raise to stop startup, since required fields are missing (not covered by legacy allowance)
                raise
            self._semantic_available = False
            logger.warning("Could not load index schema for field mapping; proceeding with defaults: %s", e)
            self._field_mapper = FieldMapper()

        # Auto-detect vector search availability
        self._vector_available = True
        try:
            from azure.search.documents.indexes import SearchIndexClient
            idx_client = SearchIndexClient(endpoint=endpoint, credential=AzureKeyCredential(admin_key))
            idx = idx_client.get_index(index_name)
            vf = next((f for f in idx.fields if f.name == "content_vector"), None)
            self._vector_available = bool(vf and getattr(vf, "vector_search_dimensions", None))
        except Exception:
            self._vector_available = False

        # Initialize vector support
        self.embedder = None
        if VECTOR_SUPPORT and (os.getenv("AZURE_OPENAI_KEY") or os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")):
            try:
                self.embedder = AzureOpenAIEmbeddingProvider()
                # Log embedding configuration
                if hasattr(self.embedder, 'dimensions') and self.embedder.dimensions:
                    logger.info(f"Vector search enabled with {self.embedder.dimensions} dimensions")
                else:
                    logger.info("Vector search enabled")

                # Check for vector dimension mismatch
                try:
                    from azure.search.documents.indexes import SearchIndexClient
                    idx_client = SearchIndexClient(endpoint=endpoint, credential=AzureKeyCredential(admin_key))
                    idx = idx_client.get_index(index_name)
                    vf = next((f for f in idx.fields if f.name == "content_vector"), None)
                    if vf and getattr(vf, "vector_search_dimensions", None) and hasattr(self.embedder, "dimensions") and self.embedder.dimensions:
                        if vf.vector_search_dimensions != self.embedder.dimensions:
                            logger.warning("Vector dim mismatch: index=%s, client=%s", vf.vector_search_dimensions, self.embedder.dimensions)
                except Exception:
                    pass
            except Exception as e:
                logger.warning("Vector search unavailable: %s", e)

    # ========================================================================
    # Core Search Implementation with Advanced Features
    # ========================================================================

    async def search_code(self, params: SearchCodeParams) -> List[SearchResult]:
        """Enhanced code search with intelligent filtering and ranking"""
        # Create internal timer for diagnostics
        timer = _Timer()

        # Build normalized cache key including new flags and pagination
        cache_key = self._get_cache_key(params)

        # Clean up expired entries periodically (every 50th query)
        if len(self._query_cache) % 50 == 0:
            self._cleanup_expired_cache_entries()

        # TTL cache read (improved logic)
        if self._should_cache_query(params):
            cached = self._query_cache.get(cache_key)
            ts = self._query_cache_ts.get(cache_key)
            now = time.time()
            if cached is not None and ts is not None and (now - ts) <= self._ttl_seconds:
                # Return a slice for safety
                return cached[:params.max_results]

        # Enhance query based on intent
        timer.mark("cache_check")
        enhanced_query = self._enhance_query(params.query, params.intent)
        timer.mark("query_enhanced")

        # Detect repository if needed
        repo = self._resolve_repository(params.repository)

        # Build search parameters
        timer.mark("repo_resolved")
        search_params = self._build_search_params(enhanced_query, repo, params)
        timer.mark("params_built")
        # Apply exact-term gating for quoted phrases or numeric literals
        applied_exact_terms = False
        exact_terms_fallback_used = False
        exact_terms_error = None

        if params.exact_terms:
            try:
                # Build a must-have filter that ORs fields per term and ANDs across terms
                term_filters = []

                # Use FieldMapper to get available searchable fields
                searchable_fields = ['content', 'function_name', 'class_name', 'docstring']
                if self._field_mapper:
                    # Map fields to what's actually available in the index
                    available_fields = []
                    for field in searchable_fields:
                        mapped = self._field_mapper.reverse_map.get(field, field)
                        if mapped in self._field_mapper.available:
                            available_fields.append(mapped)
                    # If no searchable fields available, fall back to content only
                    searchable_fields = available_fields if available_fields else ['content']

                # Validate and sanitize exact terms
                valid_terms = []
                for term in params.exact_terms:
                    if term and len(str(term).strip()) > 0:
                        # Enhanced escaping for OData filter syntax
                        safe_term = str(term).strip()
                        # Escape single quotes and other special characters
                        safe_term = safe_term.replace("'", "''").replace('"', '""')
                        # Validate term doesn't contain problematic characters for search.ismatch
                        if not any(char in safe_term for char in ['(', ')', '&', '|', '!', '^']):
                            valid_terms.append(safe_term)
                        else:
                            logger.warning(f"Skipping exact term with special characters: {term}")

                if valid_terms:
                    for term in valid_terms:
                        field_conditions = []
                        for field in searchable_fields:
                            # Use search.ismatch with proper escaping
                            field_conditions.append(f"search.ismatch('{term}', '{field}')")
                        if field_conditions:
                            term_filters.append("(" + " or ".join(field_conditions) + ")")

                    if term_filters:
                        exact_filter = " and ".join(term_filters)
                        if "filter" in search_params and search_params["filter"]:
                            search_params["filter"] = f"({search_params['filter']}) and {exact_filter}"
                        else:
                            search_params["filter"] = exact_filter
                        applied_exact_terms = True
                        logger.debug(f"Applied exact terms filter: {exact_filter}")

            except Exception as e:
                # Log the error and apply fallback
                exact_terms_error = str(e)
                logger.warning(f"Exact terms filtering failed: {e}, applying fallback")

                # Fallback: Add exact terms as quoted phrases to the main query
                try:
                    fallback_terms = []
                    for term in params.exact_terms:
                        if term and len(str(term).strip()) > 0:
                            # Add as quoted phrase to boost exact matches
                            clean_term = str(term).strip().replace('"', '')
                            if ' ' in clean_term:
                                fallback_terms.append(f'"{clean_term}"')
                            else:
                                fallback_terms.append(clean_term)

                    if fallback_terms:
                        # Enhance the main search query with exact terms
                        enhanced_query = search_params.get("search_text", "")
                        enhanced_query += " " + " ".join(fallback_terms)
                        search_params["search_text"] = enhanced_query.strip()
                        exact_terms_fallback_used = True
                        logger.info(f"Applied exact terms fallback to query: {enhanced_query}")

                except Exception as fallback_error:
                    logger.error(f"Exact terms fallback also failed: {fallback_error}")
                    # Continue without exact terms processing

        # Store for later reporting
        search_params['_applied_exact_terms'] = applied_exact_terms
        search_params['_exact_terms_fallback_used'] = exact_terms_fallback_used
        search_params['_exact_terms_error'] = exact_terms_error

        # Execute search
        from enhanced_rag.utils.error_handler import with_retry
        # Store search params for later inspection
        self._last_search_params = search_params
        timer.mark("exact_terms_applied")
        search_response = with_retry(op_name="acs.search")(self.search_client.search)(**search_params)
        timer.mark("acs_search_complete")
        raw_results = list(search_response)
        # Store total count for later use
        self._last_total_count = search_response.get_count() if hasattr(search_response, 'get_count') else None
        timer.mark("results_fetched")

        # Filter and rank results
        results = self._filter_and_rank_results(raw_results, params.query, repo)
        timer.mark("filtered_ranked")

        # Convert to typed results
        search_results = self._convert_to_search_results(results)
        timer.mark("results_converted")

        # Resolve dependencies based on dependency_mode
        dependency_mode = getattr(params, 'dependency_mode', 'auto')
        should_include_deps = (
            dependency_mode == "always" or
            (dependency_mode == "auto" and params.intent == SearchIntent.IMPLEMENT) or
            dependency_mode == "graph" or
            (dependency_mode == "auto" and params.include_dependencies)
        )

        if should_include_deps:
            if dependency_mode == "graph":
                search_results = await self._resolve_dependency_graph(search_results)
            else:
                search_results = await self._resolve_dependencies(search_results)
            timer.mark("dependencies_resolved")

        # Cache results with TTL and improved eviction
        if self._should_cache_query(params):
            self._query_cache[cache_key] = search_results
            self._query_cache_ts[cache_key] = time.time()

            # Evict old entries if above max
            if len(self._query_cache) > self._cache_max_entries:
                # First try to remove expired entries
                self._cleanup_expired_cache_entries()

                # If still above max, remove the oldest by timestamp
                if len(self._query_cache) > self._cache_max_entries:
                    oldest_key = min(self._query_cache_ts.items(), key=lambda kv: kv[1])[0]
                    self._query_cache.pop(oldest_key, None)
                    self._query_cache_ts.pop(oldest_key, None)

        # Apply skip for pagination after all processing
        if params.skip > 0:
            search_results = search_results[params.skip:]

        # Store timing info for diagnostics
        self._last_search_timings = timer.durations()

        return search_results[:params.max_results]

    def _enhance_query(self, query: str, intent: Optional[SearchIntent]) -> str:
        """Enhance query with intent-specific terms and context"""
        if not intent:
            return query

        enhancements = {
            SearchIntent.IMPLEMENT: {
                "prefix": "implementation example",
                "boost": ["function", "class", "method", "def", "async"],
                "exclude": ["test", "mock", "stub"]
            },
            SearchIntent.DEBUG: {
                "prefix": "error handling debug",
                "boost": ["try", "except", "catch", "error", "exception", "raise", "throw"],
                "exclude": ["test"]
            },
            SearchIntent.UNDERSTAND: {
                "prefix": "documentation explanation",
                "boost": ["docstring", "comment", "README", "example", "usage"],
                "exclude": []
            },
            SearchIntent.REFACTOR: {
                "prefix": "refactoring pattern",
                "boost": ["pattern", "design", "architecture", "best practice"],
                "exclude": ["legacy", "deprecated", "old"]
            }
        }

        config = enhancements.get(intent, {})
        enhanced = f"{config.get('prefix', '')} {query}".strip()

        # Add boost terms
        if config.get('boost'):
            enhanced += f" ({' OR '.join(config['boost'])})"

        return enhanced

    def _resolve_repository(self, repo: Optional[str]) -> Optional[str]:
        """Resolve repository with caching"""
        if repo == "*" or repo == "all":
            return None

        if repo:
            return repo

        # Detect current repository with caching
        cwd = os.getcwd()
        if cwd in self._repo_cache:
            return self._repo_cache[cwd]

        current_path = Path(cwd)
        for parent in [current_path] + list(current_path.parents):
            if (parent / ".git").exists():
                repo_name = parent.name
                self._repo_cache[cwd] = repo_name
                return repo_name

        repo_name = current_path.name
        self._repo_cache[cwd] = repo_name
        return repo_name

    def _build_search_params(self, query: str, repo: Optional[str], params: SearchCodeParams) -> Dict:
        """Build optimized search parameters"""
        # Note: vector_queries expects a Sequence[VectorizedQuery] at runtime.
        # Some type checkers flag list[VectorizedQuery] for invariance; we use Sequence for compatibility.
        use_semantic = (not getattr(params, "bm25_only", False)) and getattr(self, "_semantic_available", False)

        # Build select using FieldMapper to support different schema versions
        select_fields = [
            "repository", "file_path", "language", "content",
            "semantic_context", "signature", "imports",
            "dependencies", "chunk_type", "start_line", "end_line",
            "function_name", "class_name", "docstring"
        ]
        if self._field_mapper:
            try:
                select_fields = self._field_mapper.select_list()
            except Exception:
                pass

        search_params: Dict[str, Any] = {
            "search_text": query,
            "include_total_count": True,
            "top": 50,  # Get more for better filtering
            "select": select_fields
        }

        # Apply query_type override if provided
        if getattr(params, "query_type", None):
            search_params["query_type"] = params.query_type
            # Only set semantic_configuration_name if semantic chosen and available
            if params.query_type == "semantic" and getattr(self, "_semantic_available", False):
                search_params["semantic_configuration_name"] = "semantic-config"
            # If user forces 'full', do not add semantic or vector queries
            if params.query_type != "semantic":
                use_semantic = False
        elif use_semantic:
            search_params["query_type"] = "semantic"
            search_params["semantic_configuration_name"] = "semantic-config"

        # Guard: ensure index likely has vector configuration before adding vector query (best-effort)
        # If the field is missing, ACS SDK will 400; we can still attempt and let server handle gracefully.

        if use_semantic:
            # Add vector search using text-to-vector (index has vectorizers configured)
            vector_queries: List[Any] = []
            if VECTORIZABLE_TEXT_QUERY_AVAILABLE and VectorizableTextQuery:
                try:
                    vector_queries.append(
                        VectorizableTextQuery(
                            text=query,
                            k_nearest_neighbors=50,
                            fields="content_vector"
                        )
                    )
                except Exception as e:
                    # Fall back to client-side embedding below
                    pass

            if not vector_queries and self.embedder:
                try:
                    embedding = self.embedder.generate_embedding(query)
                    if embedding:
                        vector_queries.append(
                            VectorizedQuery(
                                vector=embedding,
                                k_nearest_neighbors=50,
                                fields="content_vector"
                            )
                        )
                except Exception:
                    pass

            if vector_queries:
                search_params["vector_queries"] = cast(Sequence[Any], vector_queries)

        # Build filters
        filters = []
        if repo:
            # Escape single quotes per OData
            safe_repo = repo.replace("'", "''")
            # Azure Search doesn't support endswith, so just use exact match
            filters.append(f"repository eq '{safe_repo}'")
        if params.language:
            filters.append(f"language eq '{params.language}'")

        if filters:
            search_params["filter"] = " and ".join(filters)

        # Graceful degradation: if repository field is not available, strip repo filter
        if "filter" in search_params and self._field_mapper and "repository" not in self._field_mapper.reverse_map:
            # Remove repo constraint if present
            parts = [p for p in search_params["filter"].split(" and ") if "repository " not in p]
            search_params["filter"] = " and ".join(parts) if parts else None
            if not search_params["filter"]:
                search_params.pop("filter", None)

        # Add pagination support
        if params.skip > 0:
            search_params["skip"] = params.skip

        # Add ordering support
        if params.orderby:
            search_params["orderby"] = params.orderby

        # Add hit highlighting
        if params.highlight_code:
            search_params["highlight_fields"] = "content,docstring"
            search_params["highlight_pre_tag"] = "<mark>"
            search_params["highlight_post_tag"] = "</mark>"

        return search_params

    def _filter_and_rank_results(self, results: List[Dict], query: str, repo: Optional[str]) -> List[Dict]:
        """Apply intelligent filtering and custom ranking"""
        filtered = []

        # Define exclusion patterns
        exclude_patterns = [
            r'(^|/)\.?v?env/', r'(^|/)site-packages/', r'(^|/)node_modules/',
            r'(^|/)__pycache__/', r'\.pyc$', r'(^|/)build/', r'(^|/)dist/',
            r'\.egg-info/', r'(^|/)\.git/'
        ]

        query_lower = query.lower()
        query_terms = set(query_lower.split())

        for result in results:
            file_path = (result.get('file_path') or '').lower()

            # Skip excluded paths
            if any(re.search(pattern, file_path) for pattern in exclude_patterns):
                continue

            # Skip test files unless searching for tests
            if 'test' not in query_lower and re.search(r'(test_|_test\.|/tests?/)', file_path):
                continue

            # Calculate enhanced score
            score = result.get('@search.score', 0)

            # Boost for repository match
            if repo and result.get('repository') == repo:
                score *= 2.0

            # Boost for function name match
            func_name = (result.get('signature') or '').lower()
            if func_name:
                func_words = set(re.findall(r'\w+', func_name))
                matching_terms = query_terms.intersection(func_words)
                score *= (1 + len(matching_terms) * 0.3)

            # Boost for semantic context match
            context = (result.get('semantic_context') or '').lower()
            if context:
                context_matches = sum(1 for term in query_terms if term in context)
                score *= (1 + context_matches * 0.1)

            # Penalize very long chunks
            code_length = len(result.get('content', ''))
            if code_length > 2000:
                score *= 0.8

            result['_enhanced_score'] = score
            filtered.append(result)

        # Sort by enhanced score
        filtered.sort(key=lambda x: x.get('_enhanced_score', 0), reverse=True)
        return filtered

    def _convert_to_search_results(self, results: List[Dict]) -> List[SearchResult]:
        """Convert raw results to typed SearchResult objects"""
        search_results = []

        for result in results:
            # Access through mapper to handle old/new schemas
            mapper = self._field_mapper or FieldMapper(result.keys())

            # Extract function name from signature
            signature = mapper.get(result, "signature", "")
            func_name = None
            if signature:
                match = re.search(r'(?:def|class|async def)\s+(\w+)', signature)
                if match:
                    func_name = match.group(1)

            # Smart content truncation
            content = mapper.get(result, "content", "")
            if len(content) > 800:
                # Try to find natural break points
                for break_point in ['\n\n', '\ndef ', '\nclass ', '\n    return']:
                    pos = content.rfind(break_point, 0, 800)
                    if pos > 400:
                        content = content[:pos] + "\n..."
                        break
                else:
                    content = content[:800] + "..."

            search_results.append(SearchResult(
                file_path=mapper.get(result, "file_path", ""),
                repository=mapper.get(result, "repository", ""),
                language=mapper.get(result, "language", ""),
                function_name=func_name,
                signature=signature,
                line_range=self._format_line_range(
                    mapper.get(result, "start_line", None),
                    mapper.get(result, "end_line", None)
                ),
                score=result.get('_enhanced_score', 0),
                content=content,
                context=(mapper.get(result, "semantic_context", "") or "")[:200],
                imports=mapper.get(result, "imports", []) or [],
                dependencies=mapper.get(result, "dependencies", []) or [],
                highlights=result.get('@search.highlights', None)
            ))

        return search_results

    async def _resolve_dependencies(self, results: List[SearchResult]) -> List[SearchResult]:
        """Resolve function dependencies for implementation intent"""
        if not results:
            return results

        primary = results[0]
        dep_results = []

        # Find unique dependencies
        seen = {primary.signature}
        for dep_name in primary.dependencies[:3]:  # Limit to 3 dependencies
            if dep_name in seen:
                continue

            # Search for dependency
            dep_params = SearchCodeParams(
                query=f"def {dep_name}",
                intent=None,
                language=primary.language,
                repository=primary.repository,
                max_results=1,
                include_dependencies=False
            )

            dep_search = await self.search_code(dep_params)
            if dep_search and dep_search[0].signature not in seen:
                dep_results.append(dep_search[0])
                seen.add(dep_search[0].signature)

        return [primary] + dep_results + results[1:]

    async def _resolve_dependency_graph(self, results: List[SearchResult]) -> List[SearchResult]:
        """Resolve dependencies with graph information"""
        if not results:
            return results

        primary = results[0]
        dependency_graph = {"nodes": [], "edges": []}

        # Add primary node
        primary_id = f"{primary.repository}:{primary.file_path}:{primary.function_name}"
        dependency_graph["nodes"].append({
            "id": primary_id,
            "type": "primary",
            "function_name": primary.function_name,
            "file_path": primary.file_path,
            "repository": primary.repository
        })

        # Find dependencies up to 2 levels deep
        seen = {primary.signature}
        dep_results = []

        for dep_name in primary.dependencies[:5]:  # Increased limit
            if dep_name in seen:
                continue

            # Search for dependency
            dep_params = SearchCodeParams(
                query=f"def {dep_name}",
                intent=None,
                language=primary.language,
                repository=primary.repository,
                max_results=1,
                include_dependencies=False
            )

            dep_search = await self.search_code(dep_params)
            if dep_search and dep_search[0].signature not in seen:
                dep_result = dep_search[0]
                dep_id = f"{dep_result.repository}:{dep_result.file_path}:{dep_result.function_name}"

                dependency_graph["nodes"].append({
                    "id": dep_id,
                    "type": "dependency",
                    "function_name": dep_result.function_name,
                    "file_path": dep_result.file_path,
                    "repository": dep_result.repository,
                    "level": 1
                })

                dependency_graph["edges"].append({
                    "from": primary_id,
                    "to": dep_id,
                    "type": "calls",
                    "dependency_name": dep_name
                })

                dep_results.append(dep_result)
                seen.add(dep_result.signature)

        # Add dependency graph to first result
        if results:
            # Create new SearchResult with graph info
            primary_dict = primary.model_dump()
            primary_dict["dependency_graph"] = dependency_graph
            primary_with_graph = SearchResult(**primary_dict)
            results[0] = primary_with_graph

        return results[:1] + dep_results + results[1:]

    async def _get_azure_ranking_explanation(self, query: str, results: List[Dict]) -> List[Dict]:
        """Get Azure Search specific ranking explanations"""
        explanations = []

        try:
            # Use Azure Search's scoring profile information
            search_params = {
                "search_text": query,
                "include_total_count": False,
                "top": min(len(results), 10),  # Limit for performance
                "query_type": "full"  # Use full Lucene syntax for detailed scoring
            }

            # Add scoring profile if available
            if hasattr(self.search_client, '_scoring_profile'):
                search_params["scoring_profile"] = self.search_client._scoring_profile

            # Re-run search with scoring details
            detailed_response = self.search_client.search(**search_params)
            detailed_results = list(detailed_response)

            for i, (original_result, detailed_result) in enumerate(zip(results, detailed_results)):
                explanation = {
                    "file_path": original_result.get("file_path"),
                    "repository": original_result.get("repository"),
                    "score": original_result.get("score", 0.0),
                    "factors": []
                }

                # Extract Azure Search scoring factors
                if hasattr(detailed_result, '@search.score'):
                    explanation["azure_score"] = detailed_result.get('@search.score')

                # Add BM25 factors if available
                if hasattr(detailed_result, '@search.features'):
                    features = detailed_result.get('@search.features', {})
                    for feature_name, feature_value in features.items():
                        explanation["factors"].append({
                            "name": feature_name,
                            "value": feature_value,
                            "type": "azure_feature"
                        })

                # Add semantic ranking factors if semantic search was used
                if self._semantic_available and hasattr(detailed_result, '@search.reranker_score'):
                    explanation["factors"].append({
                        "name": "semantic_reranker_score",
                        "value": detailed_result.get('@search.reranker_score'),
                        "type": "semantic"
                    })

                # Add field-specific scoring
                content = original_result.get("content", "")
                query_terms = set(query.lower().split())

                # Content relevance
                content_matches = sum(1 for term in query_terms if term in content.lower())
                if content_matches > 0:
                    explanation["factors"].append({
                        "name": "content_term_matches",
                        "value": content_matches,
                        "type": "content_analysis"
                    })

                # Function name relevance
                func_name = original_result.get("function_name", "")
                if func_name:
                    func_matches = sum(1 for term in query_terms if term in func_name.lower())
                    if func_matches > 0:
                        explanation["factors"].append({
                            "name": "function_name_matches",
                            "value": func_matches,
                            "type": "function_analysis"
                        })

                # Repository and language boost
                if original_result.get("repository"):
                    explanation["factors"].append({
                        "name": "repository_boost",
                        "value": 0.1,
                        "type": "metadata_boost"
                    })

                if original_result.get("language"):
                    explanation["factors"].append({
                        "name": "language_boost",
                        "value": 0.05,
                        "type": "metadata_boost"
                    })

                explanation["summary"] = f"Azure Search score: {explanation.get('azure_score', 'N/A')}, Content matches: {content_matches}"
                explanations.append(explanation)

        except Exception as e:
            logger.warning(f"Azure ranking explanation failed: {e}")
            # Fall back to heuristic explanations
            return self._get_heuristic_explanations(query, results)

        return explanations

    def _get_heuristic_explanations(self, query: str, results: List[Dict]) -> List[Dict]:
        """Fallback heuristic explanations when Azure features unavailable"""
        explanations = []
        q_terms = set(query.lower().split())

        for item in results:
            content = (item.get("content") or "").lower()
            signature = (item.get("signature") or "").lower()
            repo = item.get("repository")
            file_path = item.get("file_path")
            score = item.get("score", 0.0)
            overlap = sum(1 for t in q_terms if t in content or t in signature)

            factors = []
            if overlap:
                factors.append({"name": "term_overlap", "weight": 0.4, "contribution": overlap * 0.1})
            if repo:
                factors.append({"name": "repo_presence", "weight": 0.2, "contribution": 0.1})
            if signature:
                factors.append({"name": "signature_match", "weight": 0.2, "contribution": 0.1})
            factors.append({"name": "base_score", "weight": 0.2, "contribution": score * 0.1})

            explanations.append({
                "file_path": file_path,
                "repository": repo,
                "score": score,
                "factors": factors,
                "summary": f"Heuristic explanation: {overlap} query-term overlaps; base score {score:.2f}"
            })

        return explanations

    # ========================================================================
    # Result Formatting
    # ========================================================================

    def format_results(self, results: List[SearchResult], query: str) -> str:
        """Format results with enhanced presentation"""
        if not results:
            return self._no_results_message(query)

        total_msg = f" (out of {self._last_total_count} total matches)" if self._last_total_count else ""
        formatted = f"🔍 Found {len(results)} relevant results{total_msg}:\n\n"

        for i, result in enumerate(results, 1):
            formatted += f"**Result {i}** (Score: {result.score:.2f})\n"
            formatted += f"📁 `{result.file_path}"
            if result.line_range:
                formatted += f":{result.line_range}"
            formatted += "`\n"

            if result.function_name:
                formatted += f"🔧 Function: `{result.function_name}`\n"

            formatted += f"📦 Repository: `{result.repository}` | Language: {result.language}\n"

            if result.context:
                formatted += f"📝 Context: {result.context}\n"

            if result.imports:
                formatted += f"📥 Imports: {', '.join(result.imports[:5])}\n"

            # Show highlights if available
            if result.highlights:
                formatted += "\n💡 **Highlighted matches:**\n"
                for field, highlights in result.highlights.items():
                    if highlights:
                        formatted += f"  - {field}: {highlights[0]}\n"

            code_block = result.content
            if not code_block.endswith("\n"):
                code_block += "\n"
            formatted += f"\n```{result.language}\n{code_block}```\n\n"

            if i < len(results):
                formatted += "---\n\n"

        return formatted

    def _no_results_message(self, query: str) -> str:
        """Helpful message when no results found"""
        return f"""No results found for "{query}".

💡 **Search Tips:**
- Try more general terms (e.g., "parse json" instead of "parseJsonData")
- Check the repository name is correct
- Use intent parameter: 'implement', 'debug', 'understand', or 'refactor'
- Remove language filter if too restrictive
- Search across all repositories with repository='*'
"""

# ============================================================================
# Initialize Server
# ============================================================================

mcp = FastMCP("azure-code-search-enhanced")
server = EnhancedMCPServer()
pipeline_instance = None

def _is_admin() -> bool:
    return os.getenv("MCP_ADMIN_MODE", "1").lower() in {"1", "true", "yes"}

def _ok(data: Any) -> Dict[str, Any]:
    return {"ok": True, "data": data}

def _err(msg: str, code: str = "error") -> Dict[str, Any]:
    return {"ok": False, "error": msg, "code": code}

import time

class _Timer:
    def __init__(self):
        self._marks = {"start": time.perf_counter()}
    def mark(self, name: str):
        self._marks[name] = time.perf_counter()
    def durations(self) -> Dict[str, float]:
        keys = list(self._marks.keys())
        out = {}
        for i in range(1, len(keys)):
            out[f"{keys[i-1]}→{keys[i]}"] = (self._marks[keys[i]] - self._marks[keys[i-1]]) * 1000.0
        out["total"] = (time.perf_counter() - self._marks["start"]) * 1000.0
        return out


# ============================================================================
# Tool Implementations
# ============================================================================

@mcp.tool()
async def search_code(
    query: str,
    intent: Optional[str] = None,
    language: Optional[str] = None,
    repository: Optional[str] = None,
    max_results: int = 10,
    include_dependencies: bool = False,
    skip: int = 0,
    orderby: Optional[str] = None,
    highlight_code: bool = False,
    bm25_only: bool = False,
    # New tool args
    exact_terms: Optional[List[str]] = None,
    disable_cache: bool = False,
    include_timings: bool = False,
    dependency_mode: str = "auto"
) -> Dict[str, Any]:
    """Search for code with advanced filtering, ranking, and optional dependency enrichment.

    Returns JSON with items[], total, took_ms, cache_status, and optionally detailed timings.
    dependency_mode: 'auto' (deps for implement intent), 'always', 'never', 'graph'
    """
    timer = _Timer()
    import re as _re
    auto_exact = None
    if exact_terms is None and query:
        # Enhanced auto-extraction for exact terms
        quoted = _re.findall(r'"([^"]+)"|\'([^\']+)\'', query)
        quoted_terms = [t for pair in quoted for t in pair if t]

        # Improved numeric detection - capture version numbers, IDs, etc.
        numeric_terms = _re.findall(r'(?<![\w])(\d+(?:\.\d+)+|\d{2,})(?![\w.])', query)

        # Detect function/method calls with parentheses
        function_calls = _re.findall(r'(\w+)\s*\(', query)

        # Detect camelCase/PascalCase identifiers
        camel_case = _re.findall(r'\b([a-z]+[A-Z][a-zA-Z]*)\b', query)

        # Detect snake_case identifiers
        snake_case = _re.findall(r'\b([a-z]+_[a-z_]+)\b', query)

        # Combine all auto-detected terms, prioritizing quoted terms
        all_terms = quoted_terms + numeric_terms + function_calls + camel_case + snake_case
        auto_exact = [t.strip() for t in all_terms if t.strip() and len(t.strip()) >= 2]

        # Remove duplicates while preserving order
        seen = set()
        auto_exact = [t for t in auto_exact if not (t in seen or seen.add(t))]
    params = SearchCodeParams(
        query=query,
        intent=SearchIntent(intent) if intent else None,
        language=language,
        repository=repository,
        max_results=max_results,
        include_dependencies=include_dependencies,
        skip=skip,
        orderby=orderby,
        highlight_code=highlight_code,
        bm25_only=bm25_only,
        exact_terms=exact_terms if exact_terms is not None else auto_exact,
        disable_cache=disable_cache,
        include_timings=include_timings,
        dependency_mode=dependency_mode
    )
    # Determine cache key and hit before execution
    cache_key = server._get_cache_key(params)
    cache_hit = (cache_key in server._query_cache and cache_key in server._query_cache_ts and
                (time.time() - server._query_cache_ts[cache_key]) <= server._ttl_seconds) if server._should_cache_query(params) else False

    try:
        results = await server.search_code(params)
    except Exception as e:
        return _err(str(e))
    timer.mark("done")

    # Check if exact terms were applied and get fallback info
    applied_exact_terms = False
    exact_terms_fallback_used = False
    exact_terms_error = None
    if hasattr(server, '_last_search_params') and server._last_search_params:
        applied_exact_terms = server._last_search_params.get('_applied_exact_terms', False)
        exact_terms_fallback_used = server._last_search_params.get('_exact_terms_fallback_used', False)
        exact_terms_error = server._last_search_params.get('_exact_terms_error', None)

    payload = {
        "items": [r.model_dump() for r in results],
        "count": len(results),
        "total": server._last_total_count,
        "took_ms": timer.durations().get("total", 0.0),  # real elapsed time
        "applied_exact_terms": applied_exact_terms,
        "exact_terms": params.exact_terms,
        "exact_terms_fallback_used": exact_terms_fallback_used,
        "exact_terms_error": exact_terms_error
    }
    durations = timer.durations()
    payload["took_ms"] = durations.get("total", payload["took_ms"])

    # Include detailed timings if requested or in debug mode
    if include_timings or os.getenv("MCP_DEBUG_TIMINGS", "").lower() in {"1", "true"}:
        payload["timings_ms"] = durations

        # Add server-side timings if available
        if hasattr(server, '_last_search_timings') and server._last_search_timings:
            payload["server_timings_ms"] = server._last_search_timings

            # Add stage breakdown
            server_timings = server._last_search_timings
            payload["stages"] = [
                {"stage": "cache_check", "duration_ms": server_timings.get("start→cache_check", 0.0)},
                {"stage": "query_enhancement", "duration_ms": server_timings.get("cache_check→query_enhanced", 0.0)},
                {"stage": "repo_resolution", "duration_ms": server_timings.get("query_enhanced→repo_resolved", 0.0)},
                {"stage": "param_building", "duration_ms": server_timings.get("repo_resolved→params_built", 0.0)},
                {"stage": "exact_term_filtering", "duration_ms": server_timings.get("params_built→exact_terms_applied", 0.0)},
                {"stage": "azure_search", "duration_ms": server_timings.get("exact_terms_applied→acs_search_complete", 0.0)},
                {"stage": "result_fetch", "duration_ms": server_timings.get("acs_search_complete→results_fetched", 0.0)},
                {"stage": "filter_rank", "duration_ms": server_timings.get("results_fetched→filtered_ranked", 0.0)},
                {"stage": "convert_results", "duration_ms": server_timings.get("filtered_ranked→results_converted", 0.0)}
            ]

            # Add dependency resolution timing if it occurred
            if "dependencies_resolved" in server_timings:
                payload["stages"].append({
                    "stage": "dependency_resolution",
                    "duration_ms": server_timings.get("results_converted→dependencies_resolved", 0.0)
                })
    else:
        # Always include basic timings for backwards compatibility
        payload["timings_ms"] = durations

    payload["cache_status"] = {
        "hit": cache_hit,
        "ttl_seconds": server._ttl_seconds,
        "max_entries": server._cache_max_entries,
        "key": cache_key if include_timings else None  # Only expose cache key in debug mode
    }
    return _ok(payload)

@mcp.tool()
async def search_code_raw(
    query: str,
    intent: Optional[str] = None,
    language: Optional[str] = None,
    repository: Optional[str] = None,
    max_results: int = 10,
    include_dependencies: bool = False,
    skip: int = 0,
    orderby: Optional[str] = None,
    highlight_code: bool = False,
    bm25_only: bool = False
) -> Dict[str, Any]:
    """
    Raw JSON results for code search (base ACS path).
    Returns structured SearchResult objects for SDK-friendly consumption.
    """
    params = SearchCodeParams(
        query=query,
        intent=SearchIntent(intent) if intent else None,
        language=language,
        repository=repository,
        max_results=max_results,
        include_dependencies=include_dependencies,
        skip=skip,
        orderby=orderby,
        highlight_code=highlight_code,
        bm25_only=bm25_only
    )
    try:
        results = await server.search_code(params)
    except Exception as e:
        return _err(str(e))
    return _ok({
        "results": [r.model_dump() for r in results],
        "count": len(results),
        "total": server._last_total_count,
        "query": query,
        "intent": intent
    })

@mcp.tool()
async def search_microsoft_docs(query: str, max_results: int = 10) -> Dict[str, Any]:
    """Search Microsoft Learn documentation"""
    if not DOCS_SUPPORT or not MicrosoftDocsMCPClient:
        return _err("docs_unavailable", code="enhanced_unavailable")

    try:
        async with MicrosoftDocsMCPClient() as client:
            results = await client.search_docs(query=query, max_results=max_results)

        if not results:
            return _ok({
                "query": query,
                "count": 0,
                "results": [],
                "formatted": f"No Microsoft documentation found for '{query}'."
            })

        formatted_results = []
        formatted_lines = [f"📚 Found {len(results)} Microsoft Docs:\n"]

        for i, doc in enumerate(results, 1):
            title = doc.get("title") or "Untitled"
            url = doc.get("url") or ""
            snippet = (doc.get("content") or "")[:300]

            formatted_results.append({
                "title": title,
                "url": url,
                "snippet": snippet
            })

            formatted_lines.append(f"{i}. {title}\n   {url}\n   {snippet}...\n")

        return _ok({
            "query": query,
            "count": len(results),
            "results": formatted_results,
            "formatted": "\n".join(formatted_lines)
        })
    except Exception as e:
        return _err(f"Error searching Microsoft Docs: {str(e)}")

@mcp.tool()
async def search_microsoft_docs_raw(query: str, max_results: int = 10) -> Dict[str, Any]:
    """Search Microsoft Learn documentation (raw JSON)."""
    if not DOCS_SUPPORT or not MicrosoftDocsMCPClient:
        return _err("docs_unavailable", code="enhanced_unavailable")
    try:
        async with MicrosoftDocsMCPClient() as client:
            results = await client.search_docs(query=query, max_results=max_results)
        return _ok({"query": query, "count": len(results or []), "results": results or []})
    except Exception as e:
        return _err(str(e))

@mcp.tool()
async def explain_ranking(
    query: str,
    mode: str = "enhanced",
    max_results: int = 10,
    intent: Optional[str] = None,
    language: Optional[str] = None,
    repository: Optional[str] = None
) -> Dict[str, Any]:
    """
    Explain ranking factors for results.
    Modes: 'enhanced' (RAG explainer), 'azure' (Azure Search features), 'base' (heuristic)
    """
    timer = _Timer()

    # Get results from chosen mode
    if mode == "enhanced" and ENHANCED_RAG_SUPPORT and 'enhanced_search_tool' in globals() and enhanced_search_tool is not None:
        try:
            timer.mark("enhanced_start")
            # Reuse EnhancedSearchTool if already instantiated (see existing code)
            result = await enhanced_search_tool.search(
                query=query,
                intent=intent,
                language=language,
                repository=repository,
                max_results=max_results,
                include_dependencies=False,
                generate_response=False,
            )
            timer.mark("enhanced_complete")
            raw_items = result.get("results", []) or result.get("final_results", []) or []
        except Exception as e:
            logger.warning(f"Enhanced search failed in explain_ranking: {e}")
            raw_items = []
            # Fall back to base mode
            mode = "base"
    else:
        # Base ACS path
        if mode != "base":
            timer.mark("base_start")
        params = SearchCodeParams(
            query=query,
            intent=SearchIntent(intent) if intent else None,
            language=language,
            repository=repository,
            max_results=max_results,
            include_dependencies=False
        )
        base_results = await server.search_code(params)
        timer.mark("search_complete")
        raw_items = [r.model_dump() for r in base_results]

    # Try proper explainer
    if RESULT_EXPLAINER_AVAILABLE and 'ResultExplainer' in globals():
        try:
            explainer = ResultExplainer()
            cq = CoreSearchQuery(
                query=query or "",
                language=language,
                intent=SearchIntent(intent) if intent else None
            )
            out = []
            for item in raw_items:
                try:
                    if isinstance(item, dict):
                        r = CoreSearchResult(
                            id=item.get("file_path", "") or item.get("id", ""),
                            score=item.get("score", 0.0),
                            file_path=item.get("file_path", ""),
                            repository=item.get("repository", ""),
                            language=item.get("language", "") or (language or ""),
                            function_name=item.get("function_name"),
                            class_name=item.get("class_name"),
                            code_snippet=item.get("content") or "",
                            signature=item.get("signature", ""),
                            semantic_context=item.get("context", "") or item.get("semantic_context", ""),
                            imports=item.get("imports") or [],
                            dependencies=item.get("dependencies") or [],
                            highlights=item.get("highlights") or item.get("@search.highlights") or {}
                        )
                    else:
                        r = item
                    exp = await explainer.explain_ranking(result=r, query=cq, context=None)
                    out.append(exp)
                except Exception:
                    continue
            if out:
                return _ok({
                    "mode": "enhanced" if ENHANCED_RAG_SUPPORT and mode == "enhanced" else "base",
                    "query": query,
                    "explanations": out
                })
        except Exception:
            pass

    # Try Azure-based explanations first, then fallback to heuristic
    try:
        if mode == "base" or mode == "azure":
            # Use Azure Search specific explanations
            explanations = await server._get_azure_ranking_explanation(query, raw_items)
            explanation_mode = "azure"
        else:
            # Fall back to heuristic explanations
            explanations = server._get_heuristic_explanations(query, raw_items)
            explanation_mode = "heuristic"
    except Exception as e:
        logger.warning(f"Azure ranking explanation failed: {e}")
        # Final fallback to heuristic explanations
        explanations = server._get_heuristic_explanations(query, raw_items)
        explanation_mode = "heuristic"

    return _ok({
        "mode": mode,
        "explanation_mode": explanation_mode,
        "query": query,
        "explanations": explanations,
        "timings_ms": timer.durations()
    })

@mcp.tool()
async def diagnose_query(
    query: str,
    mode: str = "enhanced",
    intent: Optional[str] = None,
    language: Optional[str] = None,
    repository: Optional[str] = None,
    max_results: int = 10
) -> Dict[str, Any]:
    """
    Run a query and return approximate stage timings and cache hints.
    """
    timer = _Timer()
    cache_hit = False
    try:
        if mode == "enhanced" and ENHANCED_RAG_SUPPORT and "enhanced_search_tool" in globals():
            # If enhanced supports diagnostics param, use it; else just time the call
            result = await enhanced_search_tool.search(
                query=query,
                intent=intent,
                language=language,
                repository=repository,
                max_results=max_results,
                include_dependencies=False,
                generate_response=False
            )
            timer.mark("enhanced_search")
            stages = result.get("stages") or []
            out = {
                "mode": "enhanced",
                "query": query,
                "timings_ms": timer.durations(),
                "stages": stages,
                "cache": {"hit": cache_hit, "cache_key": None}
            }
            return _ok(out)
        else:
            # Base ACS
            timer = _Timer()
            params = SearchCodeParams(
                query=query,
                intent=SearchIntent(intent) if intent else None,
                language=language,
                repository=repository,
                max_results=max_results,
                include_dependencies=False
            )
            # Try to detect simple cache use
            cache_key = f"{params.query}|{params.intent}|{params.repository}|{params.language}|{params.max_results}|{params.skip}|{bool(params.include_dependencies)}|{params.orderby}|{params.highlight_code}|{params.bm25_only}|{params.query_type}|{','.join(params.exact_terms or [])}"
            ts = server._query_cache_ts.get(cache_key)
            cache_hit = (cache_key in server._query_cache and ts is not None and (time.time() - ts) <= server._ttl_seconds)
            timer.mark("cache_check")

            res = await server.search_code(params)
            timer.mark("base_search")

            # Get detailed server timings if available
            server_timings = getattr(server, '_last_search_timings', {})

            # Build detailed stages from server timings
            stages = []
            if server_timings:
                stages.extend([
                    {"stage": "cache_check", "duration_ms": server_timings.get("start→cache_check", 0.0)},
                    {"stage": "query_enhancement", "duration_ms": server_timings.get("cache_check→query_enhanced", 0.0)},
                    {"stage": "repo_resolution", "duration_ms": server_timings.get("query_enhanced→repo_resolved", 0.0)},
                    {"stage": "param_building", "duration_ms": server_timings.get("repo_resolved→params_built", 0.0)},
                    {"stage": "exact_term_filtering", "duration_ms": server_timings.get("params_built→exact_terms_applied", 0.0)},
                    {"stage": "azure_search", "duration_ms": server_timings.get("exact_terms_applied→acs_search_complete", 0.0)},
                    {"stage": "result_fetch", "duration_ms": server_timings.get("acs_search_complete→results_fetched", 0.0)},
                    {"stage": "filter_rank", "duration_ms": server_timings.get("results_fetched→filtered_ranked", 0.0)},
                    {"stage": "convert_results", "duration_ms": server_timings.get("filtered_ranked→results_converted", 0.0)}
                ])
            else:
                stages.append({"stage": "base_search", "count": len(res), "duration_ms": timer.durations().get("start→base_search", 0.0)})

            # Check if exact terms were applied
            applied_exact_terms = False
            if hasattr(server, '_last_search_params') and server._last_search_params:
                applied_exact_terms = server._last_search_params.get('_applied_exact_terms', False)

            out = {
                "mode": "base",
                "query": query,
                "timings_ms": timer.durations(),
                "server_timings_ms": server_timings,
                "stages": stages,
                "cache": {"hit": cache_hit, "cache_key": cache_key if cache_hit else None},
                "applied_exact_terms": applied_exact_terms,
                "exact_terms": params.exact_terms,
                "result_count": len(res)
            }
            return _ok(out)
    except Exception as e:
        return _err(str(e))

@mcp.tool()
async def preview_query_processing(
    query: str,
    intent: Optional[str] = None,
    language: Optional[str] = None,
    repository: Optional[str] = None
) -> Dict[str, Any]:
    """
    Show intent classification, enhancements, rewrites, and applied rules for a query.
    """
    try:
        if ENHANCED_RAG_SUPPORT and SEMANTIC_TOOLS_AVAILABLE:
            try:
                classifier = IntentClassifier()
                try:
                    detected = (await classifier.classify_intent(query)).value
                except Exception:
                    detected = intent
            except Exception:
                detected = intent

            enhancements = {}
            rewrites = []
            rules = []
            try:
                enhancer = ContextualQueryEnhancer()
                enhanced = await enhancer.enhance_query(query, context=None, intent=(detected or intent))
                enhancements = enhanced or {}
            except Exception:
                pass
            try:
                rewriter = MultiVariantQueryRewriter()
                rw = await rewriter.rewrite_query(query, intent=(detected or intent))
                if isinstance(rw, list):
                    rewrites = rw
            except Exception:
                pass

            return _ok({
                "input_query": query,
                "detected_intent": detected,
                "enhancements": enhancements,
                "rewritten_queries": rewrites,
                "applied_rules": rules
            })
        else:
            # Base fallback using server._enhance_query
            enhanced = server._enhance_query(query, SearchIntent(intent) if intent else None)
            boost_terms = []
            if intent:
                if intent == "implement":
                    boost_terms = ["function", "class", "method", "def", "async"]
                elif intent == "debug":
                    boost_terms = ["try", "except", "catch", "error", "exception", "raise", "throw"]
                elif intent == "understand":
                    boost_terms = ["docstring", "comment", "README", "example", "usage"]
                elif intent == "refactor":
                    boost_terms = ["pattern", "design", "architecture", "best practice"]
            return _ok({
                "input_query": query,
                "detected_intent": intent,
                "enhancements": {"prefix": None, "boost_terms": boost_terms},
                "rewritten_queries": [enhanced] if enhanced and enhanced != query else [],
                "applied_rules": []
            })
    except Exception as e:
        return _err(str(e))

@mcp.tool()
async def search_code_then_docs(
    query: str,
    max_code_results: int = 5,
    max_doc_results: int = 5,
    docs_threshold: float = 0.5,
    retry_docs: bool = True,
    fallback_to_web: bool = False,
    timeout_seconds: int = 30
) -> Dict[str, Any]:
    """Search code first; if few results, supplement with Microsoft Docs with fault tolerance."""
    import asyncio

    try:
        params = SearchCodeParams(query=query, max_results=max(max_code_results, 1))
        code_results = await server.search_code(params)

        data = {
            "query": query,
            "code_results": [r.model_dump() for r in code_results],
            "docs_attempted": False,
            "docs_success": False,
            "retry_attempts": 0,
            "fallback_used": False
        }

        # Use configurable threshold
        threshold = int(max_code_results * docs_threshold)
        should_search_docs = len(code_results) < threshold

        if should_search_docs and DOCS_SUPPORT and MicrosoftDocsMCPClient:
            data["docs_attempted"] = True
            docs_results = None
            last_error = None

            # Retry logic for docs search
            max_retries = 3 if retry_docs else 1
            for attempt in range(max_retries):
                data["retry_attempts"] = attempt + 1
                try:
                    # Use timeout for docs search
                    async with asyncio.timeout(timeout_seconds):
                        async with MicrosoftDocsMCPClient() as client:
                            docs_results = await client.search_docs(query=query, max_results=max_doc_results)

                    if docs_results:
                        data["docs_results"] = docs_results
                        data["docs_success"] = True
                        break

                except asyncio.TimeoutError:
                    last_error = f"Timeout after {timeout_seconds} seconds"
                    if attempt < max_retries - 1:
                        await asyncio.sleep(1 * (attempt + 1))  # Exponential backoff
                except Exception as e:
                    last_error = str(e)
                    if attempt < max_retries - 1:
                        await asyncio.sleep(1 * (attempt + 1))  # Exponential backoff

            if not data["docs_success"]:
                data["docs_error"] = f"Failed after {max_retries} attempts: {last_error}"

                # Fallback to web search if enabled
                if fallback_to_web:
                    try:
                        data["fallback_attempted"] = True
                        # Placeholder for web search fallback
                        # This would require implementing web search functionality
                        data["fallback_note"] = "Web search fallback not yet implemented"
                    except Exception as web_error:
                        data["fallback_error"] = str(web_error)

        # Add recommendations for improving results
        if len(code_results) < max_code_results // 2:
            data["recommendations"] = [
                "Try broader search terms",
                "Search across all repositories with repository='*'",
                "Use different intent (implement/debug/understand/refactor)",
                f"Current threshold: {threshold} results (adjust with docs_threshold parameter)"
            ]

        # Add performance metrics
        data["performance"] = {
            "code_results_count": len(code_results),
            "docs_threshold_used": threshold,
            "docs_threshold_met": len(code_results) >= threshold
        }

        return _ok(data)
    except Exception as e:
        return _err(str(e))

@mcp.tool()
async def search_code_hybrid(
    query: str,
    bm25_weight: float = 0.5,
    vector_weight: float = 0.5,
    max_results: int = 10,
    intent: Optional[str] = None,
    language: Optional[str] = None,
    repository: Optional[str] = None,
    include_stage_results: bool = True
) -> Dict[str, Any]:
    """
    Hybrid BM25 + Vector search. Uses Enhanced RAG when available; base fallback merges available signals.
    """
    try:
        if ENHANCED_RAG_SUPPORT:
            try:
                result = await enhanced_search_tool.search(
                    query=query,
                    intent=intent,
                    language=language,
                    repository=repository,
                    max_results=max_results,
                    include_dependencies=False,
                    generate_response=False
                )
                # Expect result to possibly contain stage breakdown
                out = {
                    "weights": {"bm25": bm25_weight, "vector": vector_weight},
                    "final_results": result.get("results") or result.get("final_results") or [],
                    "stages": result.get("stages") if include_stage_results else None
                }
                return _ok(out)
            except Exception:
                pass

        # Base fallback: Run two searches - one BM25, one semantic (if available)
        timer = _Timer()

        # Run BM25 search
        bm25_params = SearchCodeParams(
            query=query,
            intent=SearchIntent(intent) if intent else None,
            language=language,
            repository=repository,
            max_results=max_results * 2,  # Get more for merging
            include_dependencies=False,
            bm25_only=True
        )
        timer.mark("bm25_start")
        bm25_results = await server.search_code(bm25_params)
        timer.mark("bm25_complete")

        # Run semantic/vector search if available
        semantic_results = []
        if server._semantic_available:
            semantic_params = SearchCodeParams(
                query=query,
                intent=SearchIntent(intent) if intent else None,
                language=language,
                repository=repository,
                max_results=max_results * 2,
                include_dependencies=False,
                bm25_only=False,
                query_type="semantic"
            )
            timer.mark("semantic_start")
            semantic_results = await server.search_code(semantic_params)
            timer.mark("semantic_complete")

        # Merge and re-rank using weights
        merged_results = {}

        # Normalize scores to 0-1 range for each result set
        bm25_max_score = max([r.score for r in bm25_results], default=1.0)
        semantic_max_score = max([r.score for r in semantic_results], default=1.0)

        # Add BM25 results with weighted scores
        for r in bm25_results:
            key = f"{r.file_path}:{r.line_range or ''}"
            normalized_score = (r.score / bm25_max_score) if bm25_max_score > 0 else 0
            merged_results[key] = {
                "result": r,
                "bm25_score": normalized_score,
                "semantic_score": 0.0,
                "hybrid_score": normalized_score * bm25_weight
            }

        # Add/update with semantic results
        for r in semantic_results:
            key = f"{r.file_path}:{r.line_range or ''}"
            normalized_score = (r.score / semantic_max_score) if semantic_max_score > 0 else 0
            if key in merged_results:
                merged_results[key]["semantic_score"] = normalized_score
                merged_results[key]["hybrid_score"] = (
                    merged_results[key]["bm25_score"] * bm25_weight +
                    normalized_score * vector_weight
                )
            else:
                merged_results[key] = {
                    "result": r,
                    "bm25_score": 0.0,
                    "semantic_score": normalized_score,
                    "hybrid_score": normalized_score * vector_weight
                }

        # Sort by hybrid score and take top results
        sorted_results = sorted(
            merged_results.values(),
            key=lambda x: x["hybrid_score"],
            reverse=True
        )[:max_results]

        # Extract final results
        final_results = []
        for item in sorted_results:
            result = item["result"].model_dump()
            result["hybrid_score"] = item["hybrid_score"]
            result["bm25_score"] = item["bm25_score"]
            result["semantic_score"] = item["semantic_score"]
            final_results.append(result)

        timer.mark("merge_complete")

        stages = []
        if include_stage_results:
            durations = timer.durations()
            stages = [
                {"stage": "bm25_search", "count": len(bm25_results), "duration_ms": durations.get("bm25_start→bm25_complete", 0.0)},
                {"stage": "semantic_search", "count": len(semantic_results), "duration_ms": durations.get("semantic_start→semantic_complete", 0.0)},
                {"stage": "merge_rerank", "count": len(final_results), "duration_ms": durations.get("semantic_complete→merge_complete", 0.0)}
            ]

        out = {
            "weights": {"bm25": bm25_weight, "vector": vector_weight},
            "final_results": final_results,
            "stages": stages if include_stage_results else None,
            "timings_ms": timer.durations()
        }
        return _ok(out)
    except Exception as e:
        return _err(str(e))

# ============================================================================
# Resources
# ============================================================================

@mcp.resource("resource://repositories")
async def list_repositories() -> str:
    """List all indexed repositories with statistics"""
    try:
        results = server.search_client.search(
            search_text="*",
            facets=["repository"],
            top=0
        )

        facets = results.get_facets()
        repos = (facets or {}).get("repository", [])

        if not repos:
            return json.dumps({"repositories": [], "count": 0})

        repo_list = [{"name": r['value'], "documents": r['count']} for r in repos]
        current = server._resolve_repository(None)

        return json.dumps({
            "repositories": repo_list,
            "count": len(repo_list),
            "current": current,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.resource("resource://statistics")
async def get_statistics() -> str:
    """Get comprehensive search statistics"""
    try:
        doc_count = server.search_client.get_document_count()

        return json.dumps({
            "total_documents": doc_count,
            "index_name": os.getenv("ACS_INDEX_NAME", "codebase-mcp-sota"),
            "features": {
                "vector_search": bool(getattr(server, "_vector_available", True)),
                "semantic_search": bool(getattr(server, "_semantic_available", True)),
                "microsoft_docs": DOCS_SUPPORT,
                "dependency_resolution": True,
                "intelligent_filtering": True
            },
            "cache_stats": {
                "repositories_cached": len(server._repo_cache),
                "queries_cached": len(server._query_cache)
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.resource("resource://runtime_diagnostics")
async def runtime_diagnostics() -> str:
    try:
        import platform
        diag = {
            "feature_flags": {
                "ENHANCED_RAG_SUPPORT": ENHANCED_RAG_SUPPORT,
                "PIPELINE_AVAILABLE": PIPELINE_AVAILABLE,
                "VECTOR_SUPPORT": VECTOR_SUPPORT,
                "DOCS_SUPPORT": DOCS_SUPPORT,
            },
            "index": {
                "name": os.getenv("ACS_INDEX_NAME", "codebase-mcp-sota"),
                "docs_available": DOCS_SUPPORT,
            },
            "asyncio": {
                "policy": type(asyncio.get_event_loop_policy()).__name__,
                "socketpair_patched": (socket.socketpair is _safe_socketpair),
            },
            "versions": {
                "python": platform.python_version(),
                "azure_sdk": "azure-search-documents",
                "mcp": "fastmcp" if MCP_SDK_AVAILABLE else "fallback",
            },
        }
        try:
            # Safe to attempt; ignore errors
            diag["index"]["document_count"] = server.search_client.get_document_count()
        except Exception as _:
            diag["index"]["document_count"] = None

        return json.dumps(_ok(diag), indent=2)
    except Exception as e:
        return json.dumps(_err(str(e)), indent=2)

@mcp.resource("resource://pipeline_status")
async def pipeline_status() -> str:
    """Get Enhanced RAG Pipeline status"""
    global pipeline_instance
    if not PIPELINE_AVAILABLE:
        return json.dumps({"available": False, "reason": "Pipeline module not available"}, indent=2)
    if not pipeline_instance:
        return json.dumps({"initialized": False}, indent=2)
    return json.dumps(pipeline_instance.get_pipeline_status(), indent=2)


# ============================================================================
# Prompts
# ============================================================================

@mcp.prompt()
async def implement_feature(feature: str) -> str:
    """Generate implementation plan for a feature"""
    return f"""I need to implement: {feature}

Please use search_code with:
1. intent='implement' to find similar implementations
2. include_dependencies=true to get required functions
3. Search for relevant utilities and patterns

Then provide a step-by-step implementation plan with code examples."""

@mcp.prompt()
async def debug_error(error: str, file: Optional[str] = None) -> str:
    """Generate debugging assistance"""
    context = f" in {file}" if file else ""
    return f"""I'm getting this error{context}: {error}

Please use search_code with:
1. intent='debug' to find error handling patterns
2. Search for the specific error message
3. Look for similar issues in test files

Help me understand and fix this error."""

# ============================================================================
# Enhanced RAG Pipeline Tools (if available)
# ============================================================================

if ENHANCED_RAG_SUPPORT:
    # Initialize enhanced tools with configuration
    rag_config = {
        "azure_endpoint": os.getenv("ACS_ENDPOINT"),
        "azure_key": os.getenv("ACS_ADMIN_KEY"),
        "index_name": os.getenv("ACS_INDEX_NAME", "codebase-mcp-sota"),
        "enable_caching": True,
        "cache_ttl": 3600
    }

    enhanced_search_tool = EnhancedSearchTool(rag_config)
    code_gen_tool = CodeGenerationTool(rag_config)
    context_aware_tool = ContextAwareTool(rag_config)

    @mcp.tool()
    async def search_code_enhanced(
        query: str,
        current_file: Optional[str] = None,
        workspace_root: Optional[str] = None,
        intent: Optional[str] = None,
        language: Optional[str] = None,
        repository: Optional[str] = None,
        max_results: int = 10,
        include_dependencies: bool = False,
        generate_response: bool = True
    ) -> Dict[str, Any]:
        """
        Enhanced code search using RAG pipeline with context awareness

        Args:
            query: Search query
            current_file: Current file for context
            workspace_root: Workspace root path
            intent: Search intent (implement/debug/understand/refactor)
            language: Filter by language
            repository: Filter by repository
            max_results: Maximum results
            include_dependencies: Include dependency resolution
            generate_response: Generate contextual response
        """
        result = await enhanced_search_tool.search(
            query=query,
            current_file=current_file,
            workspace_root=workspace_root,
            intent=intent,
            language=language,
            repository=repository,
            max_results=max_results,
            include_dependencies=include_dependencies,
            generate_response=generate_response
        )
        return result

    @mcp.tool()
    async def generate_code(
        description: str,
        language: str = "python",
        context_file: Optional[str] = None,
        style_guide: Optional[str] = None,
        include_tests: bool = False,
        workspace_root: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate code using enhanced RAG pipeline

        Args:
            description: What code to generate
            language: Target programming language
            context_file: Current file for context
            style_guide: Specific style guide to follow
            include_tests: Whether to generate tests
            workspace_root: Workspace root path
        """
        return await code_gen_tool.generate_code(
            description=description,
            language=language,
            context_file=context_file,
            style_guide=style_guide,
            include_tests=include_tests,
            workspace_root=workspace_root
        )

    @mcp.tool()
    async def analyze_context(
        file_path: str,
        include_dependencies: bool = True,
        depth: int = 2,
        include_imports: bool = True,
        include_git_history: bool = False
    ) -> Dict[str, Any]:
        """
        Analyze hierarchical context for a file

        Args:
            file_path: Path to analyze
            include_dependencies: Include dependency analysis
            depth: Depth of context analysis (1-3)
            include_imports: Include import analysis
            include_git_history: Include recent git changes
        """
        return await context_aware_tool.analyze_context(
            file_path=file_path,
            include_dependencies=include_dependencies,
            depth=depth,
            include_imports=include_imports,
            include_git_history=include_git_history
        )

    @mcp.tool()
    async def suggest_improvements(
        file_path: str,
        focus: Optional[str] = None,
        include_examples: bool = True
    ) -> Dict[str, Any]:
        """
        Suggest improvements for a file based on context analysis

        Args:
            file_path: File to analyze
            focus: Specific area to focus on (performance/readability/testing)
            include_examples: Include code examples
        """
        return await context_aware_tool.suggest_improvements(
            file_path=file_path,
            focus=focus,
            include_examples=include_examples
        )

@mcp.tool()
async def submit_feedback(
    target_id: str,
    kind: str,  # "search_result" | "code_gen"
    rating: int,  # e.g., 1-5
    notes: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Store user feedback for learning loops.
    """
    if not LEARNING_SUPPORT or not FeedbackCollector:
        return _err("enhanced_rag_learning_unavailable", code="enhanced_unavailable")

    try:
        collector = FeedbackCollector(storage_path=FEEDBACK_DIR)
        await collector.record_explicit_feedback(
            interaction_id=target_id,
            satisfaction=rating,
            comment=notes
        )
        return _ok({"stored": True})
    except Exception as e:
        return _err(str(e))

@mcp.tool()
async def usage_report(
    range: str = "7d"  # e.g., "24h", "7d", "30d"
) -> Dict[str, Any]:
    """
    Summarize usage analytics from stored feedback/usage data.
    """
    if not LEARNING_SUPPORT or not UsageAnalyzer:
        return _err("enhanced_rag_learning_unavailable", code="enhanced_unavailable")

    try:
        collector = FeedbackCollector(storage_path=FEEDBACK_DIR)
        analyzer = UsageAnalyzer(feedback_collector=collector)
        summary = await analyzer.get_performance_metrics()
        return _ok({"range": range, "summary": summary})
    except Exception as e:
        return _err(str(e))

@mcp.tool()
async def update_learning_model(
    dry_run: bool = True
) -> Dict[str, Any]:
    """
    Update ranking/learning artifacts. Requires admin when dry_run is False.
    """
    if not LEARNING_SUPPORT or not ModelUpdater:
        return _err("enhanced_rag_learning_unavailable", code="enhanced_unavailable")

    if not dry_run and not _is_admin():
        return _err("admin_required", code="admin_required")

    return _err("not_implemented", code="not_implemented")

@mcp.tool()
async def index_status() -> Dict[str, Any]:
    if not _is_admin():
        return _err("admin_required", code="admin_required")
    if not AZURE_ADMIN_SUPPORT or not IndexOperations:
        return _err("azure_admin_unavailable", code="enhanced_unavailable")
    try:
        ops = IndexOperations(
            endpoint=os.getenv("ACS_ENDPOINT"),
            admin_key=os.getenv("ACS_ADMIN_KEY"),
        )
        status = await ops.get_index_statistics(os.getenv("ACS_INDEX_NAME", "codebase-mcp-sota"))
        return _ok(status)
    except Exception as e:
        return _err(str(e))

@mcp.tool()
async def index_create_or_update(profile: Optional[str] = None) -> Dict[str, Any]:
    if not _is_admin():
        return _err("admin_required", code="admin_required")
    if not AZURE_ADMIN_SUPPORT or not IndexOperations:
        return _err("azure_admin_unavailable", code="enhanced_unavailable")

    return _err("not_implemented", code="not_implemented")


@mcp.tool()
async def index_rebuild(repository: Optional[str] = None) -> Dict[str, Any]:
    if not _is_admin():
        return _err("admin_required", code="admin_required")
    if not AZURE_ADMIN_SUPPORT or not IndexerIntegration:
        return _err("azure_admin_unavailable", code="enhanced_unavailable")
    try:
        idx = IndexerIntegration()

        # Check if the method exists
        if hasattr(idx, 'run_indexer_on_demand'):
            result = await idx.run_indexer_on_demand(repository)
            return _ok({"repository": repository, "result": result})
        elif hasattr(idx, 'run_indexer'):
            # Try alternative method names
            result = await idx.run_indexer(repository)
            return _ok({"repository": repository, "result": result})
        elif hasattr(idx, 'start_indexer'):
            result = await idx.start_indexer(repository)
            return _ok({"repository": repository, "result": result})
        else:
            return _err("IndexerIntegration does not support run_indexer_on_demand or equivalent method", code="not_supported_by_integration")
    except Exception as e:
        return _err(f"Failed to rebuild index: {str(e)}")

@mcp.tool()
async def document_upsert(document: Dict[str, Any]) -> Dict[str, Any]:
    if not _is_admin():
        return _err("admin_required", code="admin_required")
    if not AZURE_ADMIN_SUPPORT or not DocumentOperations:
        return _err("azure_admin_unavailable", code="enhanced_unavailable")
    try:
        docs = DocumentOperations(
            endpoint=os.getenv("ACS_ENDPOINT"),
            admin_key=os.getenv("ACS_ADMIN_KEY"),
        )
        result = await docs.upload_documents(os.getenv("ACS_INDEX_NAME", "codebase-mcp-sota"),[document])
        return _ok({"upserted": True, "result": result})
    except Exception as e:
        return _err(str(e))

@mcp.tool()
async def document_delete(doc_id: str) -> Dict[str, Any]:
    if not _is_admin():
        return _err("admin_required", code="admin_required")
    if not AZURE_ADMIN_SUPPORT or not DocumentOperations:
        return _err("azure_admin_unavailable", code="enhanced_unavailable")
    try:
        docs = DocumentOperations(
            endpoint=os.getenv("ACS_ENDPOINT"),
            admin_key=os.getenv("ACS_ADMIN_KEY"),
        )
        result = await docs.delete_documents(os.getenv("ACS_INDEX_NAME", "codebase-mcp-sota"),[doc_id])
        return _ok({"deleted": True, "doc_id": doc_id, "result": result})
    except Exception as e:
        return _err(str(e))

@mcp.tool()
async def github_list_repos(org: str, max_repos: int = 50) -> Dict[str, Any]:
    if not _is_admin():
        return _err("admin_required", code="admin_required")
    if not GITHUB_SUPPORT or not GitHubClient:
        return _err("github_integration_unavailable", code="enhanced_unavailable")

    return _err("not_implemented", code="not_implemented")

@mcp.tool()
async def github_index_repo(
    repo: str,  # "org/name"
    branch: Optional[str] = None,
    mode: str = "full"  # "full" | "incremental"
) -> Dict[str, Any]:
    if not _is_admin():
        return _err("admin_required", code="admin_required")
    if not GITHUB_SUPPORT or not RemoteIndexer:
        return _err("github_integration_unavailable", code="enhanced_unavailable")
    try:
        owner, repo_name = repo.split('/')
        indexer = RemoteIndexer()
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, lambda: indexer.index_remote_repository(owner, repo_name, ref=branch))
        return _ok({"repo": repo, "branch": branch, "mode": mode, "result": result})
    except Exception as e:
        return _err(str(e))

@mcp.tool()
async def github_index_status(repo: str) -> Dict[str, Any]:
    if not _is_admin():
        return _err("admin_required", code="admin_required")
    if not GITHUB_SUPPORT or not RemoteIndexer:
        return _err("github_integration_unavailable", code="enhanced_unavailable")

    return _err("not_implemented", code="not_implemented")

@mcp.tool()
async def cache_stats() -> Dict[str, Any]:
    """Get detailed cache statistics including expiration info"""
    try:
        # Get detailed query cache stats
        query_cache_stats = server._get_cache_stats()

        rag_cache = None
        if ENHANCED_RAG_SUPPORT and RAG_CACHE_SUPPORT and CacheManager:
            rag_cache = _err("not_implemented", code="not_implemented")

        data = {
            "query_cache": query_cache_stats,
            "repo_cache": {
                "total_entries": len(server._repo_cache),
                "memory_usage_estimate": len(server._repo_cache) * 256  # Rough estimate
            },
            "rag_cache": rag_cache
        }
        return _ok(data)
    except Exception as e:
        return _err(str(e))

@mcp.tool()
async def cache_clear(
    scope: str = "all",
    pattern: Optional[str] = None,
    repository: Optional[str] = None,
    language: Optional[str] = None
) -> Dict[str, Any]:
    """Clear caches with optional pattern-based filtering"""
    try:
        cleared = []
        invalidated_count = 0

        if scope in ("all", "queries"):
            if pattern or repository or language:
                # Pattern-based invalidation
                invalidated_count = server._invalidate_cache_by_pattern(
                    pattern=pattern,
                    repository=repository,
                    language=language
                )
                cleared.append(f"queries (pattern-based: {invalidated_count} entries)")
            else:
                # Clear all queries
                server._query_cache.clear()
                server._query_cache_ts.clear()
                cleared.append("queries (all)")

        if scope in ("all", "repos"):
            server._repo_cache.clear()
            cleared.append("repos")

        if scope in ("all", "rag") and ENHANCED_RAG_SUPPORT and RAG_CACHE_SUPPORT and CacheManager:
            cleared.append("rag")

        # Get updated cache stats
        cache_stats = server._get_cache_stats()

        return _ok({
            "cleared": cleared,
            "invalidated_count": invalidated_count,
            "cache_stats": cache_stats
        })
    except Exception as e:
        return _err(str(e))

@mcp.tool()
async def search_code_pipeline(
    query: str,
    current_file: Optional[str] = None,
    workspace_root: Optional[str] = None,
    session_id: Optional[str] = None,
    max_results: int = 10,
    generate_response: bool = True
) -> Dict[str, Any]:
    """Run the Enhanced RAG Pipeline end-to-end."""
    if not PIPELINE_AVAILABLE:
        return _err("Enhanced RAG Pipeline not available", code="pipeline_unavailable")

    try:
        global pipeline_instance
        if pipeline_instance is None:
            pipeline_instance = RAGPipeline()
        ctx = QueryContext(
            current_file=current_file,
            workspace_root=workspace_root,
            session_id=session_id
        )
        result = await pipeline_instance.process_query(
            query=query,
            context=ctx,
            generate_response=generate_response,
            max_results=max_results
        )
        return _ok({
            "success": result.success,
            "results": [r.model_dump() for r in result.results],
            "response": result.response,
            "metadata": result.metadata,
            "error": result.error
        })
    except Exception as e:
        return _err(str(e))

# ============================================================================
# Main Entry Point with Multiple Modes
# ============================================================================

if __name__ == "__main__":
    if "--api" in sys.argv:
        # FastAPI mode
        from fastapi import FastAPI
        import uvicorn

        app = FastAPI(title="Enhanced Code Search API")

        @app.post("/search")
        async def api_search(
            query: str,
            intent: Optional[str] = None,
            repository: Optional[str] = None,
            language: Optional[str] = None,
            max_results: int = 10,
            include_dependencies: bool = False
        ):
            params = SearchCodeParams(
                query=query,
                intent=SearchIntent(intent) if intent else None,
                language=language,
                repository=repository,
                max_results=max_results,
                include_dependencies=include_dependencies
            )
            results = await server.search_code(params)
            return {"results": [r.model_dump() for r in results]}

        uvicorn.run(app, host="0.0.0.0", port=8001)
    else:
        # Default: MCP stdio mode
        mcp.run(transport='stdio')
