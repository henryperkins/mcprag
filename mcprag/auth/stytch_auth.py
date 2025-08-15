"""
Stytch authentication integration for mcprag.

Provides magic link authentication with tier-based access control.
"""

import os
import json
import secrets
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from fastapi import HTTPException, Header

from enhanced_rag.core.unified_config import UnifiedConfig as Config
from .tool_security import SecurityTier

logger = logging.getLogger(__name__)

# Import Redis and Stytch conditionally
try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available - session storage disabled")

try:
    import stytch
    STYTCH_AVAILABLE = True
except ImportError:
    STYTCH_AVAILABLE = False
    logger.warning("Stytch SDK not available - authentication will be disabled")

class StytchAuthenticator:
    """Stytch authentication handler for mcprag."""
    
    def __init__(self):
        """Initialize Stytch client."""
        self.project_id = getattr(Config, 'stytch_project_id', None)
        self.secret = getattr(Config, 'stytch_secret', None)
        self.environment = getattr(Config, 'stytch_env', 'test')
        
        # Check if Stytch is configured and available
        if not STYTCH_AVAILABLE:
            logger.warning("Stytch SDK not installed - auth disabled")
            self.enabled = False
            self.client = None
        elif not self.project_id or not self.secret:
            logger.warning("Stytch credentials not configured - auth disabled")
            self.enabled = False
            self.client = None
        else:
            self.enabled = True
            self.client = stytch.Client(
                project_id=self.project_id,
                secret=self.secret,
                environment=self.environment
            )
        
        self.redis: Optional[Any] = None
        self.session_duration_minutes = getattr(Config, 'SESSION_DURATION_MINUTES', 480)
        self.base_url = getattr(Config, 'BASE_URL', 'http://localhost:8001')
    
    async def initialize(self, redis_client: Optional[Any] = None):
        """
        Initialize with Redis client.
        
        Args:
            redis_client: Optional Redis client for session storage
        """
        if REDIS_AVAILABLE and redis_client:
            self.redis = redis_client
            logger.info("Stytch authenticator initialized with Redis")
        else:
            logger.info("Stytch authenticator initialized without Redis (in-memory sessions)")
            # Use in-memory storage as fallback
            self._sessions = {}
    
    async def send_magic_link(self, email: str) -> Dict[str, Any]:
        """
        Send magic link email for authentication.
        
        Args:
            email: User's email address
            
        Returns:
            Status and user information
        """
        if not self.enabled:
            raise HTTPException(503, "Authentication not configured")
        
        # Determine tier based on email domain or configuration
        tier = await self._determine_user_tier(email)
        
        try:
            # Send magic link through Stytch
            response = self.client.magic_links.email.login_or_create(
                email=email,
                login_magic_link_url=f"{self.base_url}/auth/callback",
                signup_magic_link_url=f"{self.base_url}/auth/callback",
                login_expiration_minutes=15,
                signup_expiration_minutes=15,
                attributes={
                    "name": email.split("@")[0],
                    "trusted_metadata": {
                        "tier": tier.value,
                        "created_via": "mcprag_remote"
                    }
                }
            )
            
            return {
                "status": "sent",
                "user_id": response.user_id,
                "request_id": response.request_id,
                "tier": tier.value,
                "message": f"Magic link sent to {email}. Check your email to complete authentication."
            }
            
        except Exception as e:
            logger.error(f"Failed to send magic link: {e}")
            raise HTTPException(500, f"Failed to send authentication email: {str(e)}")
    
    async def complete_authentication(self, token: str) -> Dict[str, Any]:
        """
        Complete magic link authentication.
        
        Args:
            token: Authentication token from magic link
            
        Returns:
            Session information
        """
        if not self.enabled:
            # In development/test mode without Stytch, create mock session
            if getattr(Config, 'DEV_MODE', False):
                session_id = secrets.token_urlsafe(32)
                session_data = {
                    "session_id": session_id,
                    "user_id": "dev_user",
                    "email": "dev@local",
                    "tier": "admin",
                    "expires_at": (datetime.utcnow() + timedelta(minutes=self.session_duration_minutes)).isoformat(),
                    "created_at": datetime.utcnow().isoformat(),
                    "mfa_verified": True
                }
                
                # Store session
                await self._store_session(session_id, session_data)
                
                return {
                    "token": session_id,
                    "user_id": "dev_user",
                    "email": "dev@local",
                    "tier": "admin",
                    "expires_at": session_data["expires_at"],
                    "mfa_required": False
                }
            
            raise HTTPException(503, "Authentication not configured")
        
        try:
            # Authenticate with Stytch
            response = self.client.magic_links.authenticate(
                token=token,
                session_duration_minutes=self.session_duration_minutes
            )
            
            # Extract user data
            user = response.user
            stytch_session = response.session
            
            # Get tier from trusted metadata
            tier = user.trusted_metadata.get("tier", "public")
            
            # Create internal session
            session_id = secrets.token_urlsafe(32)
            session_data = {
                "session_id": session_id,
                "user_id": user.user_id,
                "email": user.emails[0].email if user.emails else "unknown",
                "tier": tier,
                "stytch_session_token": stytch_session.session_token,
                "stytch_session_id": stytch_session.session_id,
                "expires_at": stytch_session.expires_at.isoformat(),
                "created_at": datetime.utcnow().isoformat(),
                "mfa_verified": False
            }
            
            # Store session
            await self._store_session(session_id, session_data)
            
            return {
                "token": session_id,
                "user_id": user.user_id,
                "email": session_data["email"],
                "tier": tier,
                "expires_at": stytch_session.expires_at.isoformat(),
                "mfa_required": tier == "admin" and getattr(Config, 'REQUIRE_MFA_FOR_ADMIN', True)
            }
            
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise HTTPException(401, f"Authentication failed: {str(e)}")
    
    async def get_current_user(self, authorization: str = Header(None)) -> Dict[str, Any]:
        """
        FastAPI dependency to get current user from session.
        
        Args:
            authorization: Authorization header value
            
        Returns:
            User session data
        """
        # Check for dev mode first
        if getattr(Config, 'DEV_MODE', False):
            # Dev mode - return default admin user
            return {
                "user_id": "dev",
                "email": "dev@localhost",
                "tier": "admin",
                "session_id": "dev-session",
                "mfa_verified": True
            }
        
        if not self.enabled:
            # When auth is not configured, do NOT silently grant admin access.
            # Only allow bypass in explicit DEV_MODE; otherwise require proper setup.
            raise HTTPException(503, "Authentication not configured")
        
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(401, "Missing or invalid authorization header")
        
        token = authorization.replace("Bearer ", "").strip()
        
        # Get session
        session_data = await self._get_session(token)
        
        if not session_data:
            raise HTTPException(401, "Invalid or expired session")
        
        # Check if session expired
        expires_at = datetime.fromisoformat(session_data["expires_at"])
        if datetime.utcnow() > expires_at:
            await self._delete_session(token)
            raise HTTPException(401, "Session expired")
        
        return session_data
    
    async def verify_totp(self, user_id: str, totp_code: str) -> Dict[str, Any]:
        """
        Verify TOTP MFA code.
        
        Args:
            user_id: User ID
            totp_code: TOTP code from authenticator app
            
        Returns:
            Verification result
        """
        if not self.enabled:
            if getattr(Config, 'DEV_MODE', False):
                return {"verified": True, "message": "MFA not required in development mode"}
            raise HTTPException(503, "Authentication not configured")
        
        try:
            response = self.client.totps.authenticate(
                user_id=user_id,
                totp_code=totp_code
            )
            
            return {
                "verified": True,
                "user_id": response.user_id,
                "message": "MFA verification successful"
            }
            
        except Exception as e:
            logger.error(f"MFA verification failed: {e}")
            return {"verified": False, "error": str(e)}
    
    async def update_session_mfa(self, session_id: str, mfa_verified: bool):
        """
        Update session MFA status.
        
        Args:
            session_id: Session ID
            mfa_verified: Whether MFA was verified
        """
        session_data = await self._get_session(session_id)
        
        if session_data:
            session_data["mfa_verified"] = mfa_verified
            await self._store_session(session_id, session_data)
    
    async def _determine_user_tier(self, email: str) -> SecurityTier:
        """
        Determine user tier based on email or configuration.
        
        Args:
            email: User's email address
            
        Returns:
            Security tier for the user
        """
        # Check admin emails
        admin_emails = getattr(Config, 'ADMIN_EMAILS', '').split(",") if hasattr(Config, 'ADMIN_EMAILS') else []
        admin_emails = [e.strip() for e in admin_emails if e.strip()]
        if email in admin_emails:
            return SecurityTier.ADMIN
        
        # Check developer domains
        dev_domains = getattr(Config, 'DEVELOPER_DOMAINS', '').split(",") if hasattr(Config, 'DEVELOPER_DOMAINS') else []
        dev_domains = [d.strip() for d in dev_domains if d.strip()]
        
        if "@" in email:
            domain = email.split("@")[1]
            if domain in dev_domains:
                return SecurityTier.DEVELOPER
        
        # Default to public
        return SecurityTier.PUBLIC
    
    async def _store_session(self, session_id: str, session_data: Dict[str, Any]):
        """Store session data."""
        if self.redis:
            # Store in Redis with TTL
            await self.redis.setex(
                f"session:{session_id}",
                self.session_duration_minutes * 60,
                json.dumps(session_data)
            )
        else:
            # Store in memory (fallback)
            self._sessions[session_id] = session_data
    
    async def _get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data."""
        if self.redis:
            # Get from Redis
            data = await self.redis.get(f"session:{session_id}")
            return json.loads(data) if data else None
        else:
            # Get from memory
            return self._sessions.get(session_id)
    
    async def _delete_session(self, session_id: str):
        """Delete session data."""
        if self.redis:
            await self.redis.delete(f"session:{session_id}")
        else:
            self._sessions.pop(session_id, None)

class M2MAuthenticator:
    """Machine-to-machine authentication for services."""
    
    def __init__(self):
        """Initialize M2M authenticator."""
        self.enabled = STYTCH_AVAILABLE and getattr(Config, 'STYTCH_PROJECT_ID', None)
        if self.enabled:
            self.client = stytch.Client(
                project_id=Config.STYTCH_PROJECT_ID,
                secret=Config.STYTCH_SECRET,
                environment=getattr(Config, 'STYTCH_ENV', 'test')
            )
    
    async def create_service_account(self, name: str, allowed_tools: list) -> Dict[str, Any]:
        """
        Create M2M service account credentials.
        
        Args:
            name: Service account name
            allowed_tools: List of allowed tool names
            
        Returns:
            Service account credentials
        """
        if not self.enabled:
            # Return mock credentials only in development mode
            if getattr(Config, 'DEV_MODE', False):
                return {
                    "client_id": f"dev_{name}",
                    "client_secret": secrets.token_urlsafe(32),
                    "allowed_tools": allowed_tools,
                    "message": "Development mode - credentials are mock"
                }
            raise HTTPException(503, "M2M authentication not configured")
        
        try:
            response = self.client.m2m.clients.create(
                client_name=name,
                client_description=f"Service account for {name}",
                trusted_metadata={"allowed_tools": allowed_tools}
            )
            
            return {
                "client_id": response.m2m_client.client_id,
                "client_secret": response.m2m_client.client_secret,
                "allowed_tools": allowed_tools
            }
        except Exception as e:
            logger.error(f"Failed to create service account: {e}")
            raise HTTPException(500, f"Failed to create service account: {str(e)}")
    
    async def authenticate_m2m(self, client_id: str, client_secret: str) -> Dict[str, Any]:
        """
        Authenticate service account.
        
        Args:
            client_id: M2M client ID
            client_secret: M2M client secret
            
        Returns:
            Access token and metadata
        """
        if not self.enabled:
            # Return mock token only in development mode
            if getattr(Config, 'DEV_MODE', False):
                return {
                    "access_token": secrets.token_urlsafe(32),
                    "expires_in": 3600,
                    "tier": SecurityTier.SERVICE.value,
                    "message": "Development mode - token is mock"
                }
            raise HTTPException(503, "M2M authentication not configured")
        
        try:
            response = self.client.m2m.token.authenticate(
                client_id=client_id,
                client_secret=client_secret,
                scopes=["read:mcp", "write:mcp"]
            )
            
            return {
                "access_token": response.access_token,
                "expires_in": response.expires_in,
                "tier": SecurityTier.SERVICE.value
            }
        except Exception as e:
            logger.error(f"M2M authentication failed: {e}")
            raise HTTPException(401, f"Service account authentication failed: {str(e)}")
