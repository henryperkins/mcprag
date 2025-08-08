# MCP Transport Parity Implementation Guide (V2)

## Executive Summary

This guide provides a comprehensive approach to achieving transport parity across stdio, HTTP, and SSE for the mcprag MCP server. It builds upon the existing architecture rather than recreating components, ensuring consistency while minimizing code duplication.

## Architecture Overview

### Existing Components Leveraged

1. **Azure Integration** (`enhanced_rag/azure_integration/`)
   - `AzureSearchClient`: REST client with circuit breaker and retry logic
   - `SearchOperations`: Comprehensive Azure Search operations
   - `UnifiedAutomation`: Orchestrates all automation tasks
   - `IndexAutomation`, `DataAutomation`, `IndexerAutomation`: Specialized managers

2. **Authentication** (`mcprag/auth/`)
   - `StytchAuthenticator`: Magic link authentication with tier-based access
   - `M2MAuthenticator`: Machine-to-machine authentication
   - `SecurityTier`: Tool access control (PUBLIC, DEVELOPER, ADMIN, SERVICE)

3. **MCP Server** (`mcprag/server.py`)
   - `MCPServer`: FastMCP-based server with component lifecycle
   - Async component initialization and cleanup
   - Tool registration via modular system

4. **MCP Tools** (`mcprag/mcp/tools/`)
   - Modular tool registration (search, generation, analysis, admin, etc.)
   - Component checking with `check_component()`
   - Response helpers (`ok`, `err`) for consistent responses

## Stytch Authentication Integration

### OAuth 2.1 Resource Server Implementation

The mcprag server implements OAuth 2.1 Resource Server functionality following the MCP authorization specification and RFC 9728. This enables secure, delegated access for AI agents while maintaining user control over their data.

### Key Authentication Components

#### 1. Stytch Token Verifier

```python
# mcprag/auth/stytch_verifier.py
from stytch import StytchClient
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcprag.auth.security_tiers import SecurityTier

class StytchTokenVerifier(TokenVerifier):
    """Stytch-based token verification for MCP authentication."""
    
    def __init__(self, stytch_client: StytchClient):
        self.stytch = stytch_client
        
    async def verify_token(self, token: str) -> AccessToken | None:
        """Verify Stytch session JWT or M2M token."""
        try:
            # Try session JWT first
            result = await self.stytch.sessions.authenticate_jwt(
                session_jwt=token
            )
            
            if result.session:
                return AccessToken(
                    sub=result.session.user_id,
                    iss="https://auth.stytch.com",
                    aud=["mcprag"],
                    scope=self._get_user_scopes(result.session),
                    exp=result.session.expires_at,
                    tier=self._get_user_tier(result.session)
                )
        except:
            # Fallback to M2M token verification
            return await self._verify_m2m_token(token)
```

#### 2. Protected Resource Metadata

```python
# mcprag/auth/settings.py
from pydantic import AnyHttpUrl
from mcp.server.auth.settings import AuthSettings

# Configure auth settings for RFC 9728 compliance
auth_settings = AuthSettings(
    issuer_url=AnyHttpUrl("https://auth.stytch.com"),
    resource_server_url=AnyHttpUrl("https://api.mcprag.dev"),
    required_scopes=["user"],
    token_endpoint_auth_methods=["none"],  # Public clients use PKCE
    code_challenge_methods_supported=["S256"]  # PKCE required
)
```

### Authentication Flow Implementation

#### Phase 1: Discovery Endpoints

```python
# mcprag/auth/discovery.py
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get("/.well-known/oauth-protected-resource")
async def protected_resource_metadata():
    """RFC 9728 Protected Resource Metadata."""
    return JSONResponse({
        "resource": "https://api.mcprag.dev/mcp",
        "authorization_servers": ["https://auth.stytch.com"],
        "bearer_methods_supported": ["header"],
        "resource_documentation": "https://docs.mcprag.dev/auth"
    })

@app.get("/.well-known/oauth-authorization-server")
async def authorization_server_metadata():
    """OAuth 2.1 Authorization Server Metadata."""
    return JSONResponse({
        "issuer": "https://auth.stytch.com",
        "authorization_endpoint": "https://auth.stytch.com/oauth/authorize",
        "token_endpoint": "https://auth.stytch.com/oauth/token",
        "registration_endpoint": "https://auth.stytch.com/oauth/register",
        "jwks_uri": "https://auth.stytch.com/.well-known/jwks.json",
        "scopes_supported": ["user", "admin", "developer"],
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": ["none"]
    })
```

