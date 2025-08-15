"""Unified authentication for MCP transports.

NOTE: Not currently used by the running server. Remote HTTP endpoints enforce
auth via `StytchAuthenticator` in `remote_server.py`, and tools are registered
directly with FastMCP. This module is kept to support future transport parity
work (single decorator-based auth across stdio/HTTP/SSE). Safe to remove if
unused.

This module provides consistent authentication across stdio, HTTP, and SSE transports
using Stytch sessions, M2M tokens, and API keys.
"""

import logging
import jwt
from typing import Optional, Dict, Any, Callable, Tuple
from functools import wraps
from datetime import datetime
from fastapi import HTTPException, Header, Request

from enhanced_rag.core.unified_config import UnifiedConfig as Config
from .stytch_auth import StytchAuthenticator, M2MAuthenticator
from .tool_security import SecurityTier, get_tool_tier, user_meets_tier_requirement
from .thread_safe_config import ThreadSafeConfig
from .audit_logger import AuditLogger, AuditEvent
from .circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)


class UnifiedAuthHandler:
    """Unified authentication handler for all MCP transports.
    
    This handler consolidates authentication logic across:
    - stdio: Direct tool invocation with dev mode support
    - HTTP: REST API with Bearer token validation  
    - SSE: Event streaming with persistent auth
    
    It supports multiple authentication methods:
    - Stytch sessions (Consumer auth)
    - M2M JWT tokens (service accounts)
    - API keys (system-managed)
    - Dev mode bypass (local development)
    """
    
    def __init__(self):
        """Initialize unified auth handler."""
        self.stytch = StytchAuthenticator()
        self.m2m = M2MAuthenticator()
        
        # JWT configuration for service tokens
        self.jwt_secret = getattr(Config, 'stytch_secret', None) or getattr(Config, 'JWT_SECRET', 'dev-secret')
        self.jwt_algorithms = ["HS256"]
        
        # API key configuration
        self.api_keys = self._load_api_keys()
        
    async def extract_token(self, **kwargs) -> Optional[str]:
        """Extract authentication token from various sources.
        
        Args:
            **kwargs: May contain request, headers, auth_token, etc.
            
        Returns:
            Token string if found, None otherwise
        """
        # 1. Check for FastAPI Request object (HTTP/SSE)
        request = kwargs.get("request")
        if request and isinstance(request, Request):
            # Check Authorization header
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                return auth_header.replace("Bearer ", "").strip()
            
            # Check for token in query params (SSE fallback)
            if hasattr(request, 'query_params'):
                token = request.query_params.get("token")
                if token:
                    return token
        
        # 2. Check for direct header parameter (HTTP)
        authorization = kwargs.get("authorization")
        if authorization and authorization.startswith("Bearer "):
            return authorization.replace("Bearer ", "").strip()
        
        # 3. Check for auth_token parameter (stdio/direct calls)
        auth_token = kwargs.get("auth_token")
        if auth_token:
            return auth_token
        
        # 4. Check for session_token in kwargs (adapter pattern)
        session_token = kwargs.get("session_token")
        if session_token:
            return session_token
        
        return None
    
    async def validate_token(self, token: Optional[str]) -> Dict[str, Any]:
        """Validate token and return user information.
        
        Tries multiple validation strategies in order:
        1. Dev mode bypass (if enabled)
        2. API key validation
        3. Stytch session validation
        4. M2M JWT validation
        5. Generic JWT validation
        
        Args:
            token: Authentication token
            
        Returns:
            User information dictionary
            
        Raises:
            HTTPException: If token is invalid or missing
        """
        # Dev mode bypass
        if Config.DEV_MODE:
            if not token or token == "dev-mode":
                user_info = {
                    "user_id": "dev",
                    "email": "dev@localhost",
                    "tier": "admin",
                    "mfa_verified": True,
                    "is_dev": True,
                    "session_id": "dev-session"
                }
                AuditLogger.auth_success("dev", "admin", "dev_mode")
                return user_info
        
        if not token:
            AuditLogger.auth_failure("No token provided")
            raise HTTPException(401, "Authentication required")
        
        # Try API key validation
        if token.startswith('sk-') or token.startswith('pk-'):
            user_info = self._validate_api_key(token)
            if user_info:
                AuditLogger.auth_success(user_info['user_id'], user_info['tier'], "api_key")
                return user_info
        
        # Try Stytch session validation
        if self.stytch.enabled:
            try:
                user_info = await self.stytch.get_current_user(f"Bearer {token}")
                if user_info:
                    return user_info
            except Exception as e:
                logger.debug(f"Stytch validation failed: {e}")
        
        # Try M2M JWT validation
        try:
            decoded = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=self.jwt_algorithms,
                options={"verify_exp": True}
            )
            
            # Check if it's an M2M token
            if decoded.get("is_m2m") or decoded.get("client_id"):
                return {
                    "user_id": decoded.get("sub", decoded.get("client_id", "m2m")),
                    "email": decoded.get("email", "service@mcprag"),
                    "tier": decoded.get("tier", "service"),
                    "is_service": True,
                    "mfa_verified": True,
                    "session_id": token[:20]  # Use token prefix as session ID
                }
            
            # Generic JWT token
            return {
                "user_id": decoded.get("sub", "unknown"),
                "email": decoded.get("email", "unknown@mcprag"),
                "tier": decoded.get("tier", "public"),
                "mfa_verified": decoded.get("mfa_verified", False),
                "session_id": token[:20]
            }
            
        except jwt.InvalidTokenError as e:
            logger.debug(f"JWT validation failed: {e}")
        
        AuditLogger.auth_failure("Invalid token", token_prefix=token[:10] if token else None)
        raise HTTPException(401, "Invalid authentication token")
    
    def _load_api_keys(self) -> Dict[str, Dict[str, Any]]:
        """Load API keys from environment or config."""
        api_keys = {}
        
        # Load from environment variables
        # Format: API_KEY_<NAME>=<key>:<tier>
        import os
        for key, value in os.environ.items():
            if key.startswith('API_KEY_'):
                try:
                    api_key, tier = value.split(':')
                    name = key.replace('API_KEY_', '').lower()
                    api_keys[api_key] = {
                        'name': name,
                        'tier': tier,
                        'mfa_verified': tier == 'admin'  # Admin keys always MFA verified
                    }
                except ValueError:
                    logger.warning(f"Invalid API key format for {key}")
        
        # Add default service keys if configured
        if hasattr(Config, 'SERVICE_API_KEY'):
            api_keys[Config.SERVICE_API_KEY] = {
                'name': 'service',
                'tier': 'service',
                'mfa_verified': True
            }
        
        return api_keys
    
    def _validate_api_key(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate API key and return user info."""
        if token not in self.api_keys:
            return None
        
        key_info = self.api_keys[token]
        return {
            "user_id": f"api_{key_info['name']}",
            "email": f"{key_info['name']}@api.mcprag",
            "tier": key_info['tier'],
            "is_api_key": True,
            "mfa_verified": key_info.get('mfa_verified', False),
            "session_id": token[:20]
        }
    
    def require_auth(self, min_tier: SecurityTier = SecurityTier.PUBLIC):
        """Decorator for protecting endpoints/tools with authentication.
        
        Args:
            min_tier: Minimum security tier required
            
        Returns:
            Decorated function that validates authentication
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Extract token from various sources
                token = await self.extract_token(**kwargs)
                
                # Validate token and get user info
                user = await self.validate_token(token)
                
                # Check tier requirements
                user_tier = SecurityTier(user.get("tier", "public"))
                if not user_meets_tier_requirement(user_tier, min_tier):
                    AuditLogger.log(
                        AuditEvent.TIER_DENIED,
                        user_id=user.get('user_id'),
                        tier=user_tier.value,
                        success=False,
                        details={'required_tier': min_tier.value}
                    )
                    raise HTTPException(
                        403,
                        f"Insufficient permissions. Required: {min_tier.value}, "
                        f"User has: {user_tier.value}"
                    )
                
                # Check MFA for admin operations if required
                if min_tier == SecurityTier.ADMIN and ThreadSafeConfig.get('REQUIRE_MFA_FOR_ADMIN', Config.REQUIRE_MFA_FOR_ADMIN):
                    if not user.get("mfa_verified"):
                        raise HTTPException(403, "MFA verification required for admin operations")
                
                # Inject user into kwargs
                kwargs["user"] = user
                
                # Use thread-safe config override for ADMIN_MODE
                if user_tier in (SecurityTier.ADMIN, SecurityTier.SERVICE):
                    with ThreadSafeConfig.override(ADMIN_MODE=True):
                        return await func(*args, **kwargs)
                else:
                    return await func(*args, **kwargs)
            
            return wrapper
        return decorator
    
    async def create_m2m_token(self, client_id: str, client_secret: str) -> Dict[str, Any]:
        """Create M2M token for service accounts.
        
        Args:
            client_id: M2M client ID
            client_secret: M2M client secret
            
        Returns:
            Token response with access_token
        """
        if self.m2m.enabled:
            return await self.m2m.authenticate_m2m(client_id, client_secret)
        
        # Fallback to local JWT generation
        token_payload = {
            "sub": client_id,
            "client_id": client_id,
            "is_m2m": True,
            "tier": "service",
            "exp": int((datetime.utcnow().timestamp())) + 3600,
            "iat": int(datetime.utcnow().timestamp())
        }
        
        token = jwt.encode(token_payload, self.jwt_secret, algorithm="HS256")
        
        return {
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": 3600
        }


# Global instance for easy import
unified_auth = UnifiedAuthHandler()
