# MCP Transport Parity Implementation Guide

## 1. Step-by-Step Plan

### Phase 1: Unified Authentication Layer
1. Create shared authentication middleware
2. Implement JWT validation for all transports
3. Add M2M authentication support
4. Configure session management

### Phase 2: Tool Registration Consistency
1. Implement tool discovery mechanism
2. Create transport-agnostic tool wrapper
3. Add tool tier validation
4. Ensure consistent error handling

### Phase 3: Azure AI Search Integration
1. Create unified search client
2. Implement BM25 and vector search
3. Add result caching layer
4. Configure Managed Identity support

### Phase 4: Testing & Validation
1. Create parity test suite
2. Implement health checks
3. Add performance monitoring
4. Configure Nginx proxy

## 2. Code Implementation

### 2.1 Unified Authentication Middleware

Create `/home/azureuser/mcprag/mcprag/auth/unified_auth.py`:

```python
"""Unified authentication for all MCP transports."""

import logging
from typing import Optional, Dict, Any, Callable
from functools import wraps
import jwt
from fastapi import HTTPException, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..config import Config
from .stytch_auth import StytchAuthenticator
from .tool_security import SecurityTier, get_tool_tier, user_meets_tier_requirement

logger = logging.getLogger(__name__)

class UnifiedAuth:
    """Unified authentication handler for all transports."""
    
    def __init__(self):
        self.stytch = StytchAuthenticator()
        self.security = HTTPBearer(auto_error=False)
        self.jwt_secret = Config.STYTCH_SECRET or "dev-secret"
        
    async def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate token across all transport types."""
        if not token:
            if Config.DEV_MODE:
                return {
                    "user_id": "dev",
                    "email": "dev@localhost",
                    "tier": "admin",
                    "mfa_verified": True
                }
            raise HTTPException(401, "Missing authorization")
        
        # Try JWT validation first (for M2M and service accounts)
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            return {
                "user_id": payload.get("sub", "unknown"),
                "email": payload.get("email", "service@mcprag"),
                "tier": payload.get("tier", "service"),
                "mfa_verified": True,
                "is_service": True
            }
        except jwt.InvalidTokenError:
            pass
        
        # Fall back to Stytch session validation
        return await self.stytch.get_current_user(f"Bearer {token}")
    
    def require_auth(self, tier: SecurityTier = SecurityTier.PUBLIC):
        """Decorator for transport-agnostic authentication."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Extract token from different sources
                token = None
                
                # Check if this is an HTTP request (FastAPI)
                request = kwargs.get("request")
                if request and isinstance(request, Request):
                    auth_header = request.headers.get("Authorization", "")
                    if auth_header.startswith("Bearer "):
                        token = auth_header.replace("Bearer ", "")
                
                # Check for direct token parameter (stdio/SSE)
                if not token:
                    token = kwargs.get("auth_token")
                
                # Validate token
                user = await self.validate_token(token)
                
                # Check tier requirements
                user_tier = SecurityTier(user.get("tier", "public"))
                if not user_meets_tier_requirement(user_tier, tier):
                    raise HTTPException(403, f"Requires {tier.value} access")
                
                # Inject user into kwargs
                kwargs["user"] = user
                
                return await func(*args, **kwargs)
            
            return wrapper
        return decorator

# Global instance
unified_auth = UnifiedAuth()
```

### 2.2 Transport-Agnostic Tool Wrapper

Create `/home/azureuser/mcprag/mcprag/mcp/transport_wrapper.py`:

