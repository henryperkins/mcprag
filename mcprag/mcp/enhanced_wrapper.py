"""Enhanced MCP tool wrapper with rate limiting, validation, and monitoring.

STATUS: Experimental/unused. This helper is not currently referenced by the
server’s tool registration path. It remains as a documented prototype for
centralized rate limiting, validation, and metrics, and can be safely removed
if you prefer a leaner runtime.
"""

import time
import logging
from functools import wraps
from typing import Dict, Any, Optional, Callable
import asyncio
from dataclasses import dataclass

from .utils import (
    RateLimitConfig,
    RateLimitError,
    rate_limit,
    ValidationError,
    validate_input,
    sanitize_input,
    create_mcp_validator
)

logger = logging.getLogger(__name__)


@dataclass
class MCPToolMetrics:
    """Metrics for MCP tool usage."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rate_limited_calls: int = 0
    validation_errors: int = 0
    average_response_time: float = 0.0
    last_called: Optional[float] = None


class MCPToolWrapper:
    """Enhanced wrapper for MCP tools with rate limiting, validation, and monitoring."""

    def __init__(
        self,
        tool_name: str,
        rate_limit_config: Optional[RateLimitConfig] = None,
        enable_validation: bool = True,
        enable_sanitization: bool = True,
        enable_metrics: bool = True
    ):
        """Initialize MCP tool wrapper.

        Args:
            tool_name: Name of the MCP tool
            rate_limit_config: Rate limiting configuration
            enable_validation: Whether to enable input validation
            enable_sanitization: Whether to enable input sanitization
            enable_metrics: Whether to collect metrics
        """
        self.tool_name = tool_name
        self.rate_limit_config = rate_limit_config or RateLimitConfig()
        self.enable_validation = enable_validation
        self.enable_sanitization = enable_sanitization
        self.enable_metrics = enable_metrics

        # Initialize components
        self.validator = create_mcp_validator(tool_name) if enable_validation else None
        self.metrics = MCPToolMetrics() if enable_metrics else None

        logger.info(f"Initialized MCP wrapper for tool '{tool_name}' with "
                   f"rate_limit={rate_limit_config is not None}, "
                   f"validation={enable_validation}, "
                   f"sanitization={enable_sanitization}, "
                   f"metrics={enable_metrics}")

    def wrap_tool(self, tool_func: Callable) -> Callable:
        """Wrap an MCP tool function with enhancements.

        Args:
            tool_func: Original tool function to wrap

        Returns:
            Enhanced tool function
        """
        @rate_limit(self.rate_limit_config, lambda *args, **kwargs: self._get_client_id(kwargs))
        @wraps(tool_func)
        async def enhanced_tool(*args, **kwargs):
            start_time = time.time()

            try:
                # Update metrics
                if self.metrics:
                    self.metrics.total_calls += 1
                    self.metrics.last_called = start_time

                # Sanitize inputs
                if self.enable_sanitization:
                    kwargs = {k: sanitize_input(v) for k, v in kwargs.items()}

                # Validate inputs
                if self.validator:
                    try:
                        kwargs = self.validator.validate(kwargs)
                    except ValidationError as e:
                        if self.metrics:
                            self.metrics.validation_errors += 1
                            self.metrics.failed_calls += 1
                        logger.warning(f"Validation failed for {self.tool_name}: {e}")
                        raise

                # Call the original tool
                result = await tool_func(*args, **kwargs)

                # Update success metrics
                if self.metrics:
                    self.metrics.successful_calls += 1
                    duration = time.time() - start_time
                    self._update_average_response_time(duration)

                logger.debug(f"Successfully called {self.tool_name} in {time.time() - start_time:.3f}s")
                return result

            except RateLimitError as e:
                if self.metrics:
                    self.metrics.rate_limited_calls += 1
                    self.metrics.failed_calls += 1
                logger.warning(f"Rate limit exceeded for {self.tool_name}: {e}")
                raise

            except Exception as e:
                if self.metrics:
                    self.metrics.failed_calls += 1
                logger.error(f"Error in {self.tool_name}: {e}", exc_info=True)
                raise

        return enhanced_tool

    def _get_client_id(self, kwargs: Dict[str, Any]) -> str:
        """Extract client ID from kwargs for rate limiting.

        Args:
            kwargs: Function keyword arguments

        Returns:
            Client identifier string
        """
        # Try to extract user/client identifier from common fields
        for field in ['user_id', 'client_id', 'session_id', 'api_key']:
            if field in kwargs:
                return str(kwargs[field])

        # Fallback to tool name (global rate limiting)
        return self.tool_name

    def _update_average_response_time(self, duration: float):
        """Update average response time metric.

        Args:
            duration: Duration of the last call
        """
        if not self.metrics:
            return

        if self.metrics.successful_calls == 1:
            self.metrics.average_response_time = duration
        else:
            # Running average
            total_time = self.metrics.average_response_time * (self.metrics.successful_calls - 1) + duration
            self.metrics.average_response_time = total_time / self.metrics.successful_calls

    def get_metrics(self) -> Optional[Dict[str, Any]]:
        """Get tool metrics.

        Returns:
            Metrics dictionary or None if metrics disabled
        """
        if not self.metrics:
            return None

        return {
            'tool_name': self.tool_name,
            'total_calls': self.metrics.total_calls,
            'successful_calls': self.metrics.successful_calls,
            'failed_calls': self.metrics.failed_calls,
            'rate_limited_calls': self.metrics.rate_limited_calls,
            'validation_errors': self.metrics.validation_errors,
            'success_rate': (
                self.metrics.successful_calls / max(1, self.metrics.total_calls) * 100
            ),
            'average_response_time_ms': self.metrics.average_response_time * 1000,
            'last_called': self.metrics.last_called,
            'uptime_hours': (time.time() - (self.metrics.last_called or time.time())) / 3600
        }

    def reset_metrics(self):
        """Reset metrics counters."""
        if self.metrics:
            self.metrics = MCPToolMetrics()
            logger.info(f"Reset metrics for tool '{self.tool_name}'")


class MCPToolRegistry:
    """Registry for managing enhanced MCP tools."""

    def __init__(self):
        """Initialize tool registry."""
        self.tools: Dict[str, MCPToolWrapper] = {}
        self.original_tools: Dict[str, Callable] = {}

    def register_tool(
        self,
        tool_name: str,
        tool_func: Callable,
        rate_limit_config: Optional[RateLimitConfig] = None,
        enable_validation: bool = True,
        enable_sanitization: bool = True,
        enable_metrics: bool = True
    ) -> Callable:
        """Register and enhance an MCP tool.

        Args:
            tool_name: Name of the tool
            tool_func: Original tool function
            rate_limit_config: Rate limiting configuration
            enable_validation: Enable input validation
            enable_sanitization: Enable input sanitization
            enable_metrics: Enable metrics collection

        Returns:
            Enhanced tool function
        """
        wrapper = MCPToolWrapper(
            tool_name=tool_name,
            rate_limit_config=rate_limit_config,
            enable_validation=enable_validation,
            enable_sanitization=enable_sanitization,
            enable_metrics=enable_metrics
        )

        enhanced_func = wrapper.wrap_tool(tool_func)

        self.tools[tool_name] = wrapper
        self.original_tools[tool_name] = tool_func

        logger.info(f"Registered enhanced MCP tool: {tool_name}")
        return enhanced_func

    def get_tool_metrics(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get metrics for a specific tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Metrics dictionary or None
        """
        wrapper = self.tools.get(tool_name)
        return wrapper.get_metrics() if wrapper else None

    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all registered tools.

        Returns:
            Dictionary mapping tool names to their metrics
        """
        metrics = {}
        for tool_name, wrapper in self.tools.items():
            tool_metrics = wrapper.get_metrics()
            if tool_metrics:
                metrics[tool_name] = tool_metrics
        return metrics

    def reset_tool_metrics(self, tool_name: str):
        """Reset metrics for a specific tool.

        Args:
            tool_name: Name of the tool
        """
        wrapper = self.tools.get(tool_name)
        if wrapper:
            wrapper.reset_metrics()

    def reset_all_metrics(self):
        """Reset metrics for all tools."""
        for wrapper in self.tools.values():
            wrapper.reset_metrics()

    def list_tools(self) -> Dict[str, Dict[str, Any]]:
        """List all registered tools with their configurations.

        Returns:
            Dictionary of tool configurations
        """
        tool_info = {}
        for tool_name, wrapper in self.tools.items():
            tool_info[tool_name] = {
                'rate_limit_enabled': wrapper.rate_limit_config is not None,
                'validation_enabled': wrapper.enable_validation,
                'sanitization_enabled': wrapper.enable_sanitization,
                'metrics_enabled': wrapper.enable_metrics,
                'rate_limit_config': {
                    'max_requests': wrapper.rate_limit_config.max_requests,
                    'window_seconds': wrapper.rate_limit_config.window_seconds,
                    'burst_limit': wrapper.rate_limit_config.burst_limit
                } if wrapper.rate_limit_config else None
            }
        return tool_info


# Global registry instance
global_mcp_registry = MCPToolRegistry()


def enhance_mcp_tool(
    tool_name: str,
    rate_limit_config: Optional[RateLimitConfig] = None,
    enable_validation: bool = True,
    enable_sanitization: bool = True,
    enable_metrics: bool = True
):
    """Decorator to enhance MCP tools.

    Args:
        tool_name: Name of the MCP tool
        rate_limit_config: Rate limiting configuration
        enable_validation: Enable input validation
        enable_sanitization: Enable input sanitization
        enable_metrics: Enable metrics collection
    """
    def decorator(func: Callable) -> Callable:
        return global_mcp_registry.register_tool(
            tool_name=tool_name,
            tool_func=func,
            rate_limit_config=rate_limit_config,
            enable_validation=enable_validation,
            enable_sanitization=enable_sanitization,
            enable_metrics=enable_metrics
        )
    return decorator
