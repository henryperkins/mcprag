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
from typing import Optional, List, Dict, Any, Sequence
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
        params: Dict[str, Any] = {
            "search_text": query,
            "query_type": "semantic",
            "semantic_configuration_name": "semantic-config",
            "count": True,  # Include total count
            "top": 50,  # Get more for better filtering
            "select": [
                "id", "repository", "file_path", "language", "content",
                "semantic_context", "signature", "imports",
                "dependencies", "chunk_type", "start_line", "end_line",
                "function_name", "class_name", "docstring"
            ]
        }

        # Add vector search using text-to-vector (index has vectorizers configured)
        if VECTORIZABLE_TEXT_QUERY_AVAILABLE and VectorizableTextQuery:
            try:
                vector_query = VectorizableTextQuery(
                    text=query,
                    k_nearest_neighbors=50,
                    fields="content_vector"
                )
                params["vector_queries"] = [vector_query]
            except Exception as e:
                # Fallback to client-side embedding if available
                if self.embedder:
                    try:
                        embedding = self.embedder.generate_embedding(query)
                        if embedding:
                            vector_query = VectorizedQuery(
                                vector=embedding,
                                k_nearest_neighbors=50,
                                fields="content_vector"
                            )
                            params["vector_queries"] = [vector_query]
                    except:
                        pass
        else:
            # Direct fallback to client-side embedding if VectorizableTextQuery not available
            if self.embedder:
                try:
                    embedding = self.embedder.generate_embedding(query)
                    if embedding:
                        vector_query = VectorizedQuery(
                            vector=embedding,
                            k_nearest_neighbors=50,
                            fields="content_vector"
                        )
                        params["vector_queries"] = [vector_query]
                except:
                    pass

        # Build filters
        filters = []
        if repo:
            filters.append(f"repository eq '{repo}'")
        if params.language:
            filters.append(f"language eq '{params.language}'")

        if filters:
            params["filter"] = " and ".join(filters)

        # Add pagination support
        if params.skip > 0:
            params["skip"] = params.skip

        # Add ordering support
        if params.orderby:
            params["orderby"] = params.orderby

        # Add hit highlighting
        if params.highlight_code:
            params["highlight"] = "content,semantic_context,docstring,function_name"
            params["highlightPreTag"] = "<mark>"
            params["highlightPostTag"] = "</mark>"

        return params

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
                imports=result.get('imports', []),
                dependencies=result.get('dependencies', []),
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

            formatted += f"\n```{result.language}\n{result.content}\n```\n\n"

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
    highlight_code: bool = False
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
        highlight_code=highlight_code
    )

    results = await server.search_code(params)
    return server.format_results(results, query)

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
                "vector_search": server.embedder is not None,
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
