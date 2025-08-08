"""Unified authentication entrypoint for all MCP transports.

This module provides a stable import path (mcprag.auth.unified_auth)
and delegates to UnifiedAuthHandler implemented in unified_auth_v2.py.
STATUS: Compatibility stub; not currently wired into runtime. It preserves
compatibility with docs and wrappers that expect a
'unified_auth' global and a 'UnifiedAuth' class with a require_auth decorator.
"""

from __future__ import annotations
import logging
from typing import Any, Callable, Optional, Dict

from .unified_auth_v2 import UnifiedAuthHandler
from .tool_security import SecurityTier

logger = logging.getLogger(__name__)


class UnifiedAuth(UnifiedAuthHandler):
    """Compatibility wrapper extending UnifiedAuthHandler.

    No additional behavior; exists to provide the class name referenced
    in guides and wrappers while reusing the underlying implementation.
    """

    pass


# Global instance used by transport wrappers and tools
unified_auth = UnifiedAuth()

__all__ = ("UnifiedAuth", "unified_auth", "SecurityTier")