#### Phase 2: Unified Token Extraction

```python
# mcprag/auth/transport_auth.py
from typing import Optional, Dict, Any
from fastapi import Request

class TransportAuthExtractor:
    """Extract auth tokens from different transport contexts."""
    
    @staticmethod
    async def extract_token(**context) -> Optional[str]:
        """Extract token from transport-specific context."""
        
        # HTTP/SSE: FastAPI Request
        if request := context.get("request"):
            if isinstance(request, Request):
                # Bearer token in header
                if auth := request.headers.get("Authorization", ""):
                    if auth.startswith("Bearer "):
                        return auth[7:].strip()
                
                # Token in query params (SSE fallback)
                if hasattr(request, 'query_params'):
                    if token := request.query_params.get("token"):
                        return token
        
        # stdio: Direct parameter
        if token := context.get("auth_token"):
            return token
        
        # Adapter pattern: session_token
        if token := context.get("session_token"):
            return token
        
        return None
```

#### Phase 3: Enhanced Stytch Authenticator

```python
# mcprag/auth/stytch_authenticator.py
from stytch import StytchClient
from mcprag.config import Config
from mcprag.auth.security_tiers import SecurityTier

class EnhancedStytchAuthenticator:
    """Enhanced Stytch authenticator supporting multiple token types."""
    
    def __init__(self):
        self.stytch = StytchClient(
            project_id=Config.STYTCH_PROJECT_ID,
            secret=Config.STYTCH_SECRET
        )
        self.enabled = bool(Config.STYTCH_PROJECT_ID)
    
    async def validate_any_token(self, token: str) -> Dict[str, Any]:
        """Validate token from any source."""
        
        # 1. Dev mode bypass
        if Config.DEV_MODE and (not token or token == "dev"):
            return self._dev_user()
        
        # 2. Azure AD tokens (Management API)
        if self._looks_like_azure_ad(token):
            return await self._validate_azure_ad(token)
        
        # 3. Stytch sessions
        if self.enabled:
            try:
                session = await self.stytch.sessions.authenticate_jwt(
                    session_jwt=token
                )
                if session.session:
                    return {
                        "user_id": session.session.user_id,
                        "email": session.session.user_email,
                        "tier": self._get_user_tier(session.session),
                        "scopes": self._get_user_scopes(session.session),
                        "mfa_verified": session.session.authentication_factors
                    }
            except Exception:
                pass
        
        # 4. M2M JWT tokens
        return await self._validate_m2m_jwt(token)
    
    def _get_user_tier(self, session) -> SecurityTier:
        """Determine user's security tier from session."""
        # Custom claims or user attributes define tier
        if "admin" in session.custom_claims.get("roles", []):
            return SecurityTier.ADMIN
        elif "developer" in session.custom_claims.get("roles", []):
            return SecurityTier.DEVELOPER
        return SecurityTier.PUBLIC
    
    async def _validate_m2m_jwt(self, token: str) -> Dict[str, Any]:
        """Validate machine-to-machine JWT."""
        try:
            result = await self.stytch.m2m.authenticate_token(
                access_token=token
            )
            return {
                "client_id": result.client_id,
                "tier": SecurityTier.SERVICE,
                "scopes": result.scopes
            }
        except Exception:
            raise ValueError("Invalid token")
```

### Stytch-Specific Features

#### 1. Magic Link Authentication

```python
# mcprag/auth/magic_link.py
async def send_magic_link(email: str):
    """Send magic link for passwordless authentication."""
    result = await stytch.magic_links.email.send(
        email=email,
        login_magic_link_url="https://api.mcprag.dev/auth/callback",
        signup_magic_link_url="https://api.mcprag.dev/auth/signup"
    )
    return result.request_id

async def authenticate_magic_link(token: str):
    """Authenticate user via magic link token."""
    result = await stytch.magic_links.authenticate(
        token=token
    )
    return {
        "session_token": result.session_token,
        "session_jwt": result.session_jwt,
        "user_id": result.user_id
    }
```

#### 2. Dynamic Client Registration

