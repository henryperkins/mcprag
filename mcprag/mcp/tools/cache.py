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
            return err(f"Invalid scope: {scope}. Must be one of: 'all', 'search', 'embeddings', 'results'")

        if not check_component(server.cache_manager, "Cache manager"):
            return err("Cache manager not available")

        # Explicit null check for type checker
        if server.cache_manager is None:
            return err("Cache manager component is not initialized")

        try:
            if scope == "all":
                await server.cache_manager.clear()
            else:
                # For specific scopes, use clear_pattern if available
                # The scope itself can be used as a pattern prefix
                if hasattr(server.cache_manager, "clear_scope"):
                    clear_method = getattr(server.cache_manager, "clear_scope")
                    await clear_method(scope)
                elif hasattr(server.cache_manager, "clear_pattern"):
                    # Use pattern-based clearing with scope as prefix
                    clear_method = getattr(server.cache_manager, "clear_pattern")
                    if pattern:
                        # Combine scope and pattern
                        await clear_method(f"{scope}:{pattern}")
                    else:
                        # Clear all entries in the scope
                        await clear_method(f"{scope}:*")
                else:
                    return err(f"Scope-based cache clearing not supported for scope: {scope}")

            stats = await server.cache_manager.get_stats()
            return ok({"cleared": True, "cache_stats": stats})
        except Exception as e:
            return err(str(e))
