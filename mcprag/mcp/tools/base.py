"""Base utilities for MCP tools."""
from typing import Optional, Any, TYPE_CHECKING
import logging
from functools import wraps

if TYPE_CHECKING:
    from ...server import MCPServer

logger = logging.getLogger(__name__)


def check_component(component: Optional[Any], name: str) -> bool:
    """Check if a component is available and log if not."""
    if not component:
        logger.debug(f"{name} component not available")
        return False
    return True


def require_admin_mode(func):
    """Decorator to require admin mode."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        from enhanced_rag.core.unified_config import get_config
        from ...utils.response_helpers import err

        config = get_config()
        if not config.mcp_admin_mode:
            return err("Admin mode not enabled")
        return await func(*args, **kwargs)
    return wrapper


def require_confirmation(func):
    """Decorator to require confirmation for destructive operations."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        from ...utils.response_helpers import ok

        # Check if confirm parameter is present and True
        # The "confirm" flag may arrive as a string when the call originates
        # from an HTTP/CLI transport.  Treat common truthy strings as
        # confirmation as well to avoid confusing users.
        confirm_raw = kwargs.get('confirm', False)
        confirm = confirm_raw
        if isinstance(confirm_raw, str):
            confirm = confirm_raw.lower() in {"1", "true", "yes", "y"}

        if not confirm:
            # Extract operation name from function name or first argument
            operation = func.__name__.replace('_', ' ')
            return ok({
                "confirmation_required": True,
                "message": f"Confirm {operation}? Call again with confirm=true to proceed.",
            })
        return await func(*args, **kwargs)
    return wrapper
