"""
Compatibility shim for tests expecting mcp_server_sota.py.

This allows existing tests to continue working
while we transition to the modular structure.
"""

# Import everything from the new modular structure
# Use package-relative imports so this works when "mcprag" is a package
from .server import MCPServer, create_server  # type: ignore
from .config import Config  # noqa: F401

# Create a module-level server instance for compatibility
server = create_server()

# Try to expose enhanced_rag-related types if present on the server
try:
    EnhancedMCPServer = MCPServer
except Exception:
    EnhancedMCPServer = MCPServer  # Fallback to MCPServer reference

# EnhancedSearchTool doesn't expose typed dataclasses here.
# Keep None placeholders for compatibility with legacy tests.
SearchCodeParams = None
SearchResult = None
SearchIntent = None


# Export the search_code function for direct imports
async def search_code(*args, **kwargs):
    """Compatibility wrapper for search_code."""
    # Import via package to avoid workspace-root import ambiguity
    from .mcp.mcp.tools import register_tools  # type: ignore

    # Build a minimal mock MCP to capture the function reference
    captured = {}

    class _MockMCP:
        def tool(self):
            def deco(func):
                captured["search_code"] = func
                return func

            return deco

        def resource(self):
            def deco(func):
                return func

            return deco

        def prompt(self):
            def deco(func):
                return func

            return deco

    mock_mcp = _MockMCP()
    # Register tools against the live server instance to get the bound function
    register_tools(mock_mcp, server)
    tool_fn = captured.get("search_code")
    if tool_fn is None:
        raise RuntimeError("search_code tool not available")
    return await tool_fn(*args, **kwargs)


# For scripts that expect to run the server directly
if __name__ == "__main__":
    server.run()
