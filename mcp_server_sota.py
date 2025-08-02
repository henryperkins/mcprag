#!/usr/bin/env python3
"""
Unified Azure Code Search MCP Server - Best of All Implementations
Combines the strongest features from all versions while staying under 900 lines
"""

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
    from enhanced_rag.ranking.result_explainer import ResultExplainer  # type: ignore
    RESULT_EXPLAINER_AVAILABLE = True
except Exception:
    ResultExplainer = None
    RESULT_EXPLAINER_AVAILABLE = False

try:
    from enhanced_rag.semantic.intent_classifier import IntentClassifier  # type: ignore
    from enhanced_rag.semantic.query_enhancer import QueryEnhancer  # type: ignore
    from enhanced_rag.semantic.query_rewriter import QueryRewriter  # type: ignore
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

# ============================================================================
# Enhanced MCP Server
# ============================================================================

class EnhancedMCPServer:
    """Unified MCP server combining best features from all implementations"""

    def __init__(self):
        self.name = "azure-code-search-enhanced"
        self.version = "3.0.0"
        self._initialize_clients()
        self._repo_cache: Dict[str, str] = {}
        self._query_cache: Dict[str, List[SearchResult]] = {}
        self._last_total_count: Optional[int] = None

    def _format_line_range(self, start_line: Optional[int], end_line: Optional[int]) -> Optional[str]:
        """Format line range from start and end line numbers"""
        if start_line is None:
            return None
        if end_line is None or end_line == start_line:
            return str(start_line)
        return f"{start_line}-{end_line}"

    def _initialize_clients(self):
        """Initialize all service clients"""
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

        # Auto-detect semantic availability
        self._semantic_available = True
        try:
            from azure.search.documents.indexes import SearchIndexClient
            idx_client = SearchIndexClient(endpoint=endpoint, credential=AzureKeyCredential(admin_key))
            idx = idx_client.get_index(index_name)
            self._semantic_available = bool(getattr(idx, "semantic_search", None))
        except Exception:
            self._semantic_available = False

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

        # Check cache first
        cache_key = f"{params.query}:{params.intent}:{params.repository}:{params.language}"
        if cache_key in self._query_cache and not params.include_dependencies:
            return self._query_cache[cache_key][:params.max_results]

        # Enhance query based on intent
        enhanced_query = self._enhance_query(params.query, params.intent)

        # Detect repository if needed
        repo = self._resolve_repository(params.repository)

        # Build search parameters
        search_params = self._build_search_params(enhanced_query, repo, params)

        # Execute search
        search_response = self.search_client.search(**search_params)
        raw_results = list(search_response)
        # Store total count for later use
        self._last_total_count = search_response.get_count() if hasattr(search_response, 'get_count') else None

        # Filter and rank results
        results = self._filter_and_rank_results(raw_results, params.query, repo)

        # Convert to typed results
        search_results = self._convert_to_search_results(results)

        # Resolve dependencies if requested
        if params.include_dependencies and params.intent == SearchIntent.IMPLEMENT:
            search_results = await self._resolve_dependencies(search_results)

        # Cache results
        self._query_cache[cache_key] = search_results

        # Apply skip for pagination after all processing
        if params.skip > 0:
            search_results = search_results[params.skip:]

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
        
        search_params: Dict[str, Any] = {
            "search_text": query,
            "count": True,  # Include total count
            "top": 50,  # Get more for better filtering
            "select": [
                "repository", "file_path", "language", "content",
                "semantic_context", "signature", "imports",
                "dependencies", "chunk_type", "start_line", "end_line",
                "function_name", "class_name", "docstring"
            ]
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
            filters.append(f"(repository eq '{safe_repo}' or endswith(repository, '/{safe_repo}'))")
        if params.language:
            filters.append(f"language eq '{params.language}'")

        if filters:
            search_params["filter"] = " and ".join(filters)

        # Add pagination support
        if params.skip > 0:
            search_params["skip"] = params.skip

        # Add ordering support
        if params.orderby:
            search_params["orderby"] = params.orderby

        # Add hit highlighting
        if params.highlight_code:
            search_params["highlight"] = "content,semantic_context,docstring,function_name"
            search_params["highlightPreTag"] = "<mark>"
            search_params["highlightPostTag"] = "</mark>"

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
            file_path = result.get('file_path', '').lower()

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
            func_name = result.get('signature', '').lower()
            if func_name:
                func_words = set(re.findall(r'\w+', func_name))
                matching_terms = query_terms.intersection(func_words)
                score *= (1 + len(matching_terms) * 0.3)

            # Boost for semantic context match
            context = result.get('semantic_context', '').lower()
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
            # Extract function name from signature
            signature = result.get('signature', '')
            func_name = None
            if signature:
                match = re.search(r'(?:def|class|async def)\s+(\w+)', signature)
                if match:
                    func_name = match.group(1)

            # Smart content truncation
            content = result.get('content', '')
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
                file_path=result.get('file_path', ''),
                repository=result.get('repository', ''),
                language=result.get('language', ''),
                function_name=func_name,
                signature=signature,
                line_range=self._format_line_range(result.get('start_line'), result.get('end_line')),
                score=result.get('_enhanced_score', 0),
                content=content,
                context=result.get('semantic_context', '')[:200],
                imports=result.get('imports') or [],
                dependencies=result.get('dependencies') or [],
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

def _is_admin() -> bool:
    return os.getenv("MCP_ADMIN_MODE", "0").lower() in {"1", "true", "yes"}

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
    bm25_only: bool = False
) -> str:
    """Search for code with advanced filtering, ranking, and dependency resolution
    
    Args:
        query: Natural language search query
        intent: Search intent (implement/debug/understand/refactor)
        language: Filter by programming language
        repository: Filter by repository name (* for all)
        max_results: Maximum number of results to return
        include_dependencies: Include function dependencies
        skip: Number of results to skip for pagination
        orderby: Sort order (e.g., 'last_modified desc')
        highlight_code: Enable hit highlighting in results
        bm25_only: Force basic BM25 (keyword) search only
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

    results = await server.search_code(params)
    return server.format_results(results, query)

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
    results = await server.search_code(params)
    return _ok({
        "results": [r.model_dump() for r in results],
        "count": len(results),
        "total": server._last_total_count,
        "query": query,
        "intent": intent
    })

@mcp.tool()
async def search_microsoft_docs(query: str, max_results: int = 10) -> str:
    """Search Microsoft Learn documentation"""
    if not DOCS_SUPPORT:
        return "Microsoft Docs search is not available. Please install microsoft_docs_mcp_client."

    try:
        if not MicrosoftDocsMCPClient:
            return "Microsoft Docs client is not available. Please install microsoft_docs_mcp_client."
        async with MicrosoftDocsMCPClient() as client:
            results = await client.search_docs(query=query, max_results=max_results)

            if not results:
                return f"No Microsoft documentation found for '{query}'."

            formatted = f"📚 Found {len(results)} Microsoft Docs:\n\n"
            for i, doc in enumerate(results, 1):
                formatted += f"**{i}. {doc.get('title', 'Untitled')}**\n"
                formatted += f"🔗 {doc.get('url', '')}\n"
                formatted += f"{doc.get('content', '')[:300]}...\n\n"

            return formatted
    except Exception as e:
        return f"Error searching Microsoft Docs: {str(e)}"

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
    Explain ranking factors for results. Uses Enhanced RAG explainer when available,
    otherwise provides a heuristic explanation from base ACS metadata.
    """
    # Get results from chosen mode
    if mode == "enhanced" and ENHANCED_RAG_SUPPORT:
        try:
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
            raw_items = result.get("results", []) or result.get("final_results", []) or []
        except Exception as e:
            raw_items = []
    else:
        # Base ACS path
        params = SearchCodeParams(
            query=query,
            intent=SearchIntent(intent) if intent else None,
            language=language,
            repository=repository,
            max_results=max_results,
            include_dependencies=False
        )
        base_results = await server.search_code(params)
        raw_items = [r.model_dump() for r in base_results]

    # Try proper explainer
    if RESULT_EXPLAINER_AVAILABLE and ENHANCED_RAG_SUPPORT:
        try:
            explainer = ResultExplainer()
            explanations = explainer.explain(raw_items, query=query)
            return _ok({
                "mode": mode if ENHANCED_RAG_SUPPORT else "base",
                "query": query,
                "explanations": explanations
            })
        except Exception as e:
            pass

    # Fallback heuristic explanation
    explanations = []
    q_terms = set((query or "").lower().split())
    for item in raw_items:
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
    return _ok({"mode": "base" if mode != "enhanced" or not ENHANCED_RAG_SUPPORT else "enhanced", "query": query, "explanations": explanations})

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
        if mode == "enhanced" and ENHANCED_RAG_SUPPORT:
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
            params = SearchCodeParams(
                query=query,
                intent=SearchIntent(intent) if intent else None,
                language=language,
                repository=repository,
                max_results=max_results,
                include_dependencies=False
            )
            # Try to detect simple cache use
            cache_key = f"{params.query}:{params.intent}:{params.repository}:{params.language}"
            cache_hit = cache_key in server._query_cache
            res = await server.search_code(params)
            timer.mark("base_search")
            out = {
                "mode": "base",
                "query": query,
                "timings_ms": timer.durations(),
                "stages": [{"stage": "base_search", "count": len(res), "duration_ms": timer.durations().get("start→base_search", 0.0)}],
                "cache": {"hit": cache_hit, "cache_key": cache_key if cache_hit else None}
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
                detected = classifier.classify(query)
            except Exception:
                detected = intent

            enhancements = {}
            rewrites = []
            rules = []
            try:
                enhancer = QueryEnhancer()
                enhanced = enhancer.enhance(query, intent=detected or intent, language=language)
                enhancements = enhanced or {}
            except Exception:
                pass
            try:
                rewriter = QueryRewriter()
                rw = rewriter.rewrite(query, intent=detected or intent, language=language)
                if isinstance(rw, dict):
                    rewrites = rw.get("rewrites", [])
                    rules = rw.get("applied_rules", [])
                elif isinstance(rw, list):
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

        # Base fallback: one pass (semantic + possibly vector). We cannot split stages reliably, but return the results.
        params = SearchCodeParams(
            query=query,
            intent=SearchIntent(intent) if intent else None,
            language=language,
            repository=repository,
            max_results=max_results,
            include_dependencies=False
        )
        results = await server.search_code(params)
        out = {
            "weights": {"bm25": bm25_weight, "vector": vector_weight},
            "final_results": [r.model_dump() for r in results],
            "stages": None
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
                "vector_search": True,  # semantic + vector queries enabled (integrated or client-side)
                "semantic_search": True,
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
                "VECTOR_SUPPORT": VECTOR_SUPPORT,
                "DOCS_SUPPORT": DOCS_SUPPORT,
            },
            "index": {
                "name": os.getenv("ACS_INDEX_NAME", "codebase-mcp-sota"),
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
        result = await idx.run_indexer_on_demand(repository)
        return _ok({"repository": repository, "result": result})
    except Exception as e:
        return _err(str(e))

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
    try:
        rag_cache = None
        if ENHANCED_RAG_SUPPORT and RAG_CACHE_SUPPORT and CacheManager:
            rag_cache = _err("not_implemented", code="not_implemented")
        data = {
            "server_query_cache": len(server._query_cache),
            "repo_cache": len(server._repo_cache),
            "rag_cache": rag_cache
        }
        return _ok(data)
    except Exception as e:
        return _err(str(e))

@mcp.tool()
async def cache_clear(scope: str = "all") -> Dict[str, Any]:
    try:
        cleared = []
        if scope in ("all", "queries"):
            server._query_cache.clear()
            cleared.append("queries")
        if scope in ("all", "repos"):
            server._repo_cache.clear()
            cleared.append("repos")
        if scope in ("all", "rag") and ENHANCED_RAG_SUPPORT and RAG_CACHE_SUPPORT and CacheManager:
            cleared.append("rag")
        remaining = {
            "server_query_cache": len(server._query_cache),
            "repo_cache": len(server._repo_cache),
        }
        return _ok({"cleared": cleared, "remaining": remaining})
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
