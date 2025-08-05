"""Cache management MCP tools."""
from typing import Optional, Dict, Any, TYPE_CHECKING
from ...utils.response_helpers import ok, err
from .base import check_component
# Helper function
def validate_cache_scope(scope: str) -> bool:
    """Validate cache scope parameter."""
    valid_scopes = {"all", "search", "embeddings", "results"}
    return scope.lower() in valid_scopes

if TYPE_CHECKING:
    from ...server import MCPServer


def register_cache_tools(mcp, server: "MCPServer") -> None:
    """Register cache management MCP tools."""

    @mcp.tool()
    async def cache_stats() -> Dict[str, Any]:
        """Get cache statistics."""
        if not check_component(server.cache_manager, "Cache manager"):
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
        # Validation
        if not validate_cache_scope(scope):
            return err(f"Invalid scope: {scope}. Must be 'all' or 'pattern'")

        if scope == "pattern" and not pattern:
            return err("Pattern required when scope is 'pattern'")

        if not check_component(server.cache_manager, "Cache manager"):
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
