# MCPRAGRemote Server Implementation Plan

## Executive Summary
Transform the existing mcprag MCP server into a secure, scalable remote service with Stytch authentication while leveraging its existing FastMCP framework, component architecture, and transport capabilities.

## Current Architecture Analysis

### Existing Strengths to Leverage
- **FastMCP Framework**: Already supports stdio, SSE, and streamable-http transports
- **Component-based Architecture**: Modular design with optional components
- **Admin Mode**: Existing `MCP_ADMIN_MODE` flag for dangerous operations
- **Async Support**: Built-in async component lifecycle management
- **Tool Organization**: Tools already categorized in separate modules
- **REST API Ready**: Some REST API support already exists

### Key Components to Extend
1. **MCPServer Class** (`mcprag/server.py`): Core orchestrator
2. **FastMCP Instance**: Transport and routing handler
3. **Tool Modules** (`mcprag/mcp/tools/`): Already organized by function
4. **Config System** (`mcprag/config.py`): Environment-based configuration

## Phase 1: Security Classification & Tool Mapping

### Tool Security Tiers (Based on CLAUDE.md)

```python
# mcprag/auth/tool_security.py
from enum import Enum
from typing import Set, Dict

class SecurityTier(Enum):
    PUBLIC = "public"      # Read-only, no sensitive data
    DEVELOPER = "developer" # Read/write non-destructive
    ADMIN = "admin"        # Destructive operations
    SERVICE = "service"    # M2M automation

# Map existing mcprag tools to security tiers
TOOL_SECURITY_MAP: Dict[str, SecurityTier] = {
    # Search Tools (PUBLIC)
    "search_code": SecurityTier.PUBLIC,
    "search_code_raw": SecurityTier.PUBLIC,
    "search_microsoft_docs": SecurityTier.PUBLIC,
    
    # Analysis Tools (PUBLIC)
    "explain_ranking": SecurityTier.PUBLIC,
    "preview_query_processing": SecurityTier.PUBLIC,
    "health_check": SecurityTier.PUBLIC,
    "index_status": SecurityTier.PUBLIC,
    "cache_stats": SecurityTier.PUBLIC,
    
    # Generation Tools (DEVELOPER)
    "generate_code": SecurityTier.DEVELOPER,
    "analyze_context": SecurityTier.DEVELOPER,
    
    # Feedback Tools (DEVELOPER)
    "submit_feedback": SecurityTier.DEVELOPER,
    "track_search_click": SecurityTier.DEVELOPER,
    "track_search_outcome": SecurityTier.DEVELOPER,
    
    # Admin Tools (ADMIN) - Already respect MCP_ADMIN_MODE
    "index_rebuild": SecurityTier.ADMIN,
    "github_index_repo": SecurityTier.ADMIN,
    "manage_index": SecurityTier.ADMIN,
    "manage_documents": SecurityTier.ADMIN,
    "manage_indexer": SecurityTier.ADMIN,
    "create_datasource": SecurityTier.ADMIN,
    "create_skillset": SecurityTier.ADMIN,
    "rebuild_index": SecurityTier.ADMIN,
    "configure_semantic_search": SecurityTier.ADMIN,
    "cache_clear": SecurityTier.ADMIN,
    "index_repository": SecurityTier.ADMIN,
    "index_changed_files": SecurityTier.ADMIN,
    "backup_index_schema": SecurityTier.ADMIN,
    "clear_repository_documents": SecurityTier.ADMIN,
    "get_service_info": SecurityTier.ADMIN,
}

def get_tool_tier(tool_name: str) -> SecurityTier:
    """Get security tier for a tool, defaulting to ADMIN for unknown tools."""
    return TOOL_SECURITY_MAP.get(tool_name, SecurityTier.ADMIN)
```

## Phase 2: Remote Server Extension

### 2.1 Extend MCPServer for Remote Operation

