"""
MCP tool definitions.

Thin wrappers around enhanced_rag functionality exposed as MCP tools.
"""

from typing import Optional, List, Dict, Any
import re
import time
import asyncio
import logging

from ..utils.response_helpers import ok, err
from ..config import Config

logger = logging.getLogger(__name__)


def register_tools(mcp: Any, server: 'MCPServer') -> None:
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
        snippet_lines: int = 0  # 0 = no truncation, >0 = max lines in snippet
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
        start_time = time.time()

        # Ensure async components are started
        await server.ensure_async_components_started()

        # Auto-extract exact terms if not provided
        if exact_terms is None and query:
            exact_terms = _extract_exact_terms(query)

        try:
            # Normalise detail level argument early to avoid repeated lower() calls
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
                    dependency_mode=dependency_mode
                )

                # Check if enhanced search returned an error
                if "error" in result:
                    return err(result["error"])

                # Pick correct list of items based on requested detail level
                if detail_level == "compact":
                    items = result.get("results_compact", result.get("results", []))
                elif detail_level == "ultra":
                    items = result.get("results_ultra_compact", result.get("results", []))
                else:
                    items = result.get("results", [])
                total = result.get("total_count", len(items))

                # Add query_id and result_position to items if available
                for i, item in enumerate(items):
                    if hasattr(item, 'query_id'):
                        item['query_id'] = getattr(item, 'query_id', None)
                    if hasattr(item, 'result_position'):
                        item['result_position'] = getattr(item, 'result_position', i + 1)

            # Fallback to basic Azure Search
            elif server.search_client:
                search_params = {
                    "search_text": query,
                    "top": max_results,
                    "skip": skip,
                    "include_total_count": True
                }

                if language:
                    search_params["filter"] = f"language eq '{language}'"
                if orderby:
                    search_params["orderby"] = orderby

                response = server.search_client.search(**search_params)
                items = list(response)
                total = response.get_count() if hasattr(response, 'get_count') else len(items)

            else:
                return err("No search backend available")

            took_ms = (time.time() - start_time) * 1000

            # Optionally truncate multi-line code snippets inside each item to
            # reduce token usage whilst retaining quick preview context. This
            # only affects the "full" detail level where full snippets are
            # present in the payload.
            # ------------------------------------------------------------------
            # Optional concise snippet handling for FULL detail level
            # ------------------------------------------------------------------
            if snippet_lines > 0 and detail_level == "full":
                for item in items:
                    # Helper to pick the most informative single-line snippet
                    def _select_headline() -> str:
                        # 1. Prefer first highlight string if present
                        hl = None
                        for k in ("@search.highlights", "highlights"):
                            maybe = item.get(k)
                            if isinstance(maybe, dict):
                                # Use first highlight text available across any field
                                for _field, hls in maybe.items():
                                    if hls:
                                        hl = hls[0]
                                        break
                            if hl:
                                break

                        if isinstance(hl, str) and hl.strip():
                            return hl.strip()

                        # 2. Fallback to first non-empty, non-comment line in snippet
                        snippet_full = item.get("content") or item.get("code_snippet") or ""
                        for ln in snippet_full.splitlines():
                            stripped = ln.strip()
                            if stripped and not stripped.startswith(("#", "//", "/*")):
                                return stripped

                        # 3. Ultimate fallback – first line (even if blank/comment)
                        lines = snippet_full.splitlines()
                        return lines[0].strip() if lines else ""

                    # Build the truncated snippet respecting snippet_lines
                    snippet_full = item.get("content") or item.get("code_snippet") or ""
                    if not isinstance(snippet_full, str):
                        continue

                    selected_lines = []

                    headline = _select_headline()
                    if headline:
                        selected_lines.append(headline)

                    # If more lines requested, add from original snippet after headline
                    if snippet_lines > 1:
                        extra_needed = snippet_lines - 1
                        for ln in snippet_full.splitlines():
                            if ln.strip() == headline:
                                continue  # skip duplicate
                            if extra_needed <= 0:
                                break
                            selected_lines.append(ln.rstrip())
                            extra_needed -= 1

                    # Trim each line to 120 chars
                    processed = []
                    for ln in selected_lines:
                        ln = ln.rstrip()
                        if len(ln) > 120:
                            processed.append(ln[:117] + "…")
                        else:
                            processed.append(ln)

                    item["content"] = "\n".join(processed)

            response = {
                "items": items,
                "count": len(items),
                "total": total,
                "took_ms": took_ms,
                "query": query,
                "applied_exact_terms": bool(exact_terms),
                "exact_terms": exact_terms,
            }

            if include_timings:
                response["timings_ms"] = {"total": took_ms}
            # Include the level so front-ends can decide how to display
            response["detail_level"] = detail_level

            return ok(response)

        except Exception as e:
            return err(str(e))

    @mcp.tool()
    async def search_code_raw(
        query: str,
        intent: Optional[str] = None,
        language: Optional[str] = None,
        repository: Optional[str] = None,
        max_results: int = 10,
        include_dependencies: bool = False
    ) -> Dict[str, Any]:
        """Raw search results without formatting."""
        result = await search_code(
            query=query,
            intent=intent,
            language=language,
            repository=repository,
            max_results=max_results,
            include_dependencies=include_dependencies
        )

        if result["ok"]:
            data = result["data"]
            return ok({
                "results": data["items"],
                "count": data["count"],
                "total": data["total"],
                "query": query,
                "intent": intent
            })
        return result

    @mcp.tool()
    async def search_microsoft_docs(
        query: str,
        max_results: int = 10
    ) -> Dict[str, Any]:
        """Search Microsoft Learn documentation."""
        try:
            from microsoft_docs_mcp_client import MicrosoftDocsMCPClient

            async with MicrosoftDocsMCPClient() as client:
                results = await client.search_docs(query=query, max_results=max_results)

            if not results:
                return ok({
                    "query": query,
                    "count": 0,
                    "results": [],
                    "formatted": f"No Microsoft documentation found for '{query}'."
                })

            formatted_results = []
            formatted_lines = [f"📚 Found {len(results)} Microsoft Docs:\n"]

            for i, doc in enumerate(results, 1):
                formatted_results.append({
                    "title": doc.get("title", "Untitled"),
                    "url": doc.get("url", ""),
                    "snippet": doc.get("content", "")[:300]
                })

                formatted_lines.append(
                    f"{i}. {doc.get('title', 'Untitled')}\n"
                    f"   {doc.get('url', '')}\n"
                    f"   {doc.get('content', '')[:300]}...\n"
                )

            return ok({
                "query": query,
                "count": len(results),
                "results": formatted_results,
                "formatted": "\n".join(formatted_lines)
            })

        except Exception as e:
            return err(f"Microsoft Docs search unavailable: {str(e)}")

    @mcp.tool()
    async def generate_code(
        description: str,
        language: str = "python",
        context_file: Optional[str] = None,
        style_guide: Optional[str] = None,
        include_tests: bool = False,
        workspace_root: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate code using enhanced RAG pipeline."""
        if not server.code_gen:
            return err("Code generation not available")

        try:
            result = await server.code_gen.generate_code(
                description=description,
                language=language,
                context_file=context_file,
                style_guide=style_guide,
                include_tests=include_tests,
                workspace_root=workspace_root
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
        include_git_history: bool = False
    ) -> Dict[str, Any]:
        """Analyze file context using enhanced RAG."""
        if not server.context_aware:
            return err("Context analysis not available")

        try:
            result = await server.context_aware.analyze_context(
                file_path=file_path,
                include_dependencies=include_dependencies,
                depth=depth,
                include_imports=include_imports,
                include_git_history=include_git_history
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
        repository: Optional[str] = None
    ) -> Dict[str, Any]:
        """Explain ranking factors for results."""
        if mode == "enhanced" and server.result_explainer:
            try:
                # Get search results first
                search_result = await search_code(
                    query=query,
                    intent=intent,
                    language=language,
                    repository=repository,
                    max_results=max_results
                )

                if not search_result["ok"]:
                    return search_result

                results = search_result["data"]["items"]
                explanations = []

                for result in results:
                    # Convert dict to SearchResult for explainer
                    from enhanced_rag.core.models import SearchResult, SearchQuery
                    search_result = SearchResult(
                        id=result.get('id', ''),
                        score=result.get('relevance', 0.0),
                        file_path=result.get('file', ''),
                        repository=result.get('repository', ''),
                        function_name=result.get('function_name'),
                        class_name=result.get('class_name'),
                        code_snippet=result.get('content', ''),
                        language=result.get('language', ''),
                        highlights=result.get('highlights', {}),
                        signature=result.get('signature', ''),
                        semantic_context=result.get('semantic_context', ''),
                        imports=result.get('imports', []),
                        dependencies=result.get('dependencies', [])
                    )

                    # Create a SearchQuery object
                    from enhanced_rag.core.models import SearchIntent
                    search_intent = SearchIntent(intent) if intent else None
                    search_query = SearchQuery(
                        query=query,
                        intent=search_intent,
                        current_file=None,
                        language=language,
                        user_id=None
                    )

                    explanation = await server.result_explainer.explain_ranking(
                        result=search_result,
                        query=search_query,
                        context=None
                    )
                    explanations.append(explanation)

                return ok({
                    "mode": mode,
                    "query": query,
                    "explanations": explanations
                })
            except Exception as e:
                return err(str(e))
        else:
            return err("Ranking explanation not available")

    @mcp.tool()
    async def preview_query_processing(
        query: str,
        intent: Optional[str] = None,
        language: Optional[str] = None,
        repository: Optional[str] = None
    ) -> Dict[str, Any]:
        """Show intent classification and query enhancements."""
        try:
            response = {
                "input_query": query,
                "detected_intent": None,
                "enhancements": {},
                "rewritten_queries": [],
                "applied_rules": []
            }

            if server.intent_classifier:
                detected = await server.intent_classifier.classify_intent(query)
                response["detected_intent"] = detected.value if hasattr(detected, 'value') else str(detected)

            # Skip query enhancement if no context is available
            # The query enhancer requires a CodeContext object
            response["enhancements"] = {
                "note": "Query enhancement requires file context",
                "skipped": True
            }

            if server.query_rewriter:
                rewrites = await server.query_rewriter.rewrite_query(
                    query, intent=response["detected_intent"] or intent
                )
                response["rewritten_queries"] = rewrites if isinstance(rewrites, list) else [rewrites]

            return ok(response)
        except Exception as e:
            return err(str(e))

    @mcp.tool()
    async def submit_feedback(
        target_id: str,
        kind: str,
        rating: int,
        notes: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Submit user feedback."""
        if not server.feedback_collector:
            return err("Feedback collection not available")

        try:
            await server.feedback_collector.record_explicit_feedback(
                interaction_id=target_id,
                satisfaction=rating,
                comment=notes
            )
            return ok({"stored": True})
        except Exception as e:
            return err(str(e))

    @mcp.tool()
    async def track_search_click(
        query_id: str,
        doc_id: str,
        rank: int,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Track user click on search result."""
        # Try enhanced_search first if available
        if server.enhanced_search:
            try:
                await server.enhanced_search.track_click(
                    query_id=query_id,
                    doc_id=doc_id,
                    rank=rank,
                    context=context
                )
                return ok({"tracked": True, "query_id": query_id, "doc_id": doc_id})
            except Exception as e:
                logger.warning(f"Enhanced search track_click failed: {e}")
        
        # Fall back to feedback_collector if available
        if server.feedback_collector:
            try:
                # FeedbackCollector might have a different interface, so we adapt
                if hasattr(server.feedback_collector, 'track_click'):
                    await server.feedback_collector.track_click(
                        query_id=query_id,
                        doc_id=doc_id,
                        rank=rank,
                        context=context
                    )
                else:
                    # Store as generic interaction data
                    await server.feedback_collector.record_interaction({
                        'type': 'search_click',
                        'query_id': query_id,
                        'doc_id': doc_id,
                        'rank': rank,
                        'context': context,
                        'timestamp': time.time()
                    })
                return ok({"tracked": True, "query_id": query_id, "doc_id": doc_id})
            except Exception as e:
                logger.warning(f"Feedback collector track_click failed: {e}")
        
        return err("No tracking backend available")

    @mcp.tool()
    async def track_search_outcome(
        query_id: str,
        outcome: str,
        score: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Track search outcome (success/failure)."""
        # Try enhanced_search first if available
        if server.enhanced_search:
            try:
                await server.enhanced_search.track_outcome(
                    query_id=query_id,
                    outcome=outcome,
                    score=score,
                    context=context
                )
                return ok({"tracked": True, "query_id": query_id, "outcome": outcome})
            except Exception as e:
                logger.warning(f"Enhanced search track_outcome failed: {e}")
        
        # Fall back to feedback_collector if available
        if server.feedback_collector:
            try:
                # FeedbackCollector might have a different interface, so we adapt
                if hasattr(server.feedback_collector, 'track_outcome'):
                    await server.feedback_collector.track_outcome(
                        query_id=query_id,
                        outcome=outcome,
                        score=score,
                        context=context
                    )
                else:
                    # Store as generic interaction data
                    await server.feedback_collector.record_interaction({
                        'type': 'search_outcome',
                        'query_id': query_id,
                        'outcome': outcome,
                        'score': score,
                        'context': context,
                        'timestamp': time.time()
                    })
                return ok({"tracked": True, "query_id": query_id, "outcome": outcome})
            except Exception as e:
                logger.warning(f"Feedback collector track_outcome failed: {e}")
        
        return err("No tracking backend available")

    @mcp.tool()
    async def cache_stats() -> Dict[str, Any]:
        """Get cache statistics."""
        if server.cache_manager:
            try:
                stats = await server.cache_manager.get_stats()
                return ok({"cache_stats": stats})
            except Exception as e:
                return err(str(e))
        return err("Cache manager not available")

    @mcp.tool()
    async def cache_clear(
        scope: str = "all",
        pattern: Optional[str] = None
    ) -> Dict[str, Any]:
        """Clear cache."""
        if server.cache_manager:
            try:
                if scope == "all":
                    await server.cache_manager.clear()
                elif pattern:
                    await server.cache_manager.clear_pattern(pattern)

                stats = await server.cache_manager.get_stats()
                return ok({"cleared": True, "cache_stats": stats})
            except Exception as e:
                return err(str(e))
        return err("Cache manager not available")

    # ------------------------------------------------------------------#
    # Admin tools – now always registered but require runtime confirmation
    # ------------------------------------------------------------------#

    @mcp.tool()
    async def index_rebuild(
        repository: Optional[str] = None,
        *,
        confirm: bool = False
    ) -> Dict[str, Any]:
        """Rebuild (re-run) the Azure Search indexer.

        The tool is potentially destructive: it triggers a full crawl
        of the configured data-source and may overwrite existing vector
        data.  Therefore a confirmation step is required.

        Pass `confirm=true` to proceed.
        """

        if not confirm:
            return ok({
                "confirmation_required": True,
                "message": f"Rebuild indexer for '{repository or '[default]'}'? "
                           "Call again with confirm=true to proceed."
            })

        if not server.indexer_integration:
            return err("Indexer integration not available")

        try:
            if hasattr(server.indexer_integration, 'run_indexer_on_demand'):
                result = await server.indexer_integration.run_indexer_on_demand(repository)
            elif hasattr(server.indexer_integration, 'run_indexer'):
                result = await server.indexer_integration.run_indexer(repository)
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
        confirm: bool = False
    ) -> Dict[str, Any]:
        """Index a GitHub repository.

        Requires confirmation. Call once without `confirm` to get the
        prompt, again with `confirm=true` to execute.
        """

        if not confirm:
            return ok({
                "confirmation_required": True,
                "message": f"Index GitHub repository '{repo}' (branch: {branch or '[default]'})? "
                           "Call again with confirm=true to proceed."
            })

        if not server.remote_indexer:
            return err("GitHub indexing not available")

        try:
            owner, repo_name = repo.split('/')

            # Run sync method in executor
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None,
                lambda: server.remote_indexer.index_remote_repository(
                    owner, repo_name, ref=branch
                )
            )

            return ok({
                "repo": repo,
                "branch": branch,
                "mode": mode,
                "result": result
            })
        except Exception as e:
            return err(str(e))


def _extract_exact_terms(query: str) -> List[str]:
    """Extract exact terms from query."""
    terms = []

    # Quoted phrases
    quoted = re.findall(r'"([^"]+)"|\'([^\']+)\'', query)
    terms.extend([t for pair in quoted for t in pair if t])

    # Numbers
    numbers = re.findall(r'(?<![\w])(\d+(?:\.\d+)+|\d{2,})(?![\w.])', query)
    terms.extend(numbers)

    # Function calls
    functions = re.findall(r'(\w+)\s*\(', query)
    terms.extend(functions)

    # Deduplicate
    seen = set()
    return [t for t in terms if not (t in seen or seen.add(t))]
