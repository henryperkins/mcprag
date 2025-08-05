"""Code generation MCP tools."""
from typing import Optional, Dict, Any, TYPE_CHECKING
from ...utils.response_helpers import ok, err
from .base import check_component

if TYPE_CHECKING:
    from ...server import MCPServer


def register_generation_tools(mcp, server: "MCPServer") -> None:
    """Register code generation MCP tools."""

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
        if server.code_gen is None or not check_component(
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