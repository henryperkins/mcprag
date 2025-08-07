"""Search implementation helpers for MCP tools."""

import time
import asyncio
import logging
import difflib
from typing import Optional, List, Dict, Any, Tuple, TYPE_CHECKING

from .formatting import (
    sanitize_text,
    normalize_items,
    first_highlight,
    headline_from_content,
    extract_exact_terms,
    truncate_snippets,
)
from .validation import check_component

if TYPE_CHECKING:
    from ...server import MCPServer
    from enhanced_rag.core.models import SearchIntent, SearchResult, SearchQuery

logger = logging.getLogger(__name__)


async def search_code_impl(
    server: "MCPServer",
    query: str,
    intent: Optional[str],
    language: Optional[str],
    repository: Optional[str],
    max_results: int,
    include_dependencies: bool,
    skip: int,
    orderby: Optional[str],
    highlight_code: bool,
    bm25_only: bool,
    exact_terms: Optional[List[str]],
    disable_cache: bool,
    include_timings: bool,
    dependency_mode: str,
    detail_level: str,
    snippet_lines: int,
) -> Dict[str, Any]:
    """Implementation of search_code functionality."""
    from ....utils.response_helpers import ok, err
    
    start_time = time.time()

    # Ensure async components are started
    await server.ensure_async_components_started()

    # Auto-extract exact terms if not provided
    if exact_terms is None and query:
        exact_terms = extract_exact_terms(query)

    try:
        # Normalize detail level
        detail_level = (detail_level or "full").lower().strip()
        if detail_level not in {"full", "compact", "ultra"}:
            return err("detail_level must be one of 'full', 'compact', or 'ultra'")

        # Use enhanced search if available
        if server.enhanced_search and not bm25_only:
            # Add null check for type checker
            if server.enhanced_search is None:
                return err("Enhanced search component is not initialized")
            result = await server.enhanced_search.search(
                query=query,
                intent=intent,
                language=language,
                repository=repository,
                max_results=max_results,
                include_dependencies=include_dependencies,
                generate_response=False,
                skip=skip,
                orderby=orderby,
                highlight_code=highlight_code,
                exact_terms=exact_terms,
                dependency_mode=dependency_mode,
            )

            # Check if enhanced search returned an error
            if "error" in result:
                return err(result["error"])

            # Pick correct list of items based on requested detail level
            items = _get_items_by_detail_level(result, detail_level)
            # Different versions of the enhanced_search backend expose total
            # hits under either "total_count" or "total" – fall back to the
            # length of the returned collection if neither is present.
            total = result.get("total_count", result.get("total", len(items)))

        # Fallback to basic Azure Search
        elif server.search_client:
            # Add null check for type checker
            if server.search_client is None:
                return err("Search client is not initialized")
            items, total = await _basic_search(
                server.search_client, query, language, max_results, skip, orderby
            )
        else:
            return err("No search backend available")

        took_ms = (time.time() - start_time) * 1000

        backend = "enhanced" if server.enhanced_search and not bm25_only else "basic"

        # Guard: if ultra format and items are already strings, pass through
        if detail_level == "ultra" and items and isinstance(items[0], str):
            response = {
                "items": items,
                "count": len(items),
                "total": total,
                "took_ms": took_ms,
                "query": query,
                "applied_exact_terms": bool(exact_terms),
                "backend": backend,
            }
            if disable_cache:
                response["cache_disabled"] = True
            if include_timings:
                response["timings_ms"] = {"total": took_ms}
            return ok(response)

        # Normalize to a stable schema for presentation
        items = normalize_items(items)

        # Optional dedupe by (file, start_line)
        _seen = {}
        deduped = []
        for e in items:
            key = (e["file"], e.get("start_line"))
            if key not in _seen or e.get("relevance", 0) > _seen[key].get("relevance", 0):
                _seen[key] = e
        deduped = list(_seen.values())
        items = deduped

        # Apply snippet truncation only for full
        if snippet_lines > 0 and detail_level == "full":
            truncate_snippets(items, snippet_lines)

        # Build compact and ultra lists
        results_compact = _build_compact(items)
        results_ultra = _build_ultra(items)

        response = {
            "items": items if detail_level == "full" else (results_compact if detail_level == "compact" else results_ultra),
            "count": len(items),
            "total": total,
            "took_ms": took_ms,
            "query": query,
            "applied_exact_terms": bool(exact_terms),
            "exact_terms": exact_terms,
            "detail_level": detail_level,
            "backend": backend,
            "has_more": skip + len(items) < total,
            "next_skip": skip + len(items) if skip + len(items) < total else None,
        }
        if include_timings:
            response["timings_ms"] = {
                "total": took_ms
            }
        return ok(response)

    except Exception as e:
        return err(str(e))


