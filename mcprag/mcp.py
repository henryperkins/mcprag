"""
MCP tool, resource and prompt registration.
"""

from typing import Any, Callable, Protocol, TYPE_CHECKING, runtime_checkable


# A structural type describing only what we use from FastMCP.
@runtime_checkable
class FastMCPLike(Protocol):
    def tool(self) -> Callable[..., Any]: ...
    def resource(self) -> Callable[..., Any]: ...
    def prompt(self) -> Callable[..., Any]: ...
    def run(self, transport: str = "stdio") -> None: ...


if TYPE_CHECKING:
    # Avoid runtime import cycles; only for typing
    from .server import MCPServer
else:
    MCPServer = Any  # type: ignore


def register_tools(mcp: FastMCPLike, server: MCPServer) -> None:
    """Register MCP tools."""
    # ...existing tool registration code...
    return None


def register_resources(mcp: FastMCPLike, server: MCPServer) -> None:
    """Register MCP resources."""
    # ...existing resource registration code...
    return None


def register_prompts(mcp: FastMCPLike) -> None:
    """Register MCP prompts."""
    # ...existing prompt registration code...
    return None