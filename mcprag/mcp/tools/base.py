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
        from ...config import Config
        from ...utils.response_helpers import err

        if not Config.ADMIN_MODE:
            return err("Admin mode not enabled")
        return await func(*args, **kwargs)
    return wrapper


def require_confirmation(func):
    """Decorator to require confirmation for destructive operations."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        from ...utils.response_helpers import ok

        # Check if confirm parameter is present and True
        confirm = kwargs.get('confirm', False)
        if not confirm:
            # Extract operation name from function name or first argument
            operation = func.__name__.replace('_', ' ')
            return ok({
                "confirmation_required": True,
                "message": f"Confirm {operation}? Call again with confirm=true to proceed.",
            })
        return await func(*args, **kwargs)
    return wrapper