```python
# mcprag/remote_server.py
"""
Remote-capable MCP Server extending the existing MCPServer.

Leverages existing FastMCP transport capabilities (SSE, streamable-http)
and adds authentication layer.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, Literal
from fastapi import FastAPI, Request, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
import redis.asyncio as aioredis

from .server import MCPServer
from .auth.stytch_auth import StytchAuthenticator
from .auth.tool_security import get_tool_tier, SecurityTier
from .config import Config

logger = logging.getLogger(__name__)

class RemoteMCPServer(MCPServer):
    """Extended MCP Server with remote capabilities."""
    
    def __init__(self):
        """Initialize remote MCP server."""
        super().__init__()
        
        # Create FastAPI app for HTTP endpoints
        self.app = FastAPI(
            title="MCPRAG Remote Server",
            version=self.version,
            description="Remote access to Azure Code Search MCP tools"
        )
        
        # Setup CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=Config.ALLOWED_ORIGINS.split(","),
            allow_credentials=True,
            allow_methods=["GET", "POST"],
            allow_headers=["*"],
        )
        
        # Initialize auth
        self.auth = StytchAuthenticator()
        
        # Setup routes
        self._setup_routes()
        
        # Redis for session management
        self.redis: Optional[aioredis.Redis] = None
    
    async def startup(self):
        """Startup hook for FastAPI."""
        # Initialize Redis
        self.redis = await aioredis.from_url(
            Config.REDIS_URL or "redis://localhost:6379"
        )
        
        # Start async components (from parent)
        await self.start_async_components()
        
        # Initialize auth
        await self.auth.initialize(self.redis)
        
        logger.info("Remote MCP Server started successfully")
    
    async def shutdown(self):
        """Shutdown hook for FastAPI."""
        # Cleanup async components
        await self.cleanup_async_components()
        
        # Close Redis
        if self.redis:
            await self.redis.close()
        
        logger.info("Remote MCP Server shutdown complete")
    
    def _setup_routes(self):
        """Setup FastAPI routes."""
        
        @self.app.on_event("startup")
        async def on_startup():
            await self.startup()
        
        @self.app.on_event("shutdown")
        async def on_shutdown():
            await self.shutdown()
        
        # Health check (unauthenticated)
        @self.app.get("/health")
        async def health():
            """Health check endpoint."""
            components = {
                "enhanced_search": self.enhanced_search is not None,
                "pipeline": self.pipeline is not None,
                "cache_manager": self.cache_manager is not None,
                "redis": self.redis is not None,
            }
            
            # Use existing health_check tool if available
            if hasattr(self, 'health_check'):
                detailed = await self.health_check()
                return {
                    "status": "healthy",
                    "version": self.version,
                    "components": components,
                    "detailed": detailed
                }
            
            return {
                "status": "healthy",
                "version": self.version,
                "components": components
            }
        
        # Authentication endpoints
        @self.app.post("/auth/login")
        async def login(email: str):
            """Send magic link."""
            return await self.auth.send_magic_link(email)
        
        @self.app.get("/auth/callback")
        async def auth_callback(token: str):
            """Handle Stytch callback."""
            return await self.auth.complete_authentication(token)
        
        @self.app.post("/auth/verify-mfa")
        async def verify_mfa(
            user_id: str,
            totp_code: str,
            authorization: str = Header(None)
        ):
            """Verify MFA for admin operations."""
            user = await self.auth.get_current_user(authorization)
            if user["user_id"] != user_id:
                raise HTTPException(403, "User mismatch")
            
            result = await self.auth.verify_totp(user_id, totp_code)
            if result["verified"]:
                # Update session with MFA status
                await self.auth.update_session_mfa(user["session_id"], True)
            
            return result
        
        # Tool execution endpoint
        @self.app.post("/mcp/tool/{tool_name}")
        async def execute_tool(
            tool_name: str,
            request: Request,
            user=Depends(self.auth.get_current_user)
        ):
            """Execute MCP tool with auth checks."""
            # Check if tool exists
            if not self._tool_exists(tool_name):
                raise HTTPException(404, f"Tool {tool_name} not found")
            
            # Check permissions
            required_tier = get_tool_tier(tool_name)
            user_tier = SecurityTier(user.get("tier", "public"))
            
            if not self._user_has_access(user_tier, required_tier):
                raise HTTPException(
                    403, 
                    f"Insufficient permissions. Required: {required_tier.value}, "
                    f"User has: {user_tier.value}"
                )
            
            # Additional MFA check for admin tools
            if required_tier == SecurityTier.ADMIN and not user.get("mfa_verified"):
                raise HTTPException(403, "MFA verification required for admin operations")
            
            # Parse request body
            body = await request.json()
            
            # Execute tool through existing MCP infrastructure
            try:
                # Set ADMIN_MODE for the request context if user is admin
                old_admin_mode = Config.ADMIN_MODE
                if user_tier == SecurityTier.ADMIN:
                    Config.ADMIN_MODE = True
                
                # Execute through existing tool infrastructure
                result = await self._execute_tool_async(tool_name, body)
                
                # Restore ADMIN_MODE
                Config.ADMIN_MODE = old_admin_mode
                
                # Audit log
                await self._audit_log(user, tool_name, body, result)
                
                return result
                
            except Exception as e:
                logger.error(f"Tool execution failed: {tool_name}", exc_info=e)
                raise HTTPException(500, f"Tool execution failed: {str(e)}")
        
        # SSE endpoint for streaming
        @self.app.get("/mcp/sse")
        async def sse_endpoint(
            request: Request,
            user=Depends(self.auth.get_current_user)
        ):
            """SSE endpoint for streaming responses."""
            async def event_generator():
                """Generate SSE events."""
                # Create a queue for this user's events
                queue = asyncio.Queue()
                
                # Register queue for user
                user_id = user["user_id"]
                self._user_queues[user_id] = queue
                
                try:
                    while True:
                        # Get event from queue
                        event = await queue.get()
                        
                        # Check if client disconnected
                        if await request.is_disconnected():
                            break
                        
                        yield {
                            "event": event.get("type", "message"),
                            "data": event.get("data", {})
                        }
                finally:
                    # Cleanup
                    del self._user_queues[user_id]
            
            return EventSourceResponse(event_generator())
    
    def _tool_exists(self, tool_name: str) -> bool:
        """Check if tool exists in MCP server."""
        # Check through FastMCP's registered tools
        return hasattr(self.mcp, f"tool_{tool_name}")
    
    def _user_has_access(self, user_tier: SecurityTier, required_tier: SecurityTier) -> bool:
        """Check if user tier has access to required tier."""
        tier_hierarchy = {
            SecurityTier.PUBLIC: 0,
            SecurityTier.DEVELOPER: 1,
            SecurityTier.ADMIN: 2,
            SecurityTier.SERVICE: 2,  # Service accounts have admin access
        }
        
        return tier_hierarchy.get(user_tier, 0) >= tier_hierarchy.get(required_tier, 2)
    
    async def _execute_tool_async(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool asynchronously through existing infrastructure."""
        # Get the tool method from FastMCP
        tool_method = getattr(self.mcp, f"tool_{tool_name}", None)
        if not tool_method:
            raise ValueError(f"Tool {tool_name} not found")
        
        # Execute tool
        result = await tool_method(**params)
        
        return result
    
    async def _audit_log(self, user: dict, tool: str, params: dict, result: dict):
        """Log tool execution for audit."""
        # Use existing monitoring/logging infrastructure if available
        if self.feedback_collector:
            await self.feedback_collector.track_tool_usage(
                user_id=user["user_id"],
                tool=tool,
                params=params,
                result_status="success" if result.get("success") else "failure"
            )
        
        logger.info(
            f"Tool execution: user={user['email']}, tool={tool}, "
            f"tier={user['tier']}, success={result.get('success', False)}"
        )


def create_remote_server() -> RemoteMCPServer:
    """Create remote MCP server instance."""
    return RemoteMCPServer()


# For running with uvicorn
app = create_remote_server().app

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        app,
        host=Config.HOST or "0.0.0.0",
        port=Config.PORT or 8001,
        log_level=Config.LOG_LEVEL.lower()
    )
```