```python
# mcprag/auth/dcr.py
async def register_oauth_client(metadata: OAuthClientMetadata):
    """Dynamic client registration with Stytch."""
    
    # Stytch handles DCR through their API
    result = await stytch.oauth.register_client(
        client_name=metadata.client_name,
        redirect_uris=metadata.redirect_uris,
        grant_types=metadata.grant_types,
        response_types=metadata.response_types,
        scope=metadata.scope,
        logo_uri=metadata.logo_uri
    )
    
    return OAuthClientInformationFull(
        client_id=result.client_id,
        client_name=metadata.client_name,
        redirect_uris=metadata.redirect_uris,
        grant_types=metadata.grant_types,
        response_types=metadata.response_types,
        scope=metadata.scope
    )
```

#### 3. Consent Management

```python
# mcprag/auth/consent.py
class StytchConsentManager:
    """Manage OAuth consent with Stytch."""
    
    async def check_consent(self, user_id: str, client_id: str, scopes: List[str]):
        """Check if user has granted consent."""
        # Stytch tracks consent automatically
        consents = await stytch.oauth.get_user_consents(
            user_id=user_id,
            client_id=client_id
        )
        
        granted_scopes = set()
        for consent in consents:
            granted_scopes.update(consent.scopes)
        
        return all(scope in granted_scopes for scope in scopes)
    
    async def grant_consent(self, user_id: str, client_id: str, scopes: List[str]):
        """Grant consent for specific scopes."""
        await stytch.oauth.grant_consent(
            user_id=user_id,
            client_id=client_id,
            scopes=scopes
        )
```

### Security Tier Enforcement

```python
# mcprag/auth/authorization.py
from functools import wraps
from mcprag.auth.security_tiers import SecurityTier

def require_tier(minimum_tier: SecurityTier):
    """Decorator to enforce security tier requirements."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract context from kwargs
            ctx = kwargs.get("ctx")
            if not ctx:
                return err("No context provided")
            
            # Get user from context
            user = ctx.request_context.user
            if not user:
                return err("Not authenticated")
            
            # Check tier
            user_tier = SecurityTier(user.get("tier", "public"))
            if not user_meets_tier_requirement(user_tier, minimum_tier):
                return err(f"Requires {minimum_tier.value} access")
            
            # MFA check for admin operations
            if minimum_tier == SecurityTier.ADMIN:
                if Config.REQUIRE_MFA_FOR_ADMIN and not user.get("mfa_verified"):
                    return err("MFA required for admin operations")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Tool with tier enforcement
@mcp.tool()
@require_tier(SecurityTier.ADMIN)
async def manage_index(action: str, ctx: Context) -> Dict[str, Any]:
    """Admin-only index management."""
    # Tool implementation
    pass
```

### Component Initialization with Auth

```python
# mcprag/server.py
class MCPServer(FastMCP):
    """MCP Server with Stytch authentication."""
    
    def __init__(self):
        # Initialize Stytch token verifier
        stytch_client = StytchClient(
            project_id=Config.STYTCH_PROJECT_ID,
            secret=Config.STYTCH_SECRET
        )
        
        token_verifier = StytchTokenVerifier(stytch_client)
        
        # Initialize FastMCP with auth
        super().__init__(
            name="mcprag",
            token_verifier=token_verifier,
            auth=AuthSettings(
                issuer_url=AnyHttpUrl("https://auth.stytch.com"),
                resource_server_url=AnyHttpUrl(Config.SERVER_URL),
                required_scopes=["user"],
                jwks_uri="https://auth.stytch.com/.well-known/jwks.json"
            )
        )
    
    async def run(self, transport: Literal["stdio", "sse", "streamable-http"] = "stdio"):
        """Run server with transport-specific initialization."""
        
        if transport == "stdio":
            # Synchronous component start for stdio
            asyncio.run(self.start_async_components())
        else:
            # Async component start for HTTP/SSE
            asyncio.create_task(self.start_async_components())
        
        # Ensure components available before first request
        self._component_ready_event = asyncio.Event()
        
        # Run transport with auth enabled
        self.mcp.run(transport=transport)
```

## Test Strategy

### 1. Authentication Tests

