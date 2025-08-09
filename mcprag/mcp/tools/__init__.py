"""
MCP tools package.

This package provides modular organization of MCP tool definitions.
The main entry point register_tools() maintains backward compatibility
with the original monolithic tools.py file.
"""

from types import ModuleType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..server import MCPServer


def register_tools(mcp: ModuleType, server: "MCPServer") -> None:
    """
    Register all MCP tools with the server.
    
    This is the main entry point that maintains backward compatibility
    with the original tools.py file. It imports and registers tools
    from all the modular submodules.
    
    If the server has a transport_wrapper, tools are registered through it
    for unified authentication. Otherwise, they're registered directly.
    
    Args:
        mcp: The MCP module
        server: The MCP server instance
    """
    # Check if we should use the transport wrapper
    if hasattr(server, 'transport_wrapper'):
        # Create a proxy MCP that intercepts tool registration
        from .auth_proxy import create_auth_proxy_mcp
        mcp = create_auth_proxy_mcp(mcp, server.transport_wrapper)
    
    # Import all tool registration functions
    from .search import register_search_tools
    from .generation import register_generation_tools
    from .analysis import register_analysis_tools
    from .feedback import register_feedback_tools
    from .cache import register_cache_tools
    from .admin import register_admin_tools
    from .azure_management import register_azure_tools
    from .service_management import register_service_management_tools
    
    # Register all tool categories
    register_search_tools(mcp, server)
    register_generation_tools(mcp, server)
    register_analysis_tools(mcp, server)
    register_feedback_tools(mcp, server)
    register_cache_tools(mcp, server)
    register_admin_tools(mcp, server)
    register_azure_tools(mcp, server)
    register_service_management_tools(mcp, server)


# Export for backward compatibility
__all__ = ['register_tools']
