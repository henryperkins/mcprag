"""
MCP tool definitions.

Thin wrappers around enhanced_rag functionality exposed as MCP tools.
"""

# flake8: max-line-length = 120
from typing import Optional, List, Dict, Any, TYPE_CHECKING
import re
import time
import asyncio
import logging
import difflib

# Fix: Move all imports to the top
from ..utils.response_helpers import ok, err
from ..config import Config

if TYPE_CHECKING:
    from ..server import MCPServer

logger = logging.getLogger(__name__)


def register_tools(mcp: Any, server: "MCPServer") -> None:
    """Register all MCP tools."""

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
        # Refactored: Extracted into separate function
        return await _search_code_impl(
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
        result = await search_code(
            query=query,
            intent=intent,
            language=language,
            repository=repository,
            max_results=max_results,
            include_dependencies=include_dependencies,
        )

        if result["ok"]:
            data = result["data"]
            return ok(
                {
                    "results": data["items"],
                    "count": data["count"],
                    "total": data["total"],
                    "query": query,
                    "intent": intent,
                }
            )
        return result

    @mcp.tool()
    async def search_microsoft_docs(
        query: str, max_results: int = 10
    ) -> Dict[str, Any]:
        """Search Microsoft Learn documentation."""
        return await _search_microsoft_docs_impl(query, max_results)

    @mcp.tool()
    async def generate_code(
        description: str,
        language: str = "python",
        context_file: Optional[str] = None,
        style_guide: Optional[str] = None,
        include_tests: bool = False,
        workspace_root: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate code using enhanced RAG pipeline."""
        if server.code_gen is None or not _check_component(
            server.code_gen, "Code generation"
        ):
            return err("Code generation not available")

        try:
            result = await server.code_gen.generate_code(
                description=description,
                language=language,
                context_file=context_file,
                style_guide=style_guide,
                include_tests=include_tests,
                workspace_root=workspace_root,
            )
            return ok(result)
        except Exception as e:
            return err(str(e))

    @mcp.tool()
    async def analyze_context(
        file_path: str,
        include_dependencies: bool = True,
        depth: int = 2,
        include_imports: bool = True,
        include_git_history: bool = False,
    ) -> Dict[str, Any]:
        """Analyze file context using enhanced RAG."""
        if not _check_component(server.context_aware, "Context analysis"):
            return err("Context analysis not available")

        # Explicit null check for type checker
        if server.context_aware is None:
            return err("Context analysis component is not initialized")

        try:
            result = await server.context_aware.analyze_context(
                file_path=file_path,
                include_dependencies=include_dependencies,
                depth=depth,
                include_imports=include_imports,
                include_git_history=include_git_history,
            )
            return ok(result)
        except Exception as e:
            return err(str(e))

    @mcp.tool()
    async def explain_ranking(
        query: str,
        mode: str = "enhanced",
        max_results: int = 10,
        intent: Optional[str] = None,
        language: Optional[str] = None,
        repository: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Explain ranking factors for results."""
        return await _explain_ranking_impl(
            server=server,
            query=query,
            mode=mode,
            max_results=max_results,
            intent=intent,
            language=language,
            repository=repository,
        )

    @mcp.tool()
    async def preview_query_processing(
        query: str,
        intent: Optional[str] = None,
        language: Optional[str] = None,
        repository: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Show intent classification and query enhancements."""
        try:
            response = {
                "input_query": query,
                "detected_intent": None,
                "enhancements": {},
                "rewritten_queries": [],
                "applied_rules": [],
            }

            detected = None  # ensure variable defined

            if server.intent_classifier:
                detected = await server.intent_classifier.classify_intent(query)
                response["detected_intent"] = (
                    detected.value if hasattr(detected, "value") else str(detected)
                )

            # Skip query enhancement if no context is available
            # The query enhancer requires a CodeContext object
            response["enhancements"] = {
                "note": "Query enhancement requires file context",
                "skipped": True,
            }

            if server.query_rewriter:
                # lazy local import to avoid circular imports
                from enhanced_rag.core.models import SearchIntent

                intent_for_rewrite: Optional[SearchIntent] = None

                # Prefer classifier result
                if detected:
                    intent_for_rewrite = detected
                # Fallback: convert supplied string to enum
                elif intent:
                    try:
                        intent_for_rewrite = SearchIntent(intent)
                    except ValueError:
                        # ignore invalid intent strings
                        intent_for_rewrite = None

                rewrites = await server.query_rewriter.rewrite_query(
                    query, intent=intent_for_rewrite
                )
                response["rewritten_queries"] = (
                    rewrites if isinstance(rewrites, list) else [rewrites]
                )

            return ok(response)
        except Exception as e:
            return err(str(e))

    @mcp.tool()
    async def submit_feedback(
        target_id: str,
        kind: str,
        rating: int,
        notes: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Submit user feedback."""
        # Fix: Add validation
        if not isinstance(rating, int) or rating < 1 or rating > 5:
            return err("Rating must be an integer between 1 and 5")

        if kind not in {"search", "code_generation", "context_analysis", "general"}:
            return err(f"Invalid feedback kind: {kind}")

        if not _check_component(server.feedback_collector, "Feedback collection"):
            return err("Feedback collection not available")

        # Explicit null check for type checker
        if server.feedback_collector is None:
            return err("Feedback collector component is not initialized")

        try:
            await server.feedback_collector.record_explicit_feedback(
                interaction_id=target_id, satisfaction=rating, comment=notes
            )
            return ok({"stored": True})
        except Exception as e:
            return err(str(e))

    @mcp.tool()
    async def track_search_click(
        query_id: str, doc_id: str, rank: int, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Track user click on search result."""
        return await _track_interaction(
            server=server,
            interaction_type="click",
            query_id=query_id,
            doc_id=doc_id,
            rank=rank,
            context=context,
        )

    @mcp.tool()
    async def track_search_outcome(
        query_id: str,
        outcome: str,
        score: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Track search outcome (success/failure)."""
        return await _track_interaction(
            server=server,
            interaction_type="outcome",
            query_id=query_id,
            outcome=outcome,
            score=score,
            context=context,
        )

    @mcp.tool()
    async def cache_stats() -> Dict[str, Any]:
        """Get cache statistics."""
        if not _check_component(server.cache_manager, "Cache manager"):
            return err("Cache manager not available")

        # Explicit null check for type checker
        if server.cache_manager is None:
            return err("Cache manager component is not initialized")

        try:
            stats = await server.cache_manager.get_stats()
            return ok({"cache_stats": stats})
        except Exception as e:
            return err(str(e))

    @mcp.tool()
    async def cache_clear(
        scope: str = "all", pattern: Optional[str] = None
    ) -> Dict[str, Any]:
        """Clear cache."""
        # Fix: Add validation
        if scope not in {"all", "pattern"}:
            return err(f"Invalid scope: {scope}. Must be 'all' or 'pattern'")

        if scope == "pattern" and not pattern:
            return err("Pattern required when scope is 'pattern'")

        if not _check_component(server.cache_manager, "Cache manager"):
            return err("Cache manager not available")

        # Explicit null check for type checker
        if server.cache_manager is None:
            return err("Cache manager component is not initialized")

        try:
            if scope == "all":
                await server.cache_manager.clear()
            elif pattern:
                # Check if clear_pattern method exists
                if hasattr(server.cache_manager, "clear_pattern"):
                    # Use getattr to safely call the method
                    clear_method = getattr(server.cache_manager, "clear_pattern")
                    await clear_method(pattern)
                else:
                    return err("Cache pattern clearing not supported")

            stats = await server.cache_manager.get_stats()
            return ok({"cleared": True, "cache_stats": stats})
        except Exception as e:
            return err(str(e))

    # Admin tools with better security
    @mcp.tool()
    async def index_rebuild(
        repository: Optional[str] = None, *, confirm: bool = False
    ) -> Dict[str, Any]:
        """Rebuild (re-run) the Azure Search indexer.

        The tool is potentially destructive: it triggers a full crawl
        of the configured data-source and may overwrite existing vector
        data.  Therefore a confirmation step is required.

        Pass `confirm=true` to proceed.
        """
        # Fix: Check admin mode
        if not Config.ADMIN_MODE:
            return err("Admin mode not enabled")

        if not confirm:
            return ok(
                {
                    "confirmation_required": True,
                    "message": f"Rebuild indexer for '{repository or '[default]'}'? "
                    "Call again with confirm=true to proceed.",
                }
            )

        if not _check_component(server.indexer_automation, "Indexer automation"):
            return err("Indexer automation not available")

        # Explicit null check for type checker
        if server.indexer_automation is None:
            return err("Indexer automation component is not initialized")

        # Ensure repository is not None for the API calls
        repo_name = repository or "default"

        try:
            if hasattr(server.indexer_automation, "reset_and_run_indexer"):
                result = await server.indexer_automation.reset_and_run_indexer(
                    repo_name, wait_for_completion=False
                )
            elif hasattr(server.indexer_automation, "ops") and hasattr(server.indexer_automation.ops, "run_indexer"):
                await server.indexer_automation.ops.run_indexer(repo_name)
                result = {"status": "started", "indexer_name": repo_name}
            else:
                return err("Indexer method not found")

            return ok({"repository": repository, "result": result})
        except Exception as e:
            return err(str(e))

    @mcp.tool()
    async def github_index_repo(
        repo: str,
        branch: Optional[str] = None,
        *,
        mode: str = "full",
        confirm: bool = False,
    ) -> Dict[str, Any]:
        """Index a GitHub repository.

        Requires confirmation. Call once without `confirm` to get the
        prompt, again with `confirm=true` to execute.
        """
        # Fix: Check admin mode
        if not Config.ADMIN_MODE:
            return err("Admin mode not enabled")

        if not confirm:
            return ok(
                {
                    "confirmation_required": True,
                    "message": f"Index GitHub repository '{repo}' (branch: {branch or '[default]'})? "
                    "Call again with confirm=true to proceed.",
                }
            )

        if not _check_component(server.remote_indexer, "GitHub indexing"):
            return err("GitHub indexing not available")

        # Explicit null check for type checker
        if server.remote_indexer is None:
            return err("Remote indexer component is not initialized")

        try:
            owner, repo_name = repo.split("/")

            # Ensure branch is not None for the API call
            ref_branch = branch or "main"

            # Run sync method in executor
            loop = asyncio.get_running_loop()

            # Use getattr to safely access the method
            if hasattr(server.remote_indexer, "index_remote_repository"):
                index_method = getattr(server.remote_indexer, "index_remote_repository")
                result = await loop.run_in_executor(
                    None, lambda: index_method(owner, repo_name, ref=ref_branch)
                )
            else:
                return err("Remote indexer method not available")

            return ok({"repo": repo, "branch": branch, "mode": mode, "result": result})
        except Exception as e:
            return err(str(e))


# Helper functions to reduce duplication and improve organization
import re as _re
_TAG_RE = _re.compile(r"<[^>]+>")


def _sanitize_text(s: str) -> str:
    return _TAG_RE.sub("", (s or "")).replace("\xa0", " ").strip()


def _sanitize_highlights(hl: Any) -> Dict[str, List[str]]:
    if not isinstance(hl, dict):
        return {}
    return {
        k: [
            _sanitize_text(x)[:200]
            for x in (v or [])
            if isinstance(x, str) and x.strip()
        ]
        for k, v in hl.items()
    }


def _normalize_items(items: List[Any]) -> List[Dict[str, Any]]:
    normalized = []
    for it in items:
        d = it if isinstance(it, dict) else getattr(it, "__dict__", {}) or {}
        file_path = d.get("file") or d.get("file_path") or d.get("path") or ""
        content = d.get("content") or d.get("code_snippet") or d.get("snippet") or ""
        normalized.append({
            "id": d.get("id") or d.get("@search.documentId") or f"{file_path}:{d.get('start_line') or ''}",
            "file": file_path,
            "repository": d.get("repository") or "",
            "language": d.get("language") or "",
            "content": content,
            "highlights": _sanitize_highlights(d.get("highlights") or d.get("@search.highlights") or {}),
            "relevance": d.get("relevance") or d.get("score") or d.get("@search.score") or 0.0,
            "start_line": d.get("start_line"),
            "end_line": d.get("end_line"),
            "function_name": d.get("function_name"),
            "class_name": d.get("class_name"),
        })
    return normalized


def _first_highlight(entry: Dict[str, Any]) -> Optional[str]:
    hl = entry.get("highlights") or {}
    for _, lst in hl.items():
        if lst:
            return lst[0]
    return None


def _headline_from_content(content: str) -> str:
    if not content:
        return "No content"
    for ln in content.splitlines():
        t = _sanitize_text(ln)
        if t and not t.startswith(("#", "//", "/*", "*", "*/", "<!--")) and not t.endswith("-->"):
            return t[:120] + ("…" if len(t) > 120 else "")
    return _sanitize_text(content.splitlines()[0])[:120]


def _check_component(component: Any, name: str) -> bool:
    """Check if a component is available and log if not."""
    if not component:
        logger.debug(f"{name} component not available")
        return False
    return True


def _extract_exact_terms(query: str) -> List[str]:
    """Extract exact terms from query."""
    terms = []

    # Quoted phrases
    quoted = re.findall(r'"([^"]+)"|\'([^\']+)\'', query)
    terms.extend([t for pair in quoted for t in pair if t])

    # Numbers
    numbers = re.findall(r"(?<![\w])(\d+(?:\.\d+)+|\d{2,})(?![\w.])", query)
    terms.extend(numbers)

    # Function calls
    functions = re.findall(r"(\w+)\s*\(", query)
    terms.extend(functions)

    # Deduplicate
    seen = set()
    return [t for t in terms if not (t in seen or seen.add(t))]


async def _search_code_impl(
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
    start_time = time.time()

    # Ensure async components are started
    await server.ensure_async_components_started()

    # Auto-extract exact terms if not provided
    if exact_terms is None and query:
        exact_terms = _extract_exact_terms(query)

    try:
        # Normalize detail level
        detail_level = (detail_level or "full").lower().strip()
        if detail_level not in {"full", "compact", "ultra"}:
            return err("detail_level must be one of 'full', 'compact', or 'ultra'")

        # Use enhanced search if available
        if server.enhanced_search and not bm25_only:
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
            total = result.get("total_count", len(items))

            # Skip tracking info for now to avoid Pydantic model issues
            # _add_tracking_info(items)

        # Fallback to basic Azure Search
        elif server.search_client:
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
        items = _normalize_items(items)

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
            _truncate_snippets(items, snippet_lines)

        # Build compact and ultra lists
        def _build_compact(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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
                    "match": e.get("function_name") or e.get("class_name") or _first_highlight(e) or "Code match",
                    "context_type": "implementation" if "def " in (e.get("content","")) or "class " in (e.get("content","")) else "general",
                    "headline": _headline_from_content(e.get("content", ""))
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
                    first_hl = _first_highlight(e)
                    if first_hl:
                        compact_entry["why"] = first_hl[:120]

                out.append(compact_entry)
            return out

        def _build_ultra(entries: List[Dict[str, Any]]) -> List[str]:
            out = []
            for i, e in enumerate(entries, start=1):
                line_ref = f":{e['start_line']}" if e.get('start_line') else ""
                why = _first_highlight(e) or "Match"
                head = _headline_from_content(e.get("content", ""))
                lang = e.get('language', '?')
                score = e.get('relevance', 0)
                out.append(f"#{i} {e['file']}{line_ref} [{lang}] score={score:.3f} | {why} || {head}")
            return out

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
    if detail_level == "compact":
        return result.get("results_compact", result.get("results", []))
    elif detail_level == "ultra":
        return result.get("results_ultra_compact", result.get("results", []))
    else:
        return result.get("results", [])


def _add_tracking_info(items: List[Any]) -> None:
    """Add tracking information to items."""
    for i, item in enumerate(items):
        # Handle both dict and object types
        if isinstance(item, dict):
            # For dictionaries, add keys directly
            item["query_id"] = None
            # Only set result_position if not already set
            if "result_position" not in item or item["result_position"] is None:
                item["result_position"] = i + 1
        else:
            # For objects (like Pydantic models), only add if the field exists
            if hasattr(item, "query_id"):
                try:
                    setattr(item, "query_id", None)
                except (AttributeError, TypeError):
                    # Field exists but is not settable (e.g., Pydantic model)
                    pass
            if hasattr(item, "result_position"):
                try:
                    # Only set if not already set
                    current_value = getattr(item, "result_position", None)
                    if current_value is None:
                        setattr(item, "result_position", i + 1)
                except (AttributeError, TypeError):
                    # Field exists but is not settable
                    pass


async def _basic_search(
    search_client: Any,
    query: str,
    language: Optional[str],
    max_results: int,
    skip: int,
    orderby: Optional[str],
) -> tuple[List[Any], int]:
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


def _truncate_snippets(items: List[Dict[str, Any]], snippet_lines: int) -> None:
    for item in items:
        snippet_full = item.get("content") or ""
        if not isinstance(snippet_full, str):
            continue

        # Headline: prefer sanitized highlight if present
        hl = _first_highlight(item)
        headline = _sanitize_text(hl) if hl else _select_headline(item, snippet_full)

        selected = []
        if headline:
            selected.append(headline)

        if snippet_lines > 1:
            lines = [ln.rstrip() for ln in snippet_full.splitlines()]
            # If we have a headline, find its position with fuzzy matching

            def _find_index(lines, headline):
                norm = lambda s: _sanitize_text(s).lower()
                h = norm(headline)
                # First try exact match
                for i, ln in enumerate(lines):
                    if h in norm(ln):
                        return i
                # Fallback to fuzzy match
                for i, ln in enumerate(lines):
                    if difflib.SequenceMatcher(None, norm(ln), h).ratio() >= 0.6:
                        return i
                return 0

            idx = _find_index(lines, headline) if headline else 0
            # Add subsequent lines, skipping blanks/comments
            extra_needed = snippet_lines - 1
            for ln in lines[idx+1:]:
                t = _sanitize_text(ln)
                if not t or t.startswith(("#", "//", "/*", "*", "*/", "<!--")):
                    continue
                selected.append(t if len(t) <= 120 else t[:117] + "…")
                extra_needed -= 1
                if extra_needed <= 0:
                    break

        item["content"] = "\n".join(selected)


def _select_headline(item: Dict[str, Any], snippet_full: str) -> str:
    """Select the most informative single-line snippet."""
    # Try highlights first
    hl = None
    for k in ("@search.highlights", "highlights"):
        maybe = item.get(k)
        if isinstance(maybe, dict):
            for _field, hls in maybe.items():
                if hls:
                    hl = hls[0]
                    break
        if hl:
            break

    if isinstance(hl, str) and hl.strip():
        return hl.strip()

    # Fallback to first non-empty, non-comment line
    for ln in snippet_full.splitlines():
        stripped = ln.strip()
        if stripped and not stripped.startswith(("#", "//", "/*")):
            return stripped

    # Ultimate fallback
    lines = snippet_full.splitlines()
    return lines[0].strip() if lines else ""


async def _search_microsoft_docs_impl(query: str, max_results: int) -> Dict[str, Any]:
    """Implementation of Microsoft Docs search."""
    try:
        from microsoft_docs_mcp_client import MicrosoftDocsMCPClient

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


async def _explain_ranking_impl(
    server: "MCPServer",
    query: str,
    mode: str,
    max_results: int,
    intent: Optional[str],
    language: Optional[str],
    repository: Optional[str],
) -> Dict[str, Any]:
    """Implementation of ranking explanation."""
    if mode == "enhanced" and server.result_explainer:
        try:
            # Get search results first
            search_result = await _search_code_impl(
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

            # Lazy imports to avoid circular dependencies
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


async def _track_interaction(
    server: "MCPServer",
    interaction_type: str,
    query_id: str,
    doc_id: Optional[str] = None,
    rank: Optional[int] = None,
    outcome: Optional[str] = None,
    score: Optional[float] = None,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Common tracking implementation for clicks and outcomes."""
    # Try enhanced_search first
    if server.enhanced_search:
        try:
            if interaction_type == "click":
                if doc_id is None:
                    return err("doc_id is required for click tracking")
                if rank is None:
                    return err("rank is required for click tracking")
                await server.enhanced_search.track_click(
                    query_id=query_id, doc_id=doc_id, rank=rank, context=context
                )
                return ok({"tracked": True, "query_id": query_id, "doc_id": doc_id})
            # outcome
            if outcome is None:
                return err("outcome is required for outcome tracking")
            await server.enhanced_search.track_outcome(
                query_id=query_id, outcome=outcome, score=score, context=context
            )
            return ok({"tracked": True, "query_id": query_id, "outcome": outcome})
        except Exception as e:
            logger.warning(f"Enhanced search tracking failed: {e}")

    # Fall back to feedback_collector
    if server.feedback_collector:
        try:
            # Check if specific method exists
            method_name = f"track_{interaction_type}"
            if hasattr(server.feedback_collector, method_name):
                method = getattr(server.feedback_collector, method_name)
                if interaction_type == "click":
                    if doc_id is None:
                        return err("doc_id is required for click tracking")
                    await method(
                        query_id=query_id,
                        doc_id=doc_id,
                        rank=rank or 0,
                        context=context,
                    )
                else:
                    if outcome is None:
                        return err("outcome is required for outcome tracking")
                    await method(
                        query_id=query_id, outcome=outcome, score=score, context=context
                    )
            else:
                # Store as generic interaction
                interaction_data: Dict[str, Any] = {
                    "type": f"search_{interaction_type}",
                    "query_id": query_id,
                    "timestamp": time.time(),
                }
                if interaction_type == "click":
                    if doc_id is None:
                        return err("doc_id is required for click tracking")
                    interaction_data["doc_id"] = doc_id
                    if rank is not None:
                        interaction_data["rank"] = rank
                else:
                    if outcome is None:
                        return err("outcome is required for outcome tracking")
                    interaction_data["outcome"] = outcome
                    if score is not None:
                        interaction_data["score"] = score
                if context:
                    interaction_data["context"] = context

                # Store in feedback collector using available method
                if hasattr(server.feedback_collector, "record_explicit_feedback"):
                    await server.feedback_collector.record_explicit_feedback(
                        interaction_id=query_id,
                        satisfaction=5,  # Default neutral rating
                        comment=f"Search {interaction_type}: {interaction_data}",
                    )
                else:
                    logger.warning("No suitable feedback storage method found")
                    return err("No suitable feedback storage method available")

            result_data: Dict[str, Any] = {"tracked": True, "query_id": query_id}
            if interaction_type == "click" and doc_id is not None:
                result_data["doc_id"] = doc_id
            elif interaction_type != "click" and outcome is not None:
                result_data["outcome"] = outcome
            return ok(result_data)
        except Exception as e:
            logger.warning(f"Feedback collector tracking failed: {e}")

    return err("No tracking backend available")

    # ========== Azure AI Search Management Tools ==========

    @mcp.tool()
    async def manage_index(
        action: str,
        index_definition: Optional[Dict[str, Any]] = None,
        index_name: Optional[str] = None,
        update_if_different: bool = True,
        backup_documents: bool = False
    ) -> Dict[str, Any]:
        """Manage Azure AI Search indexes.

        Actions:
        - create: Create or update an index (requires index_definition)
        - ensure: Ensure index exists with correct schema (requires index_definition)
        - recreate: Drop and recreate index (requires index_definition)
        - delete: Delete an index (requires index_name)
        - optimize: Get optimization recommendations (requires index_name)
        - validate: Validate index schema (requires index_name)
        - list: List all indexes with stats
        """
        if not _check_component(server.index_automation, "Index automation"):
            return err("Index automation not available")

        if not Config.ADMIN_MODE and action in ["create", "recreate", "delete"]:
            return err("Admin mode required for destructive operations")

        try:
            if action == "create" or action == "ensure":
                if not index_definition:
                    return err("index_definition required for create/ensure")
                result = await server.index_automation.ensure_index_exists(
                    index_definition, update_if_different
                )
                return ok(result)

            elif action == "recreate":
                if not index_definition:
                    return err("index_definition required for recreate")
                result = await server.index_automation.recreate_index(
                    index_definition, backup_documents
                )
                return ok(result)

            elif action == "delete":
                if not index_name:
                    return err("index_name required for delete")
                await server.rest_ops.delete_index(index_name)
                return ok({"deleted": True, "index": index_name})

            elif action == "optimize":
                if not index_name:
                    return err("index_name required for optimize")
                result = await server.index_automation.optimize_index(index_name)
                return ok(result)

            elif action == "validate":
                if not index_name:
                    return err("index_name required for validate")
                result = await server.index_automation.validate_index_schema(
                    index_name, index_definition
                )
                return ok(result)

            elif action == "list":
                result = await server.index_automation.list_indexes_with_stats()
                return ok({"indexes": result})

            else:
                return err(f"Invalid action: {action}")

        except Exception as e:
            return err(str(e))

    @mcp.tool()
    async def manage_documents(
        action: str,
        index_name: str,
        documents: Optional[List[Dict[str, Any]]] = None,
        document_keys: Optional[List[str]] = None,
        filter_query: Optional[str] = None,
        batch_size: int = 1000,
        merge: bool = False,
        days_old: Optional[int] = None,
        date_field: Optional[str] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Manage documents in Azure AI Search.

        Actions:
        - upload: Upload documents (requires documents)
        - delete: Delete documents by key (requires document_keys)
        - cleanup: Delete old documents (requires days_old and date_field)
        - count: Get document count
        - verify: Verify document integrity
        """
        if not _check_component(server.data_automation, "Data automation"):
            return err("Data automation not available")

        if not Config.ADMIN_MODE and action in ["upload", "delete", "cleanup"]:
            return err("Admin mode required for document modifications")

        try:
            if action == "upload":
                if not documents:
                    return err("documents required for upload")

                # Convert list to async generator
                async def doc_generator():
                    for doc in documents:
                        yield doc

                result = await server.data_automation.bulk_upload(
                    index_name, doc_generator(), batch_size, merge
                )
                return ok(result)

            elif action == "delete":
                if not document_keys:
                    return err("document_keys required for delete")
                result = await server.rest_ops.delete_documents(index_name, document_keys)
                return ok({"deleted": len(document_keys), "index": index_name})

            elif action == "cleanup":
                if not days_old or not date_field:
                    return err("days_old and date_field required for cleanup")
                result = await server.data_automation.cleanup_old_documents(
                    index_name, date_field, days_old, batch_size, dry_run
                )
                return ok(result)

            elif action == "count":
                count = await server.rest_ops.count_documents(index_name)
                return ok({"count": count, "index": index_name})

            elif action == "verify":
                result = await server.data_automation.verify_documents(
                    index_name, sample_size=100
                )
                return ok(result)

            else:
                return err(f"Invalid action: {action}")

        except Exception as e:
            return err(str(e))

    @mcp.tool()
    async def manage_indexer(
        action: str,
        indexer_name: Optional[str] = None,
        indexer_definition: Optional[Dict[str, Any]] = None,
        datasource_definition: Optional[Dict[str, Any]] = None,
        skillset_definition: Optional[Dict[str, Any]] = None,
        wait_for_completion: bool = False,
        lookback_hours: int = 24
    ) -> Dict[str, Any]:
        """Manage Azure AI Search indexers.

        Actions:
        - create: Create indexer (requires indexer_definition)
        - delete: Delete indexer (requires indexer_name)
        - run: Run indexer on demand (requires indexer_name)
        - reset: Reset indexer (requires indexer_name)
        - status: Get indexer status (requires indexer_name)
        - health: Monitor indexer health (requires indexer_name)
        - list: List all indexers
        """
        if not _check_component(server.indexer_automation, "Indexer automation"):
            return err("Indexer automation not available")

        if not Config.ADMIN_MODE and action in ["create", "delete", "reset"]:
            return err("Admin mode required for indexer modifications")

        try:
            if action == "create":
                if not indexer_definition:
                    return err("indexer_definition required for create")

                # Create datasource if provided
                if datasource_definition:
                    await server.rest_ops.create_datasource(datasource_definition)

                # Create skillset if provided
                if skillset_definition:
                    await server.rest_ops.create_skillset(skillset_definition)

                result = await server.rest_ops.create_indexer(indexer_definition)
                return ok({"created": True, "indexer": result})

            elif action == "delete":
                if not indexer_name:
                    return err("indexer_name required for delete")
                await server.rest_ops.delete_indexer(indexer_name)
                return ok({"deleted": True, "indexer": indexer_name})

            elif action == "run":
                if not indexer_name:
                    return err("indexer_name required for run")
                result = await server.indexer_automation.reset_and_run_indexer(
                    indexer_name, wait_for_completion
                )
                return ok(result)

            elif action == "reset":
                if not indexer_name:
                    return err("indexer_name required for reset")
                await server.rest_ops.reset_indexer(indexer_name)
                return ok({"reset": True, "indexer": indexer_name})

            elif action == "status":
                if not indexer_name:
                    return err("indexer_name required for status")
                result = await server.rest_ops.get_indexer_status(indexer_name)
                return ok(result)

            elif action == "health":
                if not indexer_name:
                    return err("indexer_name required for health")
                result = await server.indexer_automation.monitor_indexer_health(
                    indexer_name, lookback_hours
                )
                return ok(result)

            elif action == "list":
                result = await server.rest_ops.list_indexers()
                return ok({"indexers": result})

            else:
                return err(f"Invalid action: {action}")

        except Exception as e:
            return err(str(e))

    @mcp.tool()
    async def health_check() -> Dict[str, Any]:
        """Get comprehensive health status of Azure AI Search service."""
        if not _check_component(server.health_monitor, "Health monitor"):
            return err("Health monitor not available")

        try:
            result = await server.health_monitor.get_full_health_report()
            return ok(result)
        except Exception as e:
            return err(str(e))

    @mcp.tool()
    async def create_datasource(
        datasource_type: str,
        name: str,
        connection_string: str,
        container: str,
        query: Optional[str] = None,
        change_detection_column: Optional[str] = None,
        delete_detection_column: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a data source for indexers.

        Args:
            datasource_type: Type of datasource (azureblob, azuresql, cosmosdb)
            name: Data source name
            connection_string: Connection string
            container: Container/table name
            query: Optional query/filter
            change_detection_column: Column for change tracking (SQL)
            delete_detection_column: Column for soft delete detection
        """
        if not _check_component(server.rest_ops, "REST operations"):
            return err("REST operations not available")

        if not Config.ADMIN_MODE:
            return err("Admin mode required for datasource creation")

        try:
            from enhanced_rag.azure_integration.rest.models import (
                create_blob_datasource,
                create_sql_datasource
            )

            if datasource_type == "azureblob":
                datasource = create_blob_datasource(
                    name=name,
                    connection_string=connection_string,
                    container_name=container,
                    query=query
                )
            elif datasource_type == "azuresql":
                datasource = create_sql_datasource(
                    name=name,
                    connection_string=connection_string,
                    table_or_view=container,
                    change_detection_policy={
                        "@odata.type": "#Microsoft.Azure.Search.HighWaterMarkChangeDetectionPolicy",
                        "highWaterMarkColumnName": change_detection_column
                    } if change_detection_column else None,
                    delete_detection_policy={
                        "@odata.type": "#Microsoft.Azure.Search.SoftDeleteColumnDeletionDetectionPolicy",
                        "softDeleteColumnName": delete_detection_column,
                        "softDeleteMarkerValue": "true"
                    } if delete_detection_column else None
                )
            else:
                return err(f"Unsupported datasource type: {datasource_type}")

            result = await server.rest_ops.create_datasource(datasource)
            return ok({"created": True, "datasource": result})
        except Exception as e:
            return err(str(e))

    @mcp.tool()
    async def create_skillset(
        name: str,
        skills: List[Dict[str, Any]],
        cognitive_services_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a skillset for cognitive enrichment.

        Args:
            name: Skillset name
            skills: List of skill definitions
            cognitive_services_key: Optional cognitive services key
        """
        if not _check_component(server.rest_ops, "REST operations"):
            return err("REST operations not available")

        if not Config.ADMIN_MODE:
            return err("Admin mode required for skillset creation")

        try:
            skillset_def = {
                "name": name,
                "skills": skills
            }

            if cognitive_services_key:
                skillset_def["cognitiveServices"] = {
                    "@odata.type": "#Microsoft.Azure.Search.CognitiveServicesByKey",
                    "key": cognitive_services_key
                }

            result = await server.rest_ops.create_skillset(skillset_def)
            return ok({"created": True, "skillset": result})
        except Exception as e:
            return err(str(e))