### 2.2 Stytch Authentication Integration

```python
# mcprag/auth/stytch_auth.py
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

import stytch
from stytch.api import sessions
from fastapi import HTTPException, Header
import redis.asyncio as aioredis

from ..config import Config
from .tool_security import SecurityTier

logger = logging.getLogger(__name__)

class StytchAuthenticator:
    """Stytch authentication handler for mcprag."""
    
    def __init__(self):
        """Initialize Stytch client."""
        self.project_id = Config.STYTCH_PROJECT_ID
        self.secret = Config.STYTCH_SECRET
        self.environment = Config.STYTCH_ENV or "test"
        
        if not self.project_id or not self.secret:
            logger.warning("Stytch credentials not configured - auth disabled")
            self.enabled = False
            return
        
        self.enabled = True
        self.client = stytch.Client(
            project_id=self.project_id,
            secret=self.secret,
            environment=self.environment
        )
        
        self.redis: Optional[aioredis.Redis] = None
        self.session_duration_minutes = Config.SESSION_DURATION_MINUTES or 480
    
    async def initialize(self, redis_client: aioredis.Redis):
        """Initialize with Redis client."""
        self.redis = redis_client
        logger.info("Stytch authenticator initialized")
    
    async def send_magic_link(self, email: str) -> Dict[str, Any]:
        """Send magic link email."""
        if not self.enabled:
            raise HTTPException(503, "Authentication not configured")
        
        # Determine tier based on email domain or existing user
        tier = await self._determine_user_tier(email)
        
        try:
            # Send magic link
            response = self.client.magic_links.email.login_or_create(
                email=email,
                login_magic_link_url=f"{Config.BASE_URL}/auth/callback",
                signup_magic_link_url=f"{Config.BASE_URL}/auth/callback",
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
                "tier": tier.value
            }
            
        except Exception as e:
            logger.error(f"Failed to send magic link: {e}")
            raise HTTPException(500, "Failed to send authentication email")
    
    async def complete_authentication(self, token: str) -> Dict[str, Any]:
        """Complete magic link authentication."""
        if not self.enabled:
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
            
            # Store in Redis
            if self.redis:
                await self.redis.setex(
                    f"session:{session_id}",
                    self.session_duration_minutes * 60,
                    json.dumps(session_data)
                )
            
            return {
                "token": session_id,
                "user_id": user.user_id,
                "email": session_data["email"],
                "tier": tier,
                "expires_at": stytch_session.expires_at.isoformat(),
                "mfa_required": tier == "admin"
            }
            
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise HTTPException(401, "Authentication failed")
    
    async def get_current_user(self, authorization: str = Header(None)) -> Dict[str, Any]:
        """FastAPI dependency to get current user from session."""
        if not self.enabled:
            # Auth disabled - return default user
            return {
                "user_id": "local",
                "email": "local@mcprag",
                "tier": "admin",
                "session_id": "local",
                "mfa_verified": True
            }
        
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(401, "Missing or invalid authorization header")
        
        token = authorization.replace("Bearer ", "")
        
        # Get session from Redis
        if not self.redis:
            raise HTTPException(503, "Session storage not available")
        
        session_data = await self.redis.get(f"session:{token}")
        
        if not session_data:
            raise HTTPException(401, "Invalid or expired session")
        
        user = json.loads(session_data)
        
        # Check if session expired
        expires_at = datetime.fromisoformat(user["expires_at"])
        if datetime.utcnow() > expires_at:
            await self.redis.delete(f"session:{token}")
            raise HTTPException(401, "Session expired")
        
        return user
    
    async def verify_totp(self, user_id: str, totp_code: str) -> Dict[str, Any]:
        """Verify TOTP MFA code."""
        if not self.enabled:
            return {"verified": True}
        
        try:
            response = self.client.totps.authenticate(
                user_id=user_id,
                totp_code=totp_code
            )
            
            return {
                "verified": True,
                "user_id": response.user_id
            }
            
        except Exception as e:
            logger.error(f"MFA verification failed: {e}")
            return {"verified": False, "error": str(e)}
    
    async def update_session_mfa(self, session_id: str, mfa_verified: bool):
        """Update session MFA status."""
        if not self.redis:
            return
        
        session_key = f"session:{session_id}"
        session_data = await self.redis.get(session_key)
        
        if session_data:
            data = json.loads(session_data)
            data["mfa_verified"] = mfa_verified
            
            # Get remaining TTL
            ttl = await self.redis.ttl(session_key)
            
            # Update session
            await self.redis.setex(
                session_key,
                ttl,
                json.dumps(data)
            )
    
    async def _determine_user_tier(self, email: str) -> SecurityTier:
        """Determine user tier based on email or configuration."""
        # Check admin emails
        admin_emails = Config.ADMIN_EMAILS.split(",") if Config.ADMIN_EMAILS else []
        if email in admin_emails:
            return SecurityTier.ADMIN
        
        # Check developer domains
        dev_domains = Config.DEVELOPER_DOMAINS.split(",") if Config.DEVELOPER_DOMAINS else []
        domain = email.split("@")[1] if "@" in email else ""
        if domain in dev_domains:
            return SecurityTier.DEVELOPER
        
        # Default to public
        return SecurityTier.PUBLIC
```