```python
# tests/test_stytch_auth.py
import pytest
from mcprag.auth.stytch_authenticator import EnhancedStytchAuthenticator

@pytest.fixture
async def authenticator():
    return EnhancedStytchAuthenticator()

async def test_magic_link_flow(authenticator):
    """Test magic link authentication flow."""
    # Send magic link
    request_id = await authenticator.send_magic_link("user@example.com")
    assert request_id
    
    # Simulate callback with token
    token = "test_magic_link_token"
    result = await authenticator.authenticate_magic_link(token)
    assert result["session_jwt"]
    assert result["user_id"]

async def test_session_validation(authenticator):
    """Test Stytch session JWT validation."""
    session_jwt = "valid_session_jwt"
    user = await authenticator.validate_any_token(session_jwt)
    assert user["user_id"]
    assert user["tier"] in ["public", "developer", "admin"]

async def test_m2m_authentication(authenticator):
    """Test machine-to-machine token validation."""
    m2m_token = "m2m_access_token"
    result = await authenticator.validate_any_token(m2m_token)
    assert result["client_id"]
    assert result["tier"] == "service"

async def test_tier_enforcement():
    """Test security tier enforcement."""
    # Test admin tool access
    user = {"tier": "public"}
    result = await admin_only_tool(user=user)
    assert "Requires admin access" in str(result)
    
    # Test with admin user
    admin_user = {"tier": "admin", "mfa_verified": True}
    result = await admin_only_tool(user=admin_user)
    assert result["success"]
```

### 2. Transport Parity Tests with Auth

```bash
# Test auth across transports

# stdio with dev mode
echo '{"method": "search_code", "params": {"query": "test"}}' | \
  MCP_DEV_MODE=true python -m mcprag

# HTTP with Stytch token
STYTCH_TOKEN=$(curl -X POST https://auth.stytch.com/oauth/token \
  -d "grant_type=authorization_code&code=$AUTH_CODE" | jq -r .access_token)

curl -X POST http://localhost:8001/mcp/tool/search_code \
  -H "Authorization: Bearer $STYTCH_TOKEN" \
  -d '{"query": "test"}'

# SSE with token in query
curl -N "http://localhost:8001/mcp/sse?token=$STYTCH_TOKEN"

# M2M authentication
M2M_TOKEN=$(curl -X POST https://auth.stytch.com/oauth/token \
  -d "grant_type=client_credentials&client_id=$CLIENT_ID&client_secret=$SECRET" | \
  jq -r .access_token)

curl -X POST http://localhost:8001/mcp/tool/manage_index \
  -H "Authorization: Bearer $M2M_TOKEN" \
  -d '{"action": "list"}'
```

## Nginx Configuration with Stytch Auth

```nginx
upstream mcprag {
    server localhost:8001;
    keepalive 32;
}

server {
    listen 443 ssl http2;
    server_name mcprag.example.com;
    
    ssl_certificate /etc/ssl/certs/mcprag.crt;
    ssl_certificate_key /etc/ssl/private/mcprag.key;
    
    # SSE-specific location with auth preservation
    location /mcp/sse {
        proxy_pass http://mcprag;
        
        # SSE requirements
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        
        # Disable buffering for real-time streaming
        proxy_buffering off;
        proxy_cache off;
        chunked_transfer_encoding on;
        
        # Preserve headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # CRITICAL: Pass Authorization header for Stytch tokens
        proxy_set_header Authorization $http_authorization;
        proxy_pass_header Authorization;
        
        # SSE timeouts (24 hours)
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
        send_timeout 86400s;
        
        # Response headers for SSE
        add_header Cache-Control "no-cache";
        add_header X-Accel-Buffering "no";
        
        # CORS for Stytch OAuth flows
        add_header Access-Control-Allow-Origin $http_origin always;
        add_header Access-Control-Allow-Credentials true always;
        add_header Access-Control-Allow-Headers "Authorization,Content-Type" always;
        add_header Access-Control-Allow-Methods "GET,POST,OPTIONS" always;
        
        # Handle preflight
        if ($request_method = 'OPTIONS') {
            return 204;
        }
    }
    
    # OAuth callback endpoint
    location /auth/callback {
        proxy_pass http://mcprag;
        proxy_http_version 1.1;
        
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Discovery endpoints
    location /.well-known/ {
        proxy_pass http://mcprag;
        proxy_http_version 1.1;
        
        # Cache discovery documents
        proxy_cache_valid 200 1h;
        add_header Cache-Control "public, max-age=3600";
    }
    
    # Regular HTTP/JSON-RPC
    location / {
        proxy_pass http://mcprag;
        proxy_http_version 1.1;
        
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Authorization $http_authorization;
        
        # Standard timeouts
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }
}
```

