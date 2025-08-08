"""
Remote-capable MCP Server extending the existing MCPServer.

Leverages existing FastMCP transport capabilities (SSE, streamable-http)
and adds authentication layer for secure remote access.
"""

import asyncio
import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from .server import MCPServer
from .auth.stytch_auth import StytchAuthenticator, M2MAuthenticator
from .auth.tool_security import get_tool_tier, SecurityTier, user_meets_tier_requirement
from .config import Config

logger = logging.getLogger(__name__)

# Import Redis conditionally
try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available - using in-memory session storage")

class RemoteMCPServer(MCPServer):
    """Extended MCP Server with remote capabilities."""

    def __init__(self):
        """Initialize remote MCP server."""
        super().__init__()

        # User event queues for SSE
        self._user_queues: Dict[str, asyncio.Queue] = {}

        # Initialize auth
        self.auth = StytchAuthenticator()
        self.m2m_auth = M2MAuthenticator()

        # Redis for session management
        self.redis: Optional[Any] = None

        # Track if we're initialized
        self._initialized = False

    async def startup(self):
        """Startup hook for async initialization."""
        if self._initialized:
            return

        # Initialize Redis if available
        if REDIS_AVAILABLE:
            redis_url = getattr(Config, 'REDIS_URL', 'redis://localhost:6379')
            try:
                self.redis = await aioredis.from_url(redis_url)
                logger.info(f"Connected to Redis at {redis_url}")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}. Using in-memory storage.")
                self.redis = None

        # Start async components from parent
        await self.start_async_components()

        # Initialize auth with Redis
        await self.auth.initialize(self.redis)

        self._initialized = True
        logger.info("Remote MCP Server initialized successfully")

    async def shutdown(self):
        """Shutdown hook for cleanup."""
        # Cleanup async components
        await self.cleanup_async_components()

        # Close Redis
        if self.redis:
            await self.redis.close()

        # Clear user queues
        self._user_queues.clear()

        logger.info("Remote MCP Server shutdown complete")

    def create_app(self) -> FastAPI:
        """
        Create FastAPI application with routes.

        Returns:
            Configured FastAPI app
        """
        # Lifespan context manager for startup/shutdown
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            await self.startup()
            yield
            # Shutdown
            await self.shutdown()

        # Create FastAPI app
        app = FastAPI(
            title="MCPRAG Remote Server",
            version=self.version,
            description="Remote access to Azure Code Search MCP tools",
            lifespan=lifespan
        )

        # Setup CORS
        allowed_origins = getattr(Config, 'ALLOWED_ORIGINS', '*').split(",")
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["*"],
        )

        # Health check (unauthenticated)
        @app.get("/health")
        async def health():
            """Health check endpoint."""
            components = {
                "server": "healthy",
                "enhanced_search": self.enhanced_search is not None,
                "pipeline": self.pipeline is not None,
                "cache_manager": self.cache_manager is not None,
                "redis": self.redis is not None if REDIS_AVAILABLE else "not_required",
                "auth": self.auth.enabled,
            }

            return {
                "status": "healthy",
                "version": self.version,
                "components": components,
                "transport": ["rest", "sse"],
                "authentication": "stytch" if self.auth.enabled else "disabled"
            }

        # Authentication endpoints
        @app.post("/auth/login")
        async def login(request: Request):
            """Send magic link for authentication."""
            body = await request.json()
            email = body.get("email")
            if not email:
                raise HTTPException(400, "Email is required")
            return await self.auth.send_magic_link(email)

        @app.get("/auth/callback")
        async def auth_callback(token: str):
            """Handle Stytch callback."""
            return await self.auth.complete_authentication(token)

        @app.post("/auth/verify-mfa")
        async def verify_mfa(
            request: Request,
            authorization: str = Header(None)
        ):
            """Verify MFA for admin operations."""
            body = await request.json()
            user_id = body.get("user_id")
            totp_code = body.get("totp_code")

            if not user_id or not totp_code:
                raise HTTPException(400, "user_id and totp_code are required")

            user = await self.auth.get_current_user(authorization)
            if user["user_id"] != user_id:
                raise HTTPException(403, "User mismatch")

            result = await self.auth.verify_totp(user_id, totp_code)
            if result["verified"]:
                # Update session with MFA status
                session_id = authorization.replace("Bearer ", "").strip()
                await self.auth.update_session_mfa(session_id, True)

            return result

        # M2M authentication
        @app.post("/auth/m2m/token")
        async def m2m_token(request: Request):
            """Get M2M access token."""
            body = await request.json()
            client_id = body.get("client_id")
            client_secret = body.get("client_secret")

            if not client_id or not client_secret:
                raise HTTPException(400, "client_id and client_secret are required")

            return await self.m2m_auth.authenticate_m2m(client_id, client_secret)

        # Tool listing endpoint
        @app.get("/mcp/tools")
        async def list_tools(user=Depends(self.auth.get_current_user)):
            """List available tools for the authenticated user."""
            user_tier = SecurityTier(user.get("tier", "public"))

            # Get all registered tools from FastMCP
            all_tools = []
            try:
                # Check if list_tools method exists (real FastMCP vs mock)
                if hasattr(self.mcp, 'list_tools') and callable(getattr(self.mcp, 'list_tools')):
                    # Use FastMCP's list_tools() method to get registered tools
                    fastmcp_tools = await self.mcp.list_tools()

                    for tool in fastmcp_tools:
                        tool_name = tool.name
                        tool_tier = get_tool_tier(tool_name)

                        # Check if user can access this tool
                        if user_meets_tier_requirement(user_tier, tool_tier):
                            all_tools.append({
                                "name": tool_name,
                                "title": tool.title,
                                "description": tool.description,
                                "tier": tool_tier.value,
                                "available": True,
                                "inputSchema": tool.inputSchema
                            })
                else:
                    # Fallback for mock or incompatible FastMCP
                    logger.warning("FastMCP list_tools() method not available - using mock data")
                    return {
                        "error": "Tool listing not available",
                        "message": "FastMCP list_tools() method not found",
                        "tools": [],
                        "user_tier": user_tier.value,
                        "total": 0
                    }
            except Exception as e:
                logger.error(f"Failed to list tools from FastMCP: {e}")
                return {
                    "error": "Failed to retrieve tools",
                    "message": str(e),
                    "tools": [],
                    "user_tier": user_tier.value,
                    "total": 0
                }

            return {
                "tools": all_tools,
                "user_tier": user_tier.value,
                "total": len(all_tools)
            }

        # Tool execution endpoint
        @app.post("/mcp/tool/{tool_name}")
        async def execute_tool(
            tool_name: str,
            request: Request,
            user=Depends(self.auth.get_current_user)
        ):
            """Execute MCP tool with auth checks."""
            # Check if tool exists by listing all tools (if possible)
            try:
                if hasattr(self.mcp, 'list_tools') and callable(getattr(self.mcp, 'list_tools')):
                    available_tools = await self.mcp.list_tools()
                    tool_names = [tool.name for tool in available_tools]
                    if tool_name not in tool_names:
                        raise HTTPException(404, f"Tool '{tool_name}' not found")
                else:
                    # Can't verify tool existence with mock FastMCP, proceed with execution attempt
                    logger.debug(f"Cannot verify tool '{tool_name}' exists - proceeding with execution attempt")
            except Exception as e:
                logger.error(f"Failed to list tools: {e}")
                raise HTTPException(500, f"Failed to access tools: {str(e)}")

            # Check permissions
            required_tier = get_tool_tier(tool_name)
            user_tier = SecurityTier(user.get("tier", "public"))

            if not user_meets_tier_requirement(user_tier, required_tier):
                raise HTTPException(
                    403,
                    f"Insufficient permissions. Required: {required_tier.value}, "
                    f"User has: {user_tier.value}"
                )

            # Additional MFA check for admin tools
            if required_tier == SecurityTier.ADMIN:
                mfa_required = getattr(Config, 'REQUIRE_MFA_FOR_ADMIN', True)
                if mfa_required and not user.get("mfa_verified"):
                    raise HTTPException(403, "MFA verification required for admin operations")

            # Parse request body
            try:
                body = await request.json()
            except json.JSONDecodeError:
                body = {}

            # Execute tool through FastMCP
            try:
                # Temporarily set ADMIN_MODE for admin users
                old_admin_mode = Config.ADMIN_MODE
                if user_tier in (SecurityTier.ADMIN, SecurityTier.SERVICE):
                    Config.ADMIN_MODE = True

                try:
                    # Check if call_tool method exists
                    if hasattr(self.mcp, 'call_tool') and callable(getattr(self.mcp, 'call_tool')):
                        # Execute the tool using FastMCP's call_tool method
                        logger.info(f"Executing tool '{tool_name}' for user {user['email']}")
                        result = await self.mcp.call_tool(tool_name, body)

                        # Log successful execution
                        await self._audit_log(user, tool_name, body, {"success": True})

                        # FastMCP returns a list of Content objects, extract the result
                        if result and len(result) > 0:
                            first_result = result[0]
                            # Check if it's a TextContent with text attribute
                            if hasattr(first_result, 'text'):
                                return {"result": first_result.text, "type": "text"}
                            else:
                                return {"result": str(first_result), "type": "content"}
                        else:
                            return {"result": "Tool executed successfully", "type": "success"}
                    else:
                        # Fallback for mock FastMCP
                        raise HTTPException(500, "Tool execution not available (FastMCP call_tool not found)")
                finally:
                    # Always restore ADMIN_MODE
                    Config.ADMIN_MODE = old_admin_mode

            except TypeError as e:
                # Handle parameter errors
                logger.error(f"Parameter error for tool '{tool_name}': {e}")
                raise HTTPException(400, f"Invalid parameters: {str(e)}")
            except Exception as e:
                # Log failed execution
                await self._audit_log(user, tool_name, body, {"success": False, "error": str(e)})
                logger.error(f"Tool execution failed: {tool_name}", exc_info=e)
                raise HTTPException(500, f"Tool execution failed: {str(e)}")

        # SSE endpoint for streaming
        @app.get("/mcp/sse")
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
                    # Send initial connection event
                    yield {
                        "event": "connected",
                        "data": json.dumps({
                            "user_id": user_id,
                            "tier": user.get("tier", "public")
                        })
                    }

                    while True:
                        # Check if client disconnected
                        if await request.is_disconnected():
                            break

                        try:
                            # Get event from queue with timeout
                            event = await asyncio.wait_for(queue.get(), timeout=30.0)

                            yield {
                                "event": event.get("type", "message"),
                                "data": json.dumps(event.get("data", {}))
                            }
                        except asyncio.TimeoutError:
                            # Send keepalive
                            yield {
                                "event": "ping",
                                "data": json.dumps({"timestamp": datetime.utcnow().isoformat()})
                            }
                finally:
                    # Cleanup
                    if user_id in self._user_queues:
                        del self._user_queues[user_id]

            return EventSourceResponse(event_generator())

        # API documentation
        @app.get("/")
        async def root():
            """API documentation."""
            return {
                "service": "MCPRAG Remote Server",
                "version": self.version,
                "endpoints": {
                    "health": "/health",
                    "auth": {
                        "login": "POST /auth/login",
                        "callback": "GET /auth/callback",
                        "verify_mfa": "POST /auth/verify-mfa",
                        "m2m_token": "POST /auth/m2m/token"
                    },
                    "tools": {
                        "list": "GET /mcp/tools",
                        "execute": "POST /mcp/tool/{tool_name}",
                        "stream": "GET /mcp/sse"
                    }
                },
                "documentation": "https://github.com/user/mcprag/docs"
            }

        return app

    async def _audit_log(self, user: dict, tool: str, params: dict, result: dict):
        """
        Log tool execution for audit.

        Args:
            user: User information
            tool: Tool name
            params: Tool parameters
            result: Execution result
        """
        # Skip feedback collection for now due to method compatibility issues
        # TODO: Implement proper feedback tracking when feedback collector interface is clarified
        pass

        # Log to standard logger
        logger.info(
            f"Tool execution audit: user={user.get('email', 'unknown')}, "
            f"tool={tool}, tier={user.get('tier', 'unknown')}, "
            f"success={result.get('success', False)}"
        )

    async def broadcast_to_user(self, user_id: str, event_type: str, data: Any):
        """
        Broadcast event to a specific user via SSE.

        Args:
            user_id: User ID
            event_type: Event type
            data: Event data
        """
        if user_id in self._user_queues:
            await self._user_queues[user_id].put({
                "type": event_type,
                "data": data
            })


def create_remote_server() -> RemoteMCPServer:
    """Create remote MCP server instance."""
    return RemoteMCPServer()


def create_app() -> FastAPI:
    """Create FastAPI app for the remote server."""
    server = create_remote_server()
    return server.create_app()


# Create app instance for uvicorn
app = create_app()

if __name__ == "__main__":
    import uvicorn
    from datetime import datetime

    # Get configuration
    host = getattr(Config, 'HOST', '0.0.0.0')
    port = getattr(Config, 'PORT', 8001)
    log_level = getattr(Config, 'LOG_LEVEL', 'INFO').lower()

    # Run server
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=log_level
    )