## Phase 3: Configuration Extensions

### 3.1 Update Config Class

```python
# Add to mcprag/config.py

class Config:
    """Extended configuration for remote operation."""
    
    # ... existing config ...
    
    # Remote server configuration
    HOST: str = os.getenv("MCP_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("MCP_PORT", "8001"))
    BASE_URL: str = os.getenv("MCP_BASE_URL", "http://localhost:8001")
    ALLOWED_ORIGINS: str = os.getenv("MCP_ALLOWED_ORIGINS", "*")
    
    # Stytch configuration
    STYTCH_PROJECT_ID: str = os.getenv("STYTCH_PROJECT_ID", "")
    STYTCH_SECRET: str = os.getenv("STYTCH_SECRET", "")
    STYTCH_ENV: str = os.getenv("STYTCH_ENV", "test")
    SESSION_DURATION_MINUTES: int = int(os.getenv("SESSION_DURATION_MINUTES", "480"))
    
    # Redis configuration
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # User tier configuration
    ADMIN_EMAILS: str = os.getenv("MCP_ADMIN_EMAILS", "")
    DEVELOPER_DOMAINS: str = os.getenv("MCP_DEVELOPER_DOMAINS", "")
    
    # Security
    REQUIRE_MFA_FOR_ADMIN: bool = os.getenv("MCP_REQUIRE_MFA", "true").lower() == "true"
    
    @classmethod
    def validate_remote(cls) -> List[str]:
        """Validate remote configuration."""
        errors = []
        
        if cls.PORT < 1 or cls.PORT > 65535:
            errors.append(f"Invalid PORT: {cls.PORT}")
        
        if not cls.BASE_URL:
            errors.append("BASE_URL not configured")
        
        # Stytch is optional but warn if not configured
        if not cls.STYTCH_PROJECT_ID or not cls.STYTCH_SECRET:
            logger.warning("Stytch not configured - authentication will be disabled")
        
        return errors
```