```python
"""Transport-agnostic tool wrapper for consistent behavior."""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass

from ..auth.unified_auth import unified_auth
from ..auth.tool_security import get_tool_tier

logger = logging.getLogger(__name__)

@dataclass
class ToolDefinition:
    """Unified tool definition."""
    name: str
    handler: Callable
    description: str
    parameters: Dict[str, Any]
    tier: str
    
class TransportWrapper:
    """Ensures tool parity across all transports."""
    
    def __init__(self, server):
        self.server = server
        self.tools: Dict[str, ToolDefinition] = {}
        
    def register_tool(
        self,
        name: str,
        handler: Callable,
        description: str,
        parameters: Dict[str, Any]
    ):
        """Register a tool for all transports."""
        tier = get_tool_tier(name)
        
        # Wrap handler with auth
        @unified_auth.require_auth(tier)
        async def wrapped_handler(**kwargs):
            # Remove transport-specific params
            kwargs.pop("user", None)
            kwargs.pop("auth_token", None)
            kwargs.pop("request", None)
            
            # Call original handler
            return await handler(**kwargs)
        
        self.tools[name] = ToolDefinition(
            name=name,
            handler=wrapped_handler,
            description=description,
            parameters=parameters,
            tier=tier.value
        )
        
    async def list_tools(self, user_tier: str = "public") -> List[Dict[str, Any]]:
        """List available tools for user tier."""
        from ..auth.tool_security import SecurityTier, user_meets_tier_requirement
        
        user_tier_enum = SecurityTier(user_tier)
        available_tools = []
        
        for tool in self.tools.values():
            tool_tier = SecurityTier(tool.tier)
            if user_meets_tier_requirement(user_tier_enum, tool_tier):
                available_tools.append({
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                    "tier": tool.tier
                })
        
        return available_tools
    
    async def execute_tool(
        self,
        tool_name: str,
        params: Dict[str, Any],
        auth_token: Optional[str] = None
    ) -> Any:
        """Execute tool with consistent behavior."""
        if tool_name not in self.tools:
            raise ValueError(f"Tool '{tool_name}' not found")
        
        tool = self.tools[tool_name]
        
        # Add auth token to params for auth decorator
        params["auth_token"] = auth_token
        
        # Execute tool
        return await tool.handler(**params)
```

### 2.3 Azure AI Search Integration

Create `/home/azureuser/mcprag/mcprag/azure/unified_search.py`:

```python
"""Unified Azure AI Search client for all transports."""

import logging
from typing import Dict, Any, List, Optional
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential

from ..config import Config

logger = logging.getLogger(__name__)

class UnifiedSearchClient:
    """Unified Azure AI Search client with consistent behavior."""
    
    def __init__(self):
        self.endpoint = Config.ENDPOINT
        self.index_name = Config.INDEX_NAME
        
        # Use API Key or Managed Identity
        if Config.ADMIN_KEY or Config.QUERY_KEY:
            credential = AzureKeyCredential(Config.ADMIN_KEY or Config.QUERY_KEY)
        else:
            credential = DefaultAzureCredential()
        
        self.client = SearchClient(
            endpoint=self.endpoint,
            index_name=self.index_name,
            credential=credential
        )
        
    async def search(
        self,
        query: str,
        use_vector: bool = True,
        use_bm25: bool = True,
        filter_expression: Optional[str] = None,
        top: int = 10,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """Perform unified search across transports."""
        search_params = {
            "search_text": query if use_bm25 else None,
            "top": top,
            "skip": skip,
            "filter": filter_expression,
            "include_total_count": True
        }
        
        # Add vector search if enabled
        if use_vector and Config.AZURE_OPENAI_KEY:
            # Get embeddings (simplified - use your existing embedding logic)
            embedding = await self._get_embedding(query)
            if embedding:
                search_params["vector_queries"] = [
                    VectorizedQuery(
                        vector=embedding,
                        k_nearest_neighbors=top,
                        fields="contentVector"
                    )
                ]
        
        # Execute search
        results = self.client.search(**search_params)
        
        # Format consistent response
        items = []
        for result in results:
            items.append({
                "id": result.get("id"),
                "file": result.get("file"),
                "content": result.get("content"),
                "relevance": result.get("@search.score", 0),
                "repository": result.get("repository"),
                "language": result.get("language")
            })
        
        return items
    
    async def _get_embedding(self, text: str) -> Optional[List[float]]:
        """Get text embedding (implement your existing logic)."""
        # Use your existing embedding generation
        return None  # Placeholder
```