## Common Issues and Solutions

| Issue | Root Cause | Solution |
|-------|------------|----------|
| **Different tools across transports** | Conditional registration | Ensure `register_tools()` called identically |
| **Auth works stdio, fails HTTP** | Token extraction differs | Use `TransportAuthExtractor.extract_token()` |
| **Stytch token rejected** | Invalid or expired | Check token expiry, refresh if needed |
| **SSE drops connections** | Nginx buffering | Add `proxy_buffering off` and `X-Accel-Buffering: no` |
| **Components not initialized** | Async startup race | Use `ensure_async_components_started()` |
| **Azure Search timeout varies** | Different client configs | Use single `AzureSearchClient` instance |
| **Indexer status too large** | No truncation applied | Apply `_truncate_indexer_status()` consistently |
| **M2M tokens rejected** | JWT validation missing | Check JWT before Stytch in validation chain |
| **MFA not enforced uniformly** | Tier check location varies | Check in unified auth decorator |
| **CORS errors in browser** | Missing headers | Add CORS headers in Nginx config |
| **Magic link callback fails** | Redirect URI mismatch | Ensure callback URL matches registration |
| **Consent not persisted** | No consent storage | Use Stytch consent management |
| **Token refresh fails** | Refresh token not stored | Store and manage refresh tokens |
| **Circuit breaker not working** | Multiple client instances | Use singleton `AzureSearchClient` |
| **Tool errors differ** | Inconsistent error handling | Always use `ok()`/`err()` helpers |

## Deployment Checklist

### Pre-deployment
- [ ] All components tested across transports
- [ ] Authentication validated (Stytch, M2M, Azure AD)
- [ ] Stytch project configured with correct redirect URIs
- [ ] Azure operations verified (index, search, manage)
- [ ] Response truncation working
- [ ] Circuit breaker tested
- [ ] CORS configuration tested for OAuth flows

### Nginx Configuration
- [ ] SSE location configured with buffering disabled
- [ ] Authorization header preserved
- [ ] Timeouts appropriate for SSE (86400s)
- [ ] CORS headers configured for Stytch OAuth
- [ ] SSL certificates installed
- [ ] OAuth callback route configured

### Environment Variables
- [ ] `ACS_ENDPOINT` and `ACS_ADMIN_KEY` set
- [ ] `STYTCH_PROJECT_ID` and `STYTCH_SECRET` configured
- [ ] `STYTCH_ENVIRONMENT` set (test/live)
- [ ] `MCP_ADMIN_MODE` set appropriately
- [ ] `REDIS_URL` for session storage
- [ ] `AZURE_RESOURCE_GROUP` for management operations
- [ ] `SERVER_URL` set for discovery endpoints
- [ ] `REQUIRE_MFA_FOR_ADMIN` configured

### Stytch Configuration
- [ ] OAuth application created in Stytch dashboard
- [ ] Redirect URIs configured correctly
- [ ] Magic link URLs configured
- [ ] M2M clients created if needed
- [ ] Custom claims configured for tier mapping
- [ ] Session duration configured
- [ ] MFA settings configured if required

### Monitoring
- [ ] Health endpoints accessible
- [ ] Logs aggregated across transports
- [ ] Metrics collection enabled
- [ ] Error tracking configured
- [ ] Stytch webhook endpoints configured
- [ ] Token usage monitoring enabled

## Summary

This implementation guide focuses on:

1. **Leveraging existing components** rather than recreating them
2. **Consistent patterns** across all transports (component checking, error handling)
3. **Unified authentication** with Stytch that supports magic links, OAuth 2.1, and M2M
4. **Proper async initialization** for different transport modes
5. **Response management** with truncation for large payloads
6. **Security enforcement** with tier-based access control and MFA support
7. **Comprehensive Stytch integration** including DCR, consent management, and token verification

The key to success is using the existing architecture's strengths while ensuring consistent behavior across all transport mechanisms, with Stytch providing a robust authentication layer that works seamlessly across stdio, HTTP, and SSE transports.