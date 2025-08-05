"""Analysis and ranking MCP tools."""
from typing import Optional, Dict, Any, TYPE_CHECKING
from ...utils.response_helpers import ok, err
from .base import check_component
from ._helpers import explain_ranking_impl

if TYPE_CHECKING:
    from ...server import MCPServer


def register_analysis_tools(mcp, server: "MCPServer") -> None:
    """Register analysis and ranking MCP tools."""

    @mcp.tool()
    async def analyze_context(
        file_path: str,
        include_dependencies: bool = True,
        depth: int = 2,
        include_imports: bool = True,
        include_git_history: bool = False,
    ) -> Dict[str, Any]:
        """Analyze file context using enhanced RAG."""
        if not check_component(server.context_aware, "Context analysis"):
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
        return await explain_ranking_impl(
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
                # Import at runtime if not available
                try:
                    from enhanced_rag.core.models import SearchIntent
                except ImportError:
                    SearchIntent = None

                intent_for_rewrite: Optional[Any] = None

                # Prefer classifier result
                if detected:
                    intent_for_rewrite = detected
                # Fallback: convert supplied string to enum
                elif intent and SearchIntent:
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
