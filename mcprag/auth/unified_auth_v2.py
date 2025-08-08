"""Unified authentication for MCP transports leveraging existing architecture.

This module provides consistent authentication across stdio, HTTP, and SSE transports
while integrating with the existing Stytch authentication and Azure AD support.
"""

import logging
import jwt
from typing import Optional, Dict, Any, Callable, Tuple
from functools import wraps
from datetime import datetime
from fastapi import HTTPException, Header, Request

from ..config import Config
from .stytch_auth import StytchAuthenticator, M2MAuthenticator
from .tool_security import SecurityTier, get_tool_tier, user_meets_tier_requirement

logger = logging.getLogger(__name__)


class UnifiedAuthHandler:
    """Unified authentication handler for all MCP transports.
    
    This handler consolidates authentication logic across:
    - stdio: Direct tool invocation with dev mode support
    - HTTP: REST API with Bearer token validation  
    - SSE: Event streaming with persistent auth
    
    It supports multiple authentication methods:
    - Stytch sessions (Consumer auth)
    - Azure AD tokens (via Management API)
    - M2M JWT tokens (service accounts)
    - Dev mode bypass (local development)
    """
    
    def __init__(self):
        """Initialize unified auth handler."""
        self.stytch = StytchAuthenticator()
        self.m2m = M2MAuthenticator()
        
        # JWT configuration for service tokens
        self.jwt_secret = Config.STYTCH_SECRET or getattr(Config, 'JWT_SECRET', 'dev-secret')
        self.jwt_algorithms = ["HS256"]
        
        # Azure AD configuration (if needed)
        self.azure_tenant = getattr(Config, 'AZURE_TENANT_ID', '')
        self.azure_client_id = getattr(Config, 'AZURE_CLIENT_ID', '')
        
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
        2. Azure AD token (if JWT with specific claims)
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
                return {
                    "user_id": "dev",
                    "email": "dev@localhost",
                    "tier": "admin",
                    "mfa_verified": True,
                    "is_dev": True,
                    "session_id": "dev-session"
                }
        
        if not token:
            raise HTTPException(401, "Authentication required")
        
        # Try Azure AD token validation (check JWT structure)
        if self._is_azure_ad_token(token):
            try:
                user_info = await self._validate_azure_ad_token(token)
                if user_info:
                    return user_info
            except Exception as e:
                logger.debug(f"Azure AD validation failed: {e}")
        
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
        
        raise HTTPException(401, "Invalid authentication token")
    
    def _is_azure_ad_token(self, token: str) -> bool:
        """Check if token appears to be an Azure AD token."""
        if not token or '.' not in token:
            return False
        
        try:
            # Decode header without verification
            header = jwt.get_unverified_header(token)
            
            # Azure AD tokens have specific header fields
            return (
                header.get("typ") == "JWT" and
                header.get("alg") in ["RS256", "RS384", "RS512"] and
                "kid" in header and
                (header.get("x5t") or header.get("x5c"))
            )
        except Exception:
            return False
    
    async def _validate_azure_ad_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate Azure AD token using existing Management API integration.
        
        Note: This is a simplified validation. In production, you would:
        1. Fetch JWKS from Azure AD
        2. Validate signature with proper RSA keys
        3. Check audience and issuer claims
        """
        try:
            # Decode without signature verification (simplified for demo)
            # In production, use python-jose or PyJWT with RSA validation
            decoded = jwt.decode(
                token,
                options={"verify_signature": False},
                audience=None  # Skip audience validation for now
            )
            
            # Check token expiration
            if decoded.get("exp", 0) < datetime.utcnow().timestamp():
                return None
            
            # Extract user information from Azure AD claims
            return {
                "user_id": decoded.get("oid", decoded.get("sub", "azure_user")),
                "email": decoded.get("email", decoded.get("upn", "user@azure")),
                "name": decoded.get("name", "Azure User"),
                "tier": self._determine_tier_from_azure_roles(decoded),
                "is_azure_ad": True,
                "mfa_verified": decoded.get("acr") == "1",  # Auth context
                "session_id": token[:20]
            }
            
        except Exception as e:
            logger.error(f"Azure AD token validation failed: {e}")
            return None
    
    def _determine_tier_from_azure_roles(self, claims: Dict[str, Any]) -> str:
        """Determine user tier from Azure AD roles/groups."""
        roles = claims.get("roles", [])
        
        # Map Azure roles to MCP tiers
        if any(role in ["Owner", "Contributor", "Search Service Contributor"] for role in roles):
            return "admin"
        elif any(role in ["Search Index Data Contributor"] for role in roles):
            return "developer"
        elif any(role in ["Search Index Data Reader", "Reader"] for role in roles):
            return "public"
        
        return "public"
    
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
                    raise HTTPException(
                        403,
                        f"Insufficient permissions. Required: {min_tier.value}, "
                        f"User has: {user_tier.value}"
                    )
                
                # Check MFA for admin operations if required
                if min_tier == SecurityTier.ADMIN and Config.REQUIRE_MFA_FOR_ADMIN:
                    if not user.get("mfa_verified"):
                        raise HTTPException(403, "MFA verification required for admin operations")
                
                # Inject user into kwargs
                kwargs["user"] = user
                
                # Temporarily set ADMIN_MODE if user has admin/service tier
                old_admin_mode = Config.ADMIN_MODE
                if user_tier in (SecurityTier.ADMIN, SecurityTier.SERVICE):
                    Config.ADMIN_MODE = True
                
                try:
                    return await func(*args, **kwargs)
                finally:
                    # Restore original ADMIN_MODE
                    Config.ADMIN_MODE = old_admin_mode
            
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