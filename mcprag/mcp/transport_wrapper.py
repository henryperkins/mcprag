"""Transport-agnostic tool wrapper for consistent behavior across transports.

NOTE: This module is currently not wired into the running server. Tool
registration still uses direct `@mcp.tool` decorators and route-level auth
checks in `remote_server.py`. We keep this wrapper as a documented,
future-facing path to centralize auth/tier enforcement across stdio/HTTP/SSE
once transport parity work lands (see docs/MCP_TRANSPORT_PARITY_GUIDE_V2.md).
Safe to remove if not needed.

This module provides a thin abstraction to:
- Register tools once with tiered authorization
- Execute tools with unified auth/context extraction (stdio, HTTP, SSE)
- List tools visible to a particular tier/user

It composes with existing modular registration in mcprag/mcp/tools by
wrapping handlers using the unified_auth decorator so behavior remains
consistent regardless of transport.

References:
- Unified auth handler: mcprag.auth.unified_auth
- Tool tier map/utilities: mcprag.auth.tool_security
"""

from __future__ import annotations

import logging
import asyncio
from dataclasses import dataclass
from inspect import iscoroutinefunction
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import Request
else:
    try:
        # FastAPI Request is optional; used for HTTP/SSE context passthrough
        from fastapi import Request  # type: ignore
    except ImportError:  # pragma: no cover
        Request = Any  # type: ignore[misc, assignment]

from ..auth.unified_auth import unified_auth, SecurityTier
from ..auth.tool_security import get_tool_tier, user_meets_tier_requirement

logger = logging.getLogger(__name__)


@dataclass
class ToolDefinition:
    """Unified tool definition descriptor."""
    name: str
    handler: Callable[..., Any]
    description: str
    parameters: Dict[str, Any]
    tier: str  # stored as string for easy JSON exposure


class TransportWrapper:
    """Ensures tool parity across all transports.

    Usage:
        wrapper = TransportWrapper(server)
        wrapper.register_tool("search_code", handler, "...", {...})
        tools = await wrapper.list_tools(user_tier="public")
        result = await wrapper.execute_tool("search_code", {"query":"..."}, auth_token="...")

    Notes:
        - Authorization is enforced uniformly via unified_auth.require_auth(tier)
        - Transport-specific kwargs ('request', 'auth_token', 'user') are stripped
          before invoking original handlers to preserve tool signatures
    """

    def __init__(self, server: Any):
        self.server = server
        self.tools: Dict[str, ToolDefinition] = {}

    def register_tool(
        self,
        name: str,
        handler: Callable[..., Any],
        description: str,
        parameters: Dict[str, Any],
    ) -> None:
        """Register a tool for all transports with unified tier enforcement."""
        tier_enum: SecurityTier = get_tool_tier(name)

        @unified_auth.require_auth(tier_enum)
        async def wrapped_handler(**kwargs: Any) -> Any:
            # Remove transport-specific params that tools don't declare
            kwargs.pop("user", None)
            kwargs.pop("auth_token", None)
            kwargs.pop("request", None)

            # If the original handler expects a FastMCP Context (commonly named 'ctx'),
            # inject a placeholder when not provided so HTTP/SSE paths don't fail.
            try:
                import inspect
                sig = inspect.signature(handler)
                if 'ctx' in sig.parameters and 'ctx' not in kwargs:
                    kwargs['ctx'] = None  # Tools that need it should guard for None
            except Exception:
                pass

            if iscoroutinefunction(handler):
                return await handler(**kwargs)  # type: ignore[arg-type]
            # Run sync handler in thread to avoid blocking event loop
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, lambda: handler(**kwargs))  # type: ignore[misc]

        self.tools[name] = ToolDefinition(
            name=name,
            handler=wrapped_handler,
            description=description,
            parameters=parameters,
            tier=tier_enum.value,
        )
        logger.debug("Registered tool '%s' with tier '%s'", name, tier_enum.value)

    async def list_tools(self, user_tier: str = "public") -> List[Dict[str, Any]]:
        """List available tools for a user tier."""
        try:
            user_tier_enum = SecurityTier(user_tier)
        except Exception:
            user_tier_enum = SecurityTier.PUBLIC

        visible: List[Dict[str, Any]] = []
        for tool in self.tools.values():
            tool_tier_enum = SecurityTier(tool.tier)
            if user_meets_tier_requirement(user_tier_enum, tool_tier_enum):
                visible.append(
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                        "tier": tool.tier,
                    }
                )
        return visible

    async def execute_tool(
        self,
        tool_name: str,
        params: Dict[str, Any],
        auth_token: Optional[str] = None,
        request: Optional[Request] = None,
    ) -> Any:
        """Execute a registered tool with consistent auth and behavior."""
        if tool_name not in self.tools:
            raise ValueError(f"Tool '{tool_name}' not found")

        tool = self.tools[tool_name]

        # Provide auth context to the decorator via kwargs
        exec_params = dict(params)
        if auth_token:
            exec_params["auth_token"] = auth_token
        if request is not None:
            exec_params["request"] = request

        return await tool.handler(**exec_params)