## Phase 4: Deployment Configuration

### 4.1 Docker Configuration

```dockerfile
# Dockerfile.remote
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt requirements-remote.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-remote.txt

# Copy application
COPY . .

# Install mcprag
RUN pip install -e .

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8001/health || exit 1

# Run remote server
CMD ["python", "-m", "mcprag.remote_server"]
```

### 4.2 Docker Compose

```yaml
# docker-compose.remote.yml
version: '3.8'

services:
  mcprag-remote:
    build:
      context: .
      dockerfile: Dockerfile.remote
    ports:
      - "8001:8001"
    environment:
      # Azure Search (read-only)
      - ACS_ENDPOINT=${ACS_ENDPOINT}
      - ACS_QUERY_KEY=${ACS_QUERY_KEY}
      - ACS_INDEX_NAME=${ACS_INDEX_NAME}
      
      # Stytch
      - STYTCH_PROJECT_ID=${STYTCH_PROJECT_ID}
      - STYTCH_SECRET=${STYTCH_SECRET}
      - STYTCH_ENV=production
      
      # Redis
      - REDIS_URL=redis://redis:6379
      
      # Server config
      - MCP_HOST=0.0.0.0
      - MCP_PORT=8001
      - MCP_BASE_URL=https://mcp.company.com
      - MCP_ALLOWED_ORIGINS=https://app.company.com
      
      # Logging
      - MCP_LOG_LEVEL=INFO
      
      # Admin emails (comma-separated)
      - MCP_ADMIN_EMAILS=admin@company.com
      - MCP_DEVELOPER_DOMAINS=company.com
      
    depends_on:
      - redis
    restart: unless-stopped
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
  
  mcprag-admin:
    build:
      context: .
      dockerfile: Dockerfile.remote
    ports:
      - "8002:8002"
    environment:
      # Azure Search (admin key)
      - ACS_ENDPOINT=${ACS_ENDPOINT}
      - ACS_ADMIN_KEY=${ACS_ADMIN_KEY}
      - ACS_INDEX_NAME=${ACS_INDEX_NAME}
      
      # Enable admin mode
      - MCP_ADMIN_MODE=true
      
      # Stytch
      - STYTCH_PROJECT_ID=${STYTCH_PROJECT_ID}
      - STYTCH_SECRET=${STYTCH_SECRET}
      
      # Redis
      - REDIS_URL=redis://redis:6379
      
      # Server config
      - MCP_PORT=8002
      - MCP_BASE_URL=https://mcp.company.com
      
    depends_on:
      - redis
    restart: unless-stopped
    deploy:
      replicas: 1  # Single admin instance
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru
    restart: unless-stopped
  
  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/certs:/etc/nginx/certs:ro
    depends_on:
      - mcprag-remote
      - mcprag-admin
    restart: unless-stopped

volumes:
  redis-data:
```

