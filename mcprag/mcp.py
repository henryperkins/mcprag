"""
MCP tool, resource and prompt registration.

"""

from typing import TYPE_CHECKING, Any, Union, Protocol, Callable, overload

# Define a minimal structural type for FastMCP-like objects to satisfy type checkers
class _FastMCPLike(Protocol):
    def tool(self) -> Callable[..., Any]: ...
    def resource(self) -> Callable[..., Any]: ...
    def prompt(self) -> Callable[..., Any]: ...
    def run(self, transport: str = "stdio") -> None: ...

FastMCPType = _FastMCPLike | Any
try:
    from .server import MCPServer  # for type context
except Exception:
    MCPServer = Any  # type: ignore

def register_tools(mcp: FastMCPType, server: Any) -> None:
    """Register MCP tools."""
    # ...existing tool registration code...
    pass

def register_resources(mcp: FastMCPType, server: Any) -> None:
    """Register MCP resources.""" 
    # ...existing resource registration code...
    pass

def register_prompts(mcp: FastMCPType) -> None:
    """Register MCP prompts."""
    # ...existing prompt registration code...
    pass