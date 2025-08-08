"""Code generation MCP tools."""
from typing import Optional, Dict, Any, TYPE_CHECKING, List
import logging

from ...utils.response_helpers import ok, err
from .base import check_component

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ...server import MCPServer


def register_generation_tools(mcp, server: "MCPServer") -> None:
    """Register code generation MCP tools."""

    async def _fallback_generate_code(
        description: str,
        language: str,
        context_file: Optional[str],
        style_guide: Optional[str],
        include_tests: bool,
        workspace_root: Optional[str],
    ) -> Dict[str, Any]:
        """
        Fallback path when server.code_gen isn't available.

        Strategy:
        - If server.pipeline exists, use it to retrieve examples to seed the generator.
        - Otherwise, call CodeGenerator with empty examples (generic template).
        Returns a dict mirroring CodeGenerationTool.generate_code output keys.
        """
        try:
            # Deferred imports to avoid making the whole module import-heavy
            from enhanced_rag.generation.code_generator import CodeGenerator, GenerationContext  # type: ignore
            from enhanced_rag.core.models import QueryContext  # type: ignore

            examples: List[Any] = []

            # Try to fetch examples via pipeline if available
            pipeline = getattr(server, "pipeline", None)
            if pipeline is not None:
                try:
                    query = f"Generate {language} code: {description}"
                    qctx = QueryContext(
                        current_file=context_file,
                        workspace_root=workspace_root,
                        user_preferences={
                            "language": language,
                            "style_guide": style_guide,
                            "include_tests": include_tests,
                        },
                    )
                    # Avoid generating natural language response; just need results
                    rag_result = await pipeline.process_query(
                        query=query, context=qctx, generate_response=False, max_results=10
                    )
                    if rag_result.success and rag_result.results:
                        examples = rag_result.results
                except Exception as e:
                    logger.debug(f"Fallback: pipeline retrieval failed: {e}")

            # Instantiate a lightweight generator
            gen = CodeGenerator({})
            gctx = GenerationContext(
                language=language,
                description=description,
                retrieved_examples=examples,  # may be empty
                style_guide=style_guide,
                context_file=context_file,
                include_tests=include_tests,
                imports_context=[],
            )

            gen_result = await gen.generate(gctx)
            if not gen_result.get("success"):
                return {
                    "success": False,
                    "error": gen_result.get("error", "Fallback generation failed"),
                }

            # Shape response to match CodeGenerationTool
            return {
                "success": True,
                "code": gen_result.get("code", ""),
                "language": language,
                "explanation": "Fallback generator used; limited context",
                "test_code": gen_result.get("test_code"),
                "references": [
                    {
                        "file": getattr(r, "file_path", ""),
                        "function": getattr(r, "function_name", None),
                        "snippet": ((getattr(r, "code_snippet", "") or "")[:200])
                        + ("..." if len(getattr(r, "code_snippet", "") or "") > 200 else ""),
                        "relevance": getattr(r, "score", 0.0),
                        "start_line": getattr(r, "start_line", None),
                        "end_line": getattr(r, "end_line", None),
                    }
                    for r in (examples[:5] if examples else [])
                ],
                "patterns_used": gen_result.get("patterns_used", []),
                "dependencies": [],
                "style_info": gen_result.get("style_info"),
                "template_used": gen_result.get("template_used"),
                "confidence": gen_result.get("confidence", 0.4),
            }
        except Exception as e:
            logger.exception("Fallback code generation failed")
            return {"success": False, "error": str(e)}

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
        # Ensure async components are started
        await server.ensure_async_components_started()

        # Primary path via CodeGenerationTool if available
        try:
            if server.code_gen is not None and check_component(server.code_gen, "Code generation"):
                result = await server.code_gen.generate_code(
                    description=description,
                    language=language,
                    context_file=context_file,
                    style_guide=style_guide,
                    include_tests=include_tests,
                    workspace_root=workspace_root,
                )
                return ok(result) if result.get("success") else err(result.get("error", "Code generation failed"))
            else:
                logger.info("CodeGenerationTool not available; using fallback generator")
                fallback = await _fallback_generate_code(
                    description, language, context_file, style_guide, include_tests, workspace_root
                )
                # Wrap fallback result as ok/err consistently
                return ok(fallback) if fallback.get("success") else err(fallback.get("error", "Fallback failed"))
        except Exception as e:
            # If primary path throws, attempt fallback before failing
            logger.warning(f"Primary code generation failed: {e}; attempting fallback")
            fallback = await _fallback_generate_code(
                description, language, context_file, style_guide, include_tests, workspace_root
            )
            return ok(fallback) if fallback.get("success") else err(fallback.get("error", str(e)))