### 4.3 Nginx Configuration

```nginx
# nginx/nginx.conf
events {
    worker_connections 1024;
}

http {
    upstream mcprag_read {
        least_conn;
        server mcprag-remote:8001 max_fails=2 fail_timeout=30s;
    }
    
    upstream mcprag_admin {
        server mcprag-admin:8002 max_fails=2 fail_timeout=30s;
    }
    
    # Rate limiting zones
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=auth:5m rate=5r/m;
    
    server {
        listen 443 ssl http2;
        server_name mcp.company.com;
        
        ssl_certificate /etc/nginx/certs/cert.pem;
        ssl_certificate_key /etc/nginx/certs/key.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        
        # Security headers
        add_header X-Content-Type-Options nosniff;
        add_header X-Frame-Options DENY;
        add_header X-XSS-Protection "1; mode=block";
        
        # Health check (no rate limit)
        location /health {
            proxy_pass http://mcprag_read;
            proxy_set_header Host $host;
            access_log off;
        }
        
        # Auth endpoints (strict rate limit)
        location /auth/ {
            limit_req zone=auth burst=2 nodelay;
            proxy_pass http://mcprag_read;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
        
        # Public tools (read operations)
        location ~ ^/mcp/tool/(search_|explain_|preview_|health_check|index_status|cache_stats) {
            limit_req zone=api burst=20 nodelay;
            proxy_pass http://mcprag_read;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header Authorization $http_authorization;
        }
        
        # Admin tools (write operations)
        location ~ ^/mcp/tool/(index_|manage_|create_|rebuild_|github_|configure_|clear_|backup_) {
            limit_req zone=api burst=5 nodelay;
            proxy_pass http://mcprag_admin;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header Authorization $http_authorization;
        }
        
        # Developer tools
        location ~ ^/mcp/tool/(generate_|analyze_|submit_|track_) {
            limit_req zone=api burst=10 nodelay;
            proxy_pass http://mcprag_read;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header Authorization $http_authorization;
        }
        
        # SSE endpoint
        location /mcp/sse {
            proxy_pass http://mcprag_read;
            proxy_http_version 1.1;
            proxy_set_header Connection "";
            proxy_buffering off;
            proxy_cache off;
            proxy_read_timeout 3600s;
            
            # SSE specific headers
            proxy_set_header Cache-Control "no-cache";
            proxy_set_header X-Accel-Buffering "no";
            proxy_set_header Authorization $http_authorization;
        }
    }
    
    # Redirect HTTP to HTTPS
    server {
        listen 80;
        server_name mcp.company.com;
        return 301 https://$server_name$request_uri;
    }
}
```

## Phase 5: Client Integration

### 5.1 Python Client SDK

```python
# mcprag_client/client.py
"""
Python client for remote mcprag server.
"""

import asyncio
import json
from typing import Optional, Dict, Any
import aiohttp
from aiohttp_sse_client import client as sse_client

class MCPRAGClient:
    """Client for remote mcprag server."""
    
    def __init__(self, base_url: str = "https://mcp.company.com"):
        """Initialize client."""
        self.base_url = base_url.rstrip("/")
        self.session_token: Optional[str] = None
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def authenticate(self, email: str) -> Dict[str, Any]:
        """Send magic link for authentication."""
        async with self.session.post(
            f"{self.base_url}/auth/login",
            json={"email": email}
        ) as resp:
            return await resp.json()
    
    async def complete_auth(self, token: str) -> Dict[str, Any]:
        """Complete authentication with token from email."""
        async with self.session.get(
            f"{self.base_url}/auth/callback",
            params={"token": token}
        ) as resp:
            result = await resp.json()
            self.session_token = result["token"]
            return result
    
    async def search_code(self, query: str, **kwargs) -> Dict[str, Any]:
        """Search code using mcprag."""
        return await self.execute_tool("search_code", {
            "query": query,
            **kwargs
        })
    
    async def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute any mcprag tool."""
        if not self.session_token:
            raise ValueError("Not authenticated")
        
        headers = {"Authorization": f"Bearer {self.session_token}"}
        
        async with self.session.post(
            f"{self.base_url}/mcp/tool/{tool_name}",
            json=params,
            headers=headers
        ) as resp:
            if resp.status == 403:
                error = await resp.text()
                raise PermissionError(f"Access denied: {error}")
            
            resp.raise_for_status()
            return await resp.json()
    
    async def stream_events(self):
        """Connect to SSE stream for real-time events."""
        if not self.session_token:
            raise ValueError("Not authenticated")
        
        headers = {"Authorization": f"Bearer {self.session_token}"}
        
        async with sse_client.EventSource(
            f"{self.base_url}/mcp/sse",
            headers=headers
        ) as event_source:
            async for event in event_source:
                yield json.loads(event.data)


# Example usage
async def main():
    async with MCPRAGClient() as client:
        # Authenticate
        await client.authenticate("developer@company.com")
        # ... user clicks link and gets token ...
        await client.complete_auth("token_from_email")
        
        # Search code
        results = await client.search_code(
            "authentication middleware",
            max_results=10,
            language="python"
        )
        
        print(json.dumps(results, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
```

