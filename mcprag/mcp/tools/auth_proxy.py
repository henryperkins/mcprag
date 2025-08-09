"""Authentication proxy for MCP tool registration.

This module creates a proxy that intercepts @mcp.tool() decorators
and registers tools through the TransportWrapper for unified auth.
"""

from types import ModuleType
from typing import Any, Callable
import functools
import logging

logger = logging.getLogger(__name__)


class AuthProxyMCP:
    """Proxy for MCP module that intercepts tool registration."""
    
    def __init__(self, original_mcp: ModuleType, transport_wrapper: Any):
        """Initialize the proxy.
        
        Args:
            original_mcp: The original MCP module
            transport_wrapper: The TransportWrapper instance
        """
        self._original = original_mcp
        self._wrapper = transport_wrapper
        
    def tool(self, *args, **kwargs):
        """Intercept @mcp.tool() decorator and route through transport wrapper."""
        # Get the original decorator
        original_decorator = self._original.tool(*args, **kwargs)
        
        def wrapper(func: Callable) -> Callable:
            # First apply the original decorator
            decorated = original_decorator(func)
            
            # Extract tool metadata
            tool_name = func.__name__
            tool_description = func.__doc__ or ""
            
            # Extract parameters from function signature
            import inspect
            sig = inspect.signature(func)
            parameters = {}
            for param_name, param in sig.parameters.items():
                # Skip transport/framework context parameter from public schema
                if param_name == 'ctx':
                    continue
                param_type = "string"  # Default type
                if param.annotation != inspect.Parameter.empty:
                    # Try to infer type from annotation
                    if param.annotation == int:
                        param_type = "integer"
                    elif param.annotation == bool:
                        param_type = "boolean"
                    elif param.annotation == float:
                        param_type = "number"
                
                parameters[param_name] = {
                    "type": param_type,
                    "required": param.default == inspect.Parameter.empty
                }
            
            # Register with transport wrapper for auth enforcement
            self._wrapper.register_tool(
                tool_name,
                func,
                tool_description,
                parameters
            )
            
            logger.debug(f"Registered tool '{tool_name}' through transport wrapper")
            
            # Return the decorated function
            return decorated
        
        return wrapper
    
    def __getattr__(self, name: str) -> Any:
        """Pass through any other attributes to the original MCP module."""
        return getattr(self._original, name)


def create_auth_proxy_mcp(mcp: ModuleType, transport_wrapper: Any) -> AuthProxyMCP:
    """Create an authentication proxy for the MCP module.
    
    Args:
        mcp: The original MCP module
        transport_wrapper: The TransportWrapper instance
        
    Returns:
        A proxy that intercepts tool registration
    """
    return AuthProxyMCP(mcp, transport_wrapper)
