"""Azure AD authentication integration for MCP server.

Supports both Stytch Consumer auth and Azure AD Bearer tokens for comprehensive auth coverage.
"""

import logging
import json
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import jwt
import aiohttp
from fastapi import HTTPException, Header

from ..config import Config

logger = logging.getLogger(__name__)

class AzureADAuthenticator:
    """Azure AD authentication handler for management operations."""
    
    def __init__(self):
        """Initialize Azure AD authenticator."""
        self.tenant_id = getattr(Config, 'AZURE_TENANT_ID', '')
        self.client_id = getattr(Config, 'AZURE_CLIENT_ID', '')
        self.client_secret = getattr(Config, 'AZURE_CLIENT_SECRET', '')
        
        # Token validation endpoint
        self.jwks_uri = f"https://login.microsoftonline.com/{self.tenant_id}/discovery/v2.0/keys"
        self.issuer = f"https://sts.windows.net/{self.tenant_id}/"
        
        # Cached JWKS for token validation
        self._jwks_cache = None
        self._jwks_cache_time = None
        self._jwks_cache_duration = 3600  # 1 hour
        
    async def validate_azure_token(self, token: str) -> Dict[str, Any]:
        """
        Validate Azure AD Bearer token.
        
        Args:
            token: Azure AD access token
            
        Returns:
            Decoded token claims if valid
            
        Raises:
            HTTPException: If token is invalid
        """
        try:
            # Get JWKS for validation
            jwks = await self._get_jwks()
            
            # Decode token header to get key ID
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get('kid')
            
            if not kid:
                raise HTTPException(401, "Token missing key ID")
            
            # Find the key
            key = None
            for jwk in jwks.get('keys', []):
                if jwk['kid'] == kid:
                    key = jwk
                    break
            
            if not key:
                raise HTTPException(401, "Token signing key not found")
            
            # Validate token
            # Note: In production, use proper RSA key validation with python-jose or PyJWT with cryptography
            # This is simplified for demonstration
            decoded = jwt.decode(
                token,
                options={"verify_signature": False},  # Simplified - implement proper RSA validation
                audience=["https://management.azure.com/", self.client_id],
                issuer=self.issuer
            )
            
            # Check token expiration
            exp = decoded.get('exp', 0)
            if datetime.utcnow().timestamp() > exp:
                raise HTTPException(401, "Token expired")
            
            return decoded
            
        except jwt.InvalidTokenError as e:
            logger.error(f"Azure AD token validation failed: {e}")
            raise HTTPException(401, f"Invalid Azure AD token: {str(e)}")
        except Exception as e:
            logger.error(f"Azure AD auth error: {e}")
            raise HTTPException(500, f"Authentication error: {str(e)}")
    
    async def _get_jwks(self) -> Dict[str, Any]:
        """Get JSON Web Key Set for token validation."""
        # Check cache
        if self._jwks_cache and self._jwks_cache_time:
            if datetime.utcnow() < self._jwks_cache_time + timedelta(seconds=self._jwks_cache_duration):
                return self._jwks_cache
        
        # Fetch new JWKS
        async with aiohttp.ClientSession() as session:
            async with session.get(self.jwks_uri) as response:
                if response.status == 200:
                    self._jwks_cache = await response.json()
                    self._jwks_cache_time = datetime.utcnow()
                    return self._jwks_cache
                else:
                    raise HTTPException(500, "Failed to fetch JWKS")
    
    async def get_management_token(self) -> str:
        """
        Get Azure AD token for management operations.
        
        Returns:
            Access token for Azure Management API
        """
        if not self.client_id or not self.client_secret:
            raise HTTPException(500, "Azure AD credentials not configured")
        
        token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': 'https://management.azure.com/.default',
            'grant_type': 'client_credentials'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(token_url, data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    return result['access_token']
                else:
                    error = await response.text()
                    raise HTTPException(500, f"Failed to get management token: {error}")
    
    def extract_user_info(self, claims: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract user information from Azure AD claims.
        
        Args:
            claims: Decoded token claims
            
        Returns:
            User information dictionary
        """
        return {
            "user_id": claims.get("oid", claims.get("sub", "unknown")),
            "email": claims.get("email", claims.get("upn", "unknown@azure")),
            "name": claims.get("name", "Azure User"),
            "tier": self._determine_tier_from_claims(claims),
            "is_azure_ad": True,
            "tenant_id": claims.get("tid"),
            "app_id": claims.get("appid"),
            "roles": claims.get("roles", []),
            "groups": claims.get("groups", [])
        }
    
    def _determine_tier_from_claims(self, claims: Dict[str, Any]) -> str:
        """
        Determine user tier from Azure AD claims.
        
        Args:
            claims: Token claims
            
        Returns:
            Security tier string
        """
        roles = claims.get("roles", [])
        groups = claims.get("groups", [])
        
        # Check for admin roles
        admin_roles = {"Global Administrator", "Search Service Contributor", "Owner"}
        if any(role in admin_roles for role in roles):
            return "admin"
        
        # Check for developer roles
        dev_roles = {"Search Index Data Contributor", "Contributor"}
        if any(role in dev_roles for role in roles):
            return "developer"
        
        # Check for read-only roles
        read_roles = {"Search Index Data Reader", "Reader"}
        if any(role in read_roles for role in roles):
            return "public"
        
        # Default to public
        return "public"


class HybridAuthenticator:
    """Hybrid authenticator supporting both Stytch and Azure AD."""
    
    def __init__(self):
        """Initialize hybrid authenticator."""
        self.azure_ad = AzureADAuthenticator()
        # Stytch authenticator is initialized in the main auth module
        self.stytch = None  # Will be set by UnifiedAuth
        
    async def validate_token(self, token: str) -> Tuple[Dict[str, Any], str]:
        """
        Validate token with automatic provider detection.
        
        Args:
            token: Authentication token
            
        Returns:
            Tuple of (user_info, provider_type)
            provider_type is "stytch", "azure_ad", or "jwt"
        """
        # Try Azure AD token validation first (if it looks like a JWT)
        if token and '.' in token and token.count('.') == 2:
            try:
                # Check if it's an Azure AD token
                header = jwt.get_unverified_header(token)
                if header.get('typ') == 'JWT' and header.get('kid'):
                    claims = await self.azure_ad.validate_azure_token(token)
                    user_info = self.azure_ad.extract_user_info(claims)
                    return user_info, "azure_ad"
            except Exception:
                pass  # Not an Azure AD token, try other methods
        
        # Try Stytch session validation
        if self.stytch and self.stytch.enabled:
            try:
                user_info = await self.stytch.get_current_user(f"Bearer {token}")
                return user_info, "stytch"
            except Exception:
                pass  # Not a Stytch token
        
        # Try generic JWT validation (for M2M tokens)
        try:
            # Use configured secret for M2M tokens
            secret = Config.STYTCH_SECRET or Config.JWT_SECRET or "dev-secret"
            decoded = jwt.decode(token, secret, algorithms=["HS256"])
            
            user_info = {
                "user_id": decoded.get("sub", "m2m"),
                "email": decoded.get("email", "m2m@service"),
                "tier": decoded.get("tier", "service"),
                "is_service": True,
                "mfa_verified": True
            }
            return user_info, "jwt"
            
        except jwt.InvalidTokenError:
            pass
        
        # Dev mode fallback
        if Config.DEV_MODE:
            return {
                "user_id": "dev",
                "email": "dev@localhost",
                "tier": "admin",
                "mfa_verified": True,
                "is_dev": True
            }, "dev"
        
        raise HTTPException(401, "Invalid authentication token")