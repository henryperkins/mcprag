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
from ..base import check_component
from .input_validation import (
    validate_all_search_params,
    validate_query,
    validate_max_results,
    validate_skip,
    validate_language,
    validate_detail_level,
    validate_orderby,
    validate_snippet_lines,
    validate_exact_terms,
)
from .data_consistency import (
    ensure_consistent_fields,
    ensure_consistent_response,
    fix_pagination_consistency,
    deduplicate_results,
)

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

    # Validate all parameters first
    is_valid, validation_errors, validated_params = validate_all_search_params(
        query=query,
        intent=intent,
        language=language,
        repository=repository,
        max_results=max_results,
        skip=skip,
        orderby=orderby,
        detail_level=detail_level,
        snippet_lines=snippet_lines,
        exact_terms=exact_terms
    )
    
    if not is_valid:
        return err(f"Validation failed: {validation_errors}")
    
    # Use validated parameters
    query = validated_params["query"]
    intent = validated_params["intent"]
    language = validated_params["language"]
    repository = validated_params["repository"]
    max_results = validated_params["max_results"]
    skip = validated_params["skip"]
    orderby = validated_params["orderby"]
    detail_level = validated_params["detail_level"]
    snippet_lines = validated_params["snippet_lines"]
    exact_terms = validated_params["exact_terms"]
    
    # Log validation warnings if any
    if validation_errors:
        logger.warning(f"Search parameter warnings: {validation_errors}")

    # Ensure async components are started
    await server.ensure_async_components_started()

    # Auto-extract exact terms if not provided
    if exact_terms is None and query:
        exact_terms = extract_exact_terms(query)

    try:

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
                server.search_client, query, language, repository, max_results, skip, orderby
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
        
        # Ensure data consistency for each item
        items = [ensure_consistent_fields(item) for item in items]

        # Deduplicate results
        items = deduplicate_results(items)
        
        # Fix pagination consistency
        items, total, has_more, next_skip_value = fix_pagination_consistency(
            items, skip, max_results, total
        )

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
            "has_more": has_more,
            "next_skip": next_skip_value,
        }
        if include_timings:
            response["timings_ms"] = {
                "total": took_ms
            }
        
        # Ensure overall response consistency
        response = ensure_consistent_response(response)
        
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
        # Ensure fields are consistent first
        from .data_consistency import ensure_consistent_fields
        e = ensure_consistent_fields(e)
        
        line_ref = f":{e['start_line']}" if e.get('start_line') else ""
        compact_entry = {
            "id": e.get("id", ""),
            "rank": i,
            "file": f"{e['file']}{line_ref}" if e.get('file') else "unknown",
            "repo": e.get("repository", ""),
            "language": e.get("language", ""),
            "lines": [e.get("start_line"), e.get("end_line")] if e.get("start_line") is not None else [None, None],
            "score": round(float(e.get("relevance", 0) or 0), 4),
            "match": e.get("function_name") or e.get("class_name") or first_highlight(e) or "Code match",
            "context_type": "implementation" if "def " in (e.get("content","")) or "class " in (e.get("content","")) else "general",
            "headline": headline_from_content(e.get("content", "")) or "No content"
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
    repository: Optional[str],
    max_results: int,
    skip: int,
    orderby: Optional[str],
) -> Tuple[List[Any], int]:
    """Perform basic Azure Search."""
    from enhanced_rag.ranking.filter_manager import FilterManager
    
    search_params = {
        "search_text": query,
        "top": max_results,
        "skip": skip,
        "include_total_count": True,
    }
    
    # Build filter using FilterManager for consistency
    filters = []
    
    # Repository filter
    repo_filter = FilterManager.repository(repository)
    if repo_filter:
        filters.append(repo_filter)
    
    # Language filter  
    lang_filter = FilterManager.language(language)
    if lang_filter:
        filters.append(lang_filter)
    
    # Combine filters with AND
    if filters:
        search_params["filter"] = " and ".join(filters)
    
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
        # For now, return a helpful message indicating the service is temporarily unavailable
        # TODO: Implement proper MCP client for Microsoft Learn MCP server
        # According to https://learn.microsoft.com/en-us/training/support/mcp-developer-reference
        # Microsoft Docs MCP requires an agent framework, not direct API calls
        
        return ok(
            {
                "query": query,
                "count": 0,
                "results": [],
                "status": "unavailable",
                "message": (
                    "Microsoft Docs MCP search is temporarily unavailable. "
                    "Microsoft Learn MCP server requires an agent framework integration "
                    "that is currently being implemented. Use web search or the Microsoft "
                    "Learn website directly for now."
                ),
                "alternative": "Try using the WebSearch tool or browse https://learn.microsoft.com directly",
                "formatted": f"Microsoft Docs search for '{query}' is temporarily unavailable. Use WebSearch tool instead.",
            }
        )

    except Exception as e:
        logger.exception("Error in Microsoft Docs search")
        return err(f"Microsoft Docs search error: {str(e)}")


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