## 3. Test Commands

### 3.1 SSE Testing

```bash
# Test SSE connection WITHOUT auth (should fail)
curl -N -H "Accept: text/event-stream" \
  http://localhost:8001/mcp/sse

# Test SSE connection WITH valid token
export TOKEN="your-jwt-or-session-token"
curl -N -H "Accept: text/event-stream" \
  -H "Authorization: Bearer $TOKEN" \
  http://localhost:8001/mcp/sse

# Test SSE with invalid token (should fail)
curl -N -H "Accept: text/event-stream" \
  -H "Authorization: Bearer invalid-token" \
  http://localhost:8001/mcp/sse
```

### 3.2 HTTP JSON-RPC Testing

```bash
# List tools WITHOUT auth (should show only public tools)
curl -X GET http://localhost:8001/mcp/tools

# List tools WITH auth
curl -X GET \
  -H "Authorization: Bearer $TOKEN" \
  http://localhost:8001/mcp/tools

# Execute search_code tool (public tier)
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"query": "server", "max_results": 5}' \
  http://localhost:8001/mcp/tool/search_code

# Execute admin tool WITHOUT proper tier (should fail)
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"action": "list"}' \
  http://localhost:8001/mcp/tool/manage_index

# M2M authentication test
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"client_id": "m2m-client", "client_secret": "m2m-secret"}' \
  http://localhost:8001/auth/m2m/token
```

### 3.3 Azure AI Search Testing

```bash
# Test BM25 search
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "query": "FastMCP",
    "bm25_only": true,
    "max_results": 3
  }' \
  http://localhost:8001/mcp/tool/search_code

# Test vector search
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "query": "authentication middleware",
    "bm25_only": false,
    "max_results": 3
  }' \
  http://localhost:8001/mcp/tool/search_code

# Test with repository filter
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "query": "config",
    "repository": "mcprag",
    "max_results": 5
  }' \
  http://localhost:8001/mcp/tool/search_code
```

## 4. Nginx SSE Configuration

```nginx
# /etc/nginx/sites-available/mcprag
upstream mcprag_backend {
    server localhost:8001;
    keepalive 64;
}

server {
    listen 443 ssl http2;
    server_name mcprag.yourdomain.com;
    
    # SSL configuration
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    # SSE-specific settings
    location /mcp/sse {
        proxy_pass http://mcprag_backend;
        
        # SSE requirements
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        
        # Disable buffering for SSE
        proxy_buffering off;
        proxy_cache off;
        
        # Preserve headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # IMPORTANT: Preserve Authorization header
        proxy_set_header Authorization $http_authorization;
        proxy_pass_header Authorization;
        
        # SSE timeouts
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
        
        # SSE content type
        proxy_set_header Accept text/event-stream;
        
        # Disable compression for SSE
        gzip off;
        
        # Add CORS headers if needed
        add_header Access-Control-Allow-Origin $http_origin always;
        add_header Access-Control-Allow-Credentials true always;
    }
    
    # Regular API endpoints
    location / {
        proxy_pass http://mcprag_backend;
        proxy_http_version 1.1;
        
        # Preserve headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Authorization $http_authorization;
        
        # WebSocket support (if needed)
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

## 5. Common Failure Modes & Solutions

| Issue | Symptoms | Root Cause | Solution |
|-------|----------|------------|----------|
| **Auth works on stdio but not HTTP/SSE** | 401/403 errors on HTTP/SSE | Different auth extraction logic | Use `UnifiedAuth.validate_token()` for all transports |
| **Tools missing on some transports** | `list_tools` returns different results | Separate tool registration | Use `TransportWrapper.register_tool()` |
| **SSE disconnects immediately** | Connection drops after handshake | Nginx buffering enabled | Add `proxy_buffering off` to Nginx |
| **Authorization header stripped** | 401 errors behind proxy | Nginx not forwarding auth | Add `proxy_pass_header Authorization` |
| **Vector search inconsistent** | Different results per transport | Multiple search client instances | Use singleton `UnifiedSearchClient` |
| **M2M tokens rejected** | Service accounts can't authenticate | JWT validation not implemented | Add JWT decode in `validate_token()` |
| **SSE events not streaming** | Events batch instead of stream | Response buffering | Set `X-Accel-Buffering: no` header |
| **CORS errors on SSE** | Browser blocks SSE connection | Missing CORS headers | Add CORS headers in Nginx config |
| **Session timeout mismatch** | Different timeout per transport | Separate session configs | Use unified `SESSION_DURATION_MINUTES` |
| **Tool permissions inconsistent** | Same user, different access | Tier checking varies | Use `user_meets_tier_requirement()` everywhere |
| **Azure Search timeout** | Queries timeout on some transports | Different timeout settings | Set consistent timeout in `UnifiedSearchClient` |
| **Embedding cache misses** | Same query, different embeddings | Transport-specific caching | Use shared cache manager |
| **MFA required inconsistently** | MFA prompted differently | Transport-specific MFA logic | Check `REQUIRE_MFA_FOR_ADMIN` uniformly |
| **Dev mode bypass fails** | Dev mode works on stdio only | `DEV_MODE` check location | Check `Config.DEV_MODE` in `validate_token()` |

## 6. Verification Checklist

Run these checks to ensure parity:

```bash
# 1. Tool parity check
diff <(curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8001/mcp/tools | jq -S '.tools[].name') \
     <(echo '{"method": "tools/list"}' | nc localhost 8001 | jq -S '.tools[].name')