### 5.2 CLI Wrapper

```bash
#!/bin/bash
# bin/mcprag-remote

# Configuration
MCPRAG_CONFIG="${HOME}/.mcprag/config.json"
MCPRAG_SERVER="${MCPRAG_SERVER:-https://mcp.company.com}"

# Ensure config directory exists
mkdir -p "$(dirname "$MCPRAG_CONFIG")"

# Function: Authenticate
auth() {
    local email="$1"
    
    echo "Sending magic link to ${email}..."
    
    response=$(curl -s -X POST "${MCPRAG_SERVER}/auth/login" \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"${email}\"}")
    
    echo "Check your email and paste the token from the link:"
    read -s token
    
    # Complete authentication
    auth_response=$(curl -s "${MCPRAG_SERVER}/auth/callback?token=${token}")
    
    # Extract session token
    session_token=$(echo "$auth_response" | jq -r '.token')
    
    # Save to config
    echo "{\"token\":\"${session_token}\",\"server\":\"${MCPRAG_SERVER}\"}" > "$MCPRAG_CONFIG"
    
    echo "Authentication successful!"
}

# Function: Execute tool
tool() {
    local tool_name="$1"
    shift
    local params="$@"
    
    # Load token
    if [ ! -f "$MCPRAG_CONFIG" ]; then
        echo "Not authenticated. Run: mcprag-remote auth <email>"
        exit 1
    fi
    
    token=$(jq -r '.token' "$MCPRAG_CONFIG")
    
    # Execute tool
    curl -s -X POST "${MCPRAG_SERVER}/mcp/tool/${tool_name}" \
        -H "Authorization: Bearer ${token}" \
        -H "Content-Type: application/json" \
        -d "${params}" | jq .
}

# Function: Search shortcut
search() {
    local query="$1"
    local max_results="${2:-10}"
    
    tool "search_code" "{\"query\":\"${query}\",\"max_results\":${max_results}}"
}

# Main command dispatcher
case "$1" in
    auth)
        auth "$2"
        ;;
    tool)
        tool "$2" "$3"
        ;;
    search)
        search "$2" "$3"
        ;;
    *)
        echo "Usage: mcprag-remote [auth|tool|search] ..."
        echo "  auth <email>      - Authenticate with email"
        echo "  tool <name> <json> - Execute tool with JSON params"
        echo "  search <query> [n] - Search code (shortcut)"
        exit 1
        ;;
esac
```

## Phase 6: Migration Plan

### 6.1 Migration Steps

1. **Week 1: Foundation**
   - Deploy Redis
   - Setup Stytch project
   - Deploy remote server in parallel with existing

2. **Week 2: Testing**
   - Test all tools through remote interface
   - Verify performance metrics
   - Test authentication flows

3. **Week 3: Gradual Rollout**
   - Enable for internal team
   - Monitor performance and errors
   - Collect feedback

4. **Week 4: Full Deployment**
   - Enable for all users
   - Deprecate local access (optional)
   - Monitor and optimize

### 6.2 Rollback Plan

```bash
#!/bin/bash
# scripts/rollback-remote.sh

echo "Rolling back remote mcprag deployment..."

# Stop remote services
docker-compose -f docker-compose.remote.yml down

# Clear Redis sessions
docker-compose -f docker-compose.remote.yml run --rm redis redis-cli FLUSHALL

# Restore local configuration
echo "Restoring local mcprag access..."

# Notify users
echo "Remote access temporarily disabled. Use local mcprag installation."

echo "Rollback complete"
```

