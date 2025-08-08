"""Search-related MCP tools."""
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from ...utils.response_helpers import ok, err
from ._helpers import search_code_impl, search_microsoft_docs_impl

if TYPE_CHECKING:
    from ...server import MCPServer


def register_search_tools(mcp, server: "MCPServer") -> None:
    """Register search-related MCP tools."""

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
        exact_terms: Optional[List[str]] = None,
        disable_cache: bool = False,
        include_timings: bool = False,
        dependency_mode: str = "auto",
        detail_level: str = "full",  # full | compact | ultra
        snippet_lines: int = 0,  # 0 = no truncation, >0 = max lines in snippet
    ) -> Dict[str, Any]:
        """Search for code using enhanced RAG pipeline.

        Parameters affecting verbosity:
        detail_level: Return format of each result.
            - "full": original rich objects with code snippets (default)
            - "compact": small dict per result (file/match/context_type)
            - "ultra": single-line strings optimised for chat UIs

        snippet_lines: If >0 (and detail_level == "full") a smarter truncation
            algorithm is applied:
                1. Try the first highlight string ("@search.highlights" / "highlights").
                2. Otherwise use the first non-empty, non-comment line.
                3. Fallback to the first raw line.
            The selected headline is trimmed to 120 chars. When
            `snippet_lines` > 1, additional raw lines from the snippet are
            appended up to the requested count.
        """
        return await search_code_impl(
            server=server,
            query=query,
            intent=intent,
            language=language,
            repository=repository,
            max_results=max_results,
            include_dependencies=include_dependencies,
            skip=skip,
            orderby=orderby,
            highlight_code=highlight_code,
            bm25_only=bm25_only,
            exact_terms=exact_terms,
            disable_cache=disable_cache,
            include_timings=include_timings,
            dependency_mode=dependency_mode,
            detail_level=detail_level,
            snippet_lines=snippet_lines,
        )

    @mcp.tool()
    async def search_code_raw(
        query: str,
        intent: Optional[str] = None,
        language: Optional[str] = None,
        repository: Optional[str] = None,
        max_results: int = 10,
        include_dependencies: bool = False,
    ) -> Dict[str, Any]:
        """Raw search results without formatting."""
        result = await search_code_impl(
            server=server,
            query=query,
            intent=intent,
            language=language,
            repository=repository,
            max_results=max_results,
            include_dependencies=include_dependencies,
            skip=0,
            orderby=None,
            highlight_code=False,
            bm25_only=False,
            exact_terms=None,
            disable_cache=False,
            include_timings=False,
            dependency_mode="auto",
            detail_level="full",
            snippet_lines=0,
        )

        if result["ok"]:
            data = result["data"]
            return ok({
                "results": data["items"],
                "count": data["count"],
                "total": data["total"],
                "query": query,
                "intent": intent,
            })
        return result

    @mcp.tool()
    async def search_microsoft_docs(
        query: str, max_results: int = 10
    ) -> Dict[str, Any]:
        """Search Microsoft Learn documentation."""
        return await search_microsoft_docs_impl(query, max_results)