# 2. Search result consistency
for transport in http sse stdio; do
  echo "Testing $transport..."
  # Run same search across transports and compare results
done

# 3. Auth validation
pytest tests/test_transport_parity.py -v

# 4. Performance comparison
ab -n 100 -c 10 -H "Authorization: Bearer $TOKEN" \
   http://localhost:8001/mcp/tool/search_code
```

## 7. Implementation Priority

1. **Phase 1 (Critical)**: Unified auth middleware - ensures security consistency
2. **Phase 2 (High)**: Transport wrapper - ensures tool availability
3. **Phase 3 (Medium)**: Azure Search unification - ensures result consistency  
4. **Phase 4 (Low)**: Nginx configuration - production deployment

## 8. Testing Strategy

Create `/home/azureuser/mcprag/tests/test_transport_parity.py`:

```python
"""Test transport parity across stdio, HTTP, and SSE."""

import pytest
import asyncio
from typing import Dict, Any

class TestTransportParity:
    """Verify consistent behavior across transports."""
    
    @pytest.mark.asyncio
    async def test_tool_listing_parity(self, stdio_client, http_client, sse_client):
        """Tools list should be identical across transports."""
        stdio_tools = await stdio_client.list_tools()
        http_tools = await http_client.list_tools()
        sse_tools = await sse_client.list_tools()
        
        assert set(stdio_tools) == set(http_tools) == set(sse_tools)
    
    @pytest.mark.asyncio
    async def test_search_results_consistency(self, all_clients):
        """Search results should be consistent."""
        query = "test_query"
        results = []
        
        for client in all_clients:
            result = await client.search_code(query=query, max_results=5)
            results.append(result)
        
        # Check result count matches
        assert len(set(len(r) for r in results)) == 1
        
        # Check top result is same
        assert all(r[0]["id"] == results[0][0]["id"] for r in results)
    
    @pytest.mark.asyncio
    async def test_auth_tier_enforcement(self, all_clients):
        """Tier restrictions should be consistent."""
        for client in all_clients:
            # Public user should fail on admin tool
            with pytest.raises(Exception) as exc:
                await client.execute_tool("rebuild_index", {}, tier="public")
            assert "403" in str(exc) or "permission" in str(exc).lower()
```