def _get_items_by_detail_level(result: Dict[str, Any], detail_level: str) -> List[Any]:
    """Get items based on detail level."""
    # The Enhanced RAG search service has evolved its response schema a few
    # times.  Older versions used keys like "results", newer ones prefer
    # "items" while also exposing format-specific variants such as
    # "results_compact".  To stay compatible we fall back through the possible
    # spellings instead of assuming one concrete field exists.  This guarantees
    # that we always return the underlying list of hits, even when the backend
    # version changes, and prevents the empty-result symptom that forced users
    # to switch to the bm25_only fallback.

    # Helper that checks a sequence of candidate keys and returns the first
    # non-empty value (or an empty list as final default).
    def _first_available(keys):
        for k in keys:
            if k in result and result[k]:
                return result[k]
        return []

    if detail_level == "compact":
        return _first_available(["results_compact", "items_compact", "results", "items"])
    elif detail_level == "ultra":
        return _first_available([
            "results_ultra_compact",
            "items_ultra_compact",
            "results_compact",
            "items_compact",
            "results",
            "items",
        ])
    else:  # full
        return _first_available(["results", "items"])


def _build_compact(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Build compact result format."""
    out = []
    for i, e in enumerate(entries, start=1):
        line_ref = f":{e['start_line']}" if e.get('start_line') else ""
        compact_entry = {
            "id": e.get("id"),
            "rank": i,
            "file": f"{e['file']}{line_ref}",
            "repo": e.get("repository"),
            "language": e.get("language"),
            "lines": [e.get("start_line"), e.get("end_line")],
            "score": round(float(e.get("relevance", 0) or 0), 4),
            "match": e.get("function_name") or e.get("class_name") or first_highlight(e) or "Code match",
            "context_type": "implementation" if "def " in (e.get("content","")) or "class " in (e.get("content","")) else "general",
            "headline": headline_from_content(e.get("content", ""))
        }

        # Add highlight information if available
        if e.get("highlights"):
            for field, hls in e.get("highlights", {}).items():
                if hls:
                    compact_entry["why"] = hls[0][:120]
                    compact_entry["why_field"] = field
                    break
        else:
            # Fallback to first highlight
            first_hl = first_highlight(e)
            if first_hl:
                compact_entry["why"] = first_hl[:120]

        out.append(compact_entry)
    return out


def _build_ultra(entries: List[Dict[str, Any]]) -> List[str]:
    """Build ultra-compact result format."""
    out = []
    for i, e in enumerate(entries, start=1):
        line_ref = f":{e['start_line']}" if e.get('start_line') else ""
        why = first_highlight(e) or "Match"
        head = headline_from_content(e.get("content", ""))
        lang = e.get('language', '?')
        score = e.get('relevance', 0)
        out.append(f"#{i} {e['file']}{line_ref} [{lang}] score={score:.3f} | {why} || {head}")
    return out


async def _basic_search(
    search_client: Any,
    query: str,
    language: Optional[str],
    max_results: int,
    skip: int,
    orderby: Optional[str],
) -> Tuple[List[Any], int]:
    """Perform basic Azure Search."""
    search_params = {
        "search_text": query,
        "top": max_results,
        "skip": skip,
        "include_total_count": True,
    }
    if language:
        search_params["filter"] = f"language eq '{language}'"
    if orderby:
        search_params["orderby"] = orderby

    loop = asyncio.get_running_loop()

    def _exec_search(sc, sp):
        resp = sc.search(**sp)
        items = list(resp)
        total = resp.get_count() if hasattr(resp, "get_count") else len(items)
        return items, total

    items, total = await loop.run_in_executor(None, lambda: _exec_search(search_client, search_params))
    return items, total


async def search_microsoft_docs_impl(query: str, max_results: int) -> Dict[str, Any]:
    """Implementation of Microsoft Docs search."""
    from ....utils.response_helpers import ok, err
    
    try:
        # Try to import the client
        try:
            from microsoft_docs_mcp_client import MicrosoftDocsMCPClient
        except ImportError:
            return err("Microsoft Docs MCP client not installed")

        async with MicrosoftDocsMCPClient() as client:
            results = await client.search_docs(query=query, max_results=max_results)

        if not results:
            return ok(
                {
                    "query": query,
                    "count": 0,
                    "results": [],
                    "formatted": f"No Microsoft documentation found for '{query}'.",
                }
            )

        formatted_results = []
        formatted_lines = [f"📚 Found {len(results)} Microsoft Docs:\n"]

        for i, doc in enumerate(results, 1):
            formatted_results.append(
                {
                    "title": doc.get("title", "Untitled"),
                    "url": doc.get("url", ""),
                    "snippet": doc.get("content", "")[:300],
                }
            )

            formatted_lines.append(
                f"{i}. {doc.get('title', 'Untitled')}\n"
                f"   {doc.get('url', '')}\n"
                f"   {doc.get('content', '')[:300]}...\n"
            )

        return ok(
            {
                "query": query,
                "count": len(results),
                "results": formatted_results,
                "formatted": "\n".join(formatted_lines),
            }
        )

    except Exception as e:
        return err(f"Microsoft Docs search unavailable: {str(e)}")


async def explain_ranking_impl(
    server: "MCPServer",
    query: str,
    mode: str,
    max_results: int,
    intent: Optional[str],
    language: Optional[str],
    repository: Optional[str],
) -> Dict[str, Any]:
    """Implementation of ranking explanation."""
    from ....utils.response_helpers import ok, err
    
    if mode == "enhanced" and server.result_explainer:
        # Add null check for type checker
        if server.result_explainer is None:
            return err("Result explainer component is not initialized")
        try:
            # Get search results first
            search_result = await search_code_impl(
                server=server,
                query=query,
                intent=intent,
                language=language,
                repository=repository,
                max_results=max_results,
                include_dependencies=False,
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

            if not search_result["ok"]:
                return search_result

            # Import at runtime if not available
            global SearchResult, SearchQuery, SearchIntent
            if ('SearchResult' not in globals() or SearchResult is None or
                'SearchQuery' not in globals() or SearchQuery is None or
                'SearchIntent' not in globals() or SearchIntent is None):
                from enhanced_rag.core.models import SearchResult, SearchQuery, SearchIntent

            results = search_result["data"]["items"]
            explanations = []

            for result in results:
                # Convert dict to SearchResult
                search_result_obj = SearchResult(
                    id=result.get("id", ""),
                    score=result.get("relevance", 0.0),
                    file_path=result.get("file", ""),
                    repository=result.get("repository", ""),
                    function_name=result.get("function_name"),
                    class_name=result.get("class_name"),
                    code_snippet=result.get("content", ""),
                    language=result.get("language", ""),
                    highlights=result.get("highlights", {}),
                    dependencies=result.get("dependencies", []),
                )

                # Create SearchQuery object
                search_intent = SearchIntent(intent) if intent else None
                search_query = SearchQuery(
                    query=query,
                    intent=search_intent,
                    current_file=None,
                    language=language,
                    user_id=None,
                )

                explanation = await server.result_explainer.explain_ranking(
                    result=search_result_obj, query=search_query, context=None
                )
                explanations.append(explanation)

            return ok({"mode": mode, "query": query, "explanations": explanations})
        except Exception as e:
            return err(str(e))
    else:
        return err("Ranking explanation not available")