## Testing Strategy

### Integration Tests

```python
# tests/test_remote_server.py
import pytest
import asyncio
from mcprag.remote_server import RemoteMCPServer
from mcprag.auth.tool_security import SecurityTier

@pytest.mark.asyncio
async def test_tool_security_enforcement():
    """Test that tool security is properly enforced."""
    server = RemoteMCPServer()
    
    # Test public user can't access admin tools
    public_user = {"tier": "public", "user_id": "test"}
    assert not server._user_has_access(
        SecurityTier.PUBLIC,
        SecurityTier.ADMIN
    )
    
    # Test admin user can access all tools
    admin_user = {"tier": "admin", "user_id": "test", "mfa_verified": True}
    assert server._user_has_access(
        SecurityTier.ADMIN,
        SecurityTier.PUBLIC
    )

@pytest.mark.asyncio
async def test_health_endpoint():
    """Test health check endpoint."""
    server = RemoteMCPServer()
    # Mock components
    server.enhanced_search = True
    server.pipeline = True
    
    health = await server.app.get("/health")
    assert health["status"] == "healthy"
    assert health["components"]["enhanced_search"] == True
```

## Monitoring & Observability

```python
# mcprag/monitoring/remote_metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Metrics
auth_attempts = Counter('mcprag_auth_attempts_total', 'Total authentication attempts', ['method', 'status'])
tool_executions = Counter('mcprag_tool_executions_total', 'Total tool executions', ['tool', 'tier', 'status'])
tool_latency = Histogram('mcprag_tool_latency_seconds', 'Tool execution latency', ['tool'])
active_sessions = Gauge('mcprag_active_sessions', 'Number of active sessions', ['tier'])
```

## Environment Variables

```bash
# .env.remote
# Azure Search (read-only for most servers)
ACS_ENDPOINT=https://your-search.search.windows.net
ACS_QUERY_KEY=your-query-key
ACS_INDEX_NAME=codebase-mcp-sota

# Azure Search (admin servers only)
ACS_ADMIN_KEY=your-admin-key

# Stytch Authentication
STYTCH_PROJECT_ID=project-live-xxx
STYTCH_SECRET=secret-live-xxx
STYTCH_ENV=production

# Redis
REDIS_URL=redis://redis:6379

# Server Configuration
MCP_HOST=0.0.0.0
MCP_PORT=8001
MCP_BASE_URL=https://mcp.company.com
MCP_ALLOWED_ORIGINS=https://app.company.com

# User Tiers
MCP_ADMIN_EMAILS=admin@company.com,cto@company.com
MCP_DEVELOPER_DOMAINS=company.com

# Security
SESSION_DURATION_MINUTES=480
MCP_REQUIRE_MFA=true

# Monitoring
MCP_LOG_LEVEL=INFO
MCP_DEBUG_TIMINGS=false
```

## Quick Start

```bash
# 1. Setup environment
cp .env.example .env.remote
# Edit .env.remote with your configuration

# 2. Build and start services
docker-compose -f docker-compose.remote.yml up -d

# 3. Test health
curl https://mcp.company.com/health

# 4. Authenticate (CLI)
./bin/mcprag-remote auth developer@company.com

# 5. Search code
./bin/mcprag-remote search "authentication"

# 6. View logs
docker-compose -f docker-compose.remote.yml logs -f mcprag-remote

# 7. Monitor metrics
curl https://mcp.company.com/metrics
```

## Key Advantages of This Implementation

1. **Leverages Existing Architecture**: Uses FastMCP's built-in SSE/HTTP support
2. **Minimal Code Changes**: Extends rather than replaces existing MCPServer
3. **Backward Compatible**: Local mode still works unchanged
4. **Component Reuse**: All existing tools work without modification
5. **Progressive Enhancement**: Can deploy incrementally
6. **Production Ready**: Includes monitoring, logging, and rollback

## Success Metrics

- Authentication success rate > 99%
- Tool execution latency P95 < 500ms
- Zero downtime migration
- 100% tool compatibility maintained
- Session management reliability > 99.9%

This implementation plan is specifically tailored for the mcprag codebase, leveraging its existing strengths while adding secure remote access capabilities.