"""
Authentication module for mcprag remote server.

Provides Stytch-based authentication and tier-based access control.
"""

from .tool_security import SecurityTier, get_tool_tier, TOOL_SECURITY_MAP
from .stytch_auth import StytchAuthenticator

__all__ = [
    "SecurityTier",
    "get_tool_tier", 
    "TOOL_SECURITY_MAP",
    "StytchAuthenticator"
]