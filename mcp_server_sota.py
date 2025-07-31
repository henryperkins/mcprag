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
from typing import Optional, List, Dict, Any, Sequence
from pathlib import Path
from datetime import datetime
from enum import Enum

# Core imports
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Azure imports
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.core.credentials import AzureKeyCredential

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
    from vector_embeddings import VectorEmbedder
    VECTOR_SUPPORT = True
except ImportError:
    VectorEmbedder = None
    VECTOR_SUPPORT = False

try:
    from microsoft_docs_mcp_client import MicrosoftDocsMCPClient
    DOCS_SUPPORT = True
except ImportError:
    MicrosoftDocsMCPClient = None
    DOCS_SUPPORT = False

load_dotenv()

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

    def _initialize_clients(self):
        """Initialize all service clients"""
        endpoint = os.getenv("ACS_ENDPOINT")
        admin_key = os.getenv("ACS_ADMIN_KEY")

        if not endpoint or not admin_key:
            raise ValueError("Missing Azure Search credentials")

        self.search_client = SearchClient(
            endpoint=endpoint,
            index_name="codebase-mcp-sota",
            credential=AzureKeyCredential(admin_key)
        )

        # Initialize vector support
        self.embedder = None
        if VECTOR_SUPPORT and os.getenv("AZURE_OPENAI_KEY"):
            try:
                self.embedder = VectorEmbedder()
                print("✅ Vector search enabled")
            except Exception as e:
                print(f"⚠️  Vector search unavailable: {e}")

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
        search_params = self._build_search_params(enhanced_query, repo, params.language)

        # Execute search
        raw_results = list(self.search_client.search(**search_params))

        # Filter and rank results
        results = self._filter_and_rank_results(raw_results, params.query, repo)

        # Convert to typed results
        search_results = self._convert_to_search_results(results)

        # Resolve dependencies if requested
        if params.include_dependencies and params.intent == SearchIntent.IMPLEMENT:
            search_results = await self._resolve_dependencies(search_results)

        # Cache results
        self._query_cache[cache_key] = search_results

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

    def _build_search_params(self, query: str, repo: Optional[str], language: Optional[str]) -> Dict:
        """Build optimized search parameters"""
        # Note: vector_queries expects a Sequence[VectorizedQuery] at runtime.
        # Some type checkers flag list[VectorizedQuery] for invariance; we use Sequence for compatibility.
        params: Dict[str, Any] = {
            "search_text": query,
            "query_type": "semantic",
            "semantic_configuration_name": "mcp-semantic",
            "top": 50,  # Get more for better filtering
            "select": [
                "id", "repo_name", "file_path", "language", "code_chunk",
                "semantic_context", "function_signature", "imports_used",
                "calls_functions", "chunk_type", "line_range"
            ]
        }

        # Add vector search if available
        if self.embedder:
            try:
                embedding = self.embedder.generate_embedding(query)
                if embedding:
                    # Use a Sequence[VectorizedQuery] to satisfy typing tools while matching SDK runtime behavior.
                    vector_query = VectorizedQuery(
                        vector=embedding,
                        k_nearest_neighbors=50,
                        fields="code_vector"
                    )
                    # Provide a tuple (Sequence) to satisfy type-checkers and the SDK.
                    params["vector_queries"] = (vector_query,)
            except:
                pass

        # Build filters
        filters = []
        if repo:
            filters.append(f"repo_name eq '{repo}'")
        if language:
            filters.append(f"language eq '{language}'")

        if filters:
            params["filter"] = " and ".join(filters)

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
            if repo and result.get('repo_name') == repo:
                score *= 2.0

            # Boost for function name match
            func_name = result.get('function_signature', '').lower()
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
            code_length = len(result.get('code_chunk', ''))
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
            signature = result.get('function_signature', '')
            func_name = None
            if signature:
                match = re.search(r'(?:def|class|async def)\s+(\w+)', signature)
                if match:
                    func_name = match.group(1)

            # Smart content truncation
            content = result.get('code_chunk', '')
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
                repository=result.get('repo_name', ''),
                language=result.get('language', ''),
                function_name=func_name,
                signature=signature,
                line_range=result.get('line_range'),
                score=result.get('_enhanced_score', 0),
                content=content,
                context=result.get('semantic_context', '')[:200],
                imports=result.get('imports_used', []),
                dependencies=result.get('calls_functions', [])
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

        formatted = f"🔍 Found {len(results)} relevant results:\n\n"

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
    include_dependencies: bool = False
) -> str:
    """Search for code with advanced filtering, ranking, and dependency resolution"""

    params = SearchCodeParams(
        query=query,
        intent=SearchIntent(intent) if intent else None,
        language=language,
        repository=repository,
        max_results=max_results,
        include_dependencies=include_dependencies
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

@mcp.resource()
async def list_repositories() -> str:
    """List all indexed repositories with statistics"""
    try:
        results = server.search_client.search(
            search_text="*",
            facets=["repo_name"],
            top=0
        )

        facets = results.get_facets()
        repos = (facets or {}).get("repo_name", [])

        if not repos:
            return json.dumps({"repositories": [], "count": 0})

        repo_list = [{"name": r['value'], "documents": r['count']} for r in repos]
        current = server._resolve_repository(None)

        return json.dumps({
            "repositories": repo_list,
            "count": len(repo_list),
            "current": current,
            "timestamp": datetime.utcnow().isoformat()
        }, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.resource()
async def get_statistics() -> str:
    """Get comprehensive search statistics"""
    try:
        doc_count = server.search_client.get_document_count()

        return json.dumps({
            "total_documents": doc_count,
            "index_name": "codebase-mcp-sota",
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
            "timestamp": datetime.utcnow().isoformat()
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
# Main Entry Point with Multiple Modes
# ============================================================================

if __name__ == "__main__":
    if "--rpc" in sys.argv:
        # JSON-RPC mode for MCP protocol
        async def run_rpc():
            while True:
                try:
                    line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
                    if not line:
                        break
                    request = json.loads(line.strip())

                    # Basic RPC handler (simplified)
                    method = request.get("method")
                    if method == "initialize":
                        response = {
                            "jsonrpc": "2.0",
                            "id": request.get("id"),
                            "result": {
                                "protocolVersion": "2024-11-05",
                                "capabilities": {"tools": {"listChanged": False}},
                                "serverInfo": {"name": server.name, "version": server.version}
                            }
                        }
                    else:
                        response = {"jsonrpc": "2.0", "id": request.get("id"), "error": {"code": -32601, "message": "Method not found"}}

                    print(json.dumps(response))
                    sys.stdout.flush()
                except Exception as e:
                    print(json.dumps({"jsonrpc": "2.0", "error": {"code": -32603, "message": str(e)}}))
                    sys.stdout.flush()

        asyncio.run(run_rpc())
    elif "--api" in sys.argv:
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
            return {"results": [r.dict() for r in results]}

        uvicorn.run(app, host="0.0.0.0", port=8001)
    else:
        # Default: MCP SDK mode
        mcp.run()
