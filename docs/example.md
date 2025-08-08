To build a remote MCP server with secure authentication and fast MCP transport, you can follow these comprehensive steps:

### 1. Understanding MCP Server Architecture

MCP servers are specialized programs that expose capabilities to AI applications through standardized interfaces. They typically focus on specific domains like file management, email handling, or travel planning. The core building blocks of MCP servers include:

- **Tools**: For AI actions (model-controlled)
- **Resources**: For context data (application-controlled)
- **Prompts**: For interaction templates (user-controlled)

### 2. Setting Up Your Development Environment

First, set up your development environment by creating a new MCP server project:

```bash
npm create cloudflare@latest -- my-mcp-server --template=cloudflare/ai/demos/remote-mcp-authless
cd my-mcp-server
npm start
```

This will create a basic MCP server running on `http://localhost:8787/sse`.

### 3. Implementing Authentication

For secure authentication, you can use OAuth providers. Here's how to set up GitHub authentication:

#### Create OAuth Apps
1. Create a GitHub OAuth App for local development:
   - Application name: `My MCP Server (local)`
   - Homepage URL: `http://localhost:8787`
   - Authorization callback URL: `http://localhost:8787/callback`

2. Create another OAuth App for production:
   - Application name: `My MCP Server (production)`
   - Homepage URL: Your workers.dev URL
   - Authorization callback URL: Your workers.dev URL with `/callback` path

#### Configure Your Server
Update your server configuration to use the OAuth handler:

```typescript
import GitHubHandler from "./github-handler";

export default new OAuthProvider({
  apiRoute: "/sse",
  apiHandler: MyMCP.Router,
  defaultHandler: GitHubHandler,
  authorizeEndpoint: "/authorize",
  tokenEndpoint: "/token",
  clientRegistrationEndpoint: "/register",
});
```

### 4. Implementing Fast MCP Transport

The `RemoteMCPServerWithSecureAuthAndFastMCPTransport` implementation shows how to support both SSE and Streamable HTTP transport methods. Here's a Python example using FastAPI:

```python
from fastapi import FastAPI, Request
from sse_starlette.sse import EventSourceResponse

class RemoteMCPServer:
    def create_app(self) -> FastAPI:
        app = FastAPI()

        @app.get("/mcp/sse")
        async def sse_endpoint(request: Request):
            async def event_generator():
                # Your SSE implementation
                yield {"event": "connected", "data": "Connection established"}

            return EventSourceResponse(event_generator())

        @app.post("/mcp")
        async def streamable_http_endpoint(request: Request):
            # Your Streamable HTTP implementation
            return {"status": "success"}

        return app
```

### 5. Adding Tools to Your MCP Server

Define tools that your MCP server will expose. Here's an example of a tool definition:

```json
{
  "name": "searchFlights",
  "description": "Search for available flights",
  "inputSchema": {
    "type": "object",
    "properties": {
      "origin": { "type": "string", "description": "Departure city" },
      "destination": { "type": "string", "description": "Arrival city" },
      "date": { "type": "string", "format": "date", "description": "Travel date" }
    },
    "required": ["origin", "destination", "date"]
  }
}
```

### 6. Implementing Resources and Prompts

Resources provide context data to AI models. Here's an example resource template:

```json
{
  "uriTemplate": "weather://forecast/{city}/{date}",
  "name": "weather-forecast",
  "title": "Weather Forecast",
  "description": "Get weather forecast for any city and date",
  "mimeType": "application/json"
}
```

Prompts provide interaction templates. Here's an example:

```json
{
  "name": "plan-vacation",
  "title": "Plan a vacation",
  "description": "Guide through vacation planning process",
  "arguments": [
    { "name": "destination", "type": "string", "required": true },
    { "name": "duration", "type": "number", "description": "days" }
  ]
}
```

### 7. Deploying to Cloudflare

Deploy your MCP server to Cloudflare using Wrangler:

```bash
npx wrangler@latest deploy
```

### 8. Connecting to MCP Clients

Use the `mcp-remote` local proxy to connect your MCP server to clients like Claude Desktop:

```json
{
  "mcpServers": {
    "math": {
      "command": "npx",
      "args": ["mcp-remote", "https://your-worker-name.your-account.workers.dev/sse"]
    }
  }
}
```

### 9. Testing and Validation

Test your MCP server using the MCP inspector:

```bash
npx @modelcontextprotocol/inspector@latest
```

Connect to your server at `http://localhost:8787/sse` and verify that you can list and execute tools.

### 10. Advanced Features

For more advanced implementations, consider:

1. **Redis Integration**: For session management and state persistence
2. **Multi-Factor Authentication**: For enhanced security
3. **Tool Security Tiers**: To implement different access levels
4. **Audit Logging**: To track tool executions and user activities

### Example: Complete Tool Execution Endpoint

Here's a complete example of a tool execution endpoint with authentication and authorization:

```python
@app.post("/mcp/tool/{tool_name}")
async def execute_tool(
    tool_name: str,
    request: Request,
    user=Depends(self.auth.get_current_user)
):
    # Check if tool exists
    if tool_name not in available_tools:
        raise HTTPException(404, f"Tool '{tool_name}' not found")

    # Check permissions
    required_tier = get_tool_tier(tool_name)
    user_tier = SecurityTier(user.get("tier", "public"))

    if not user_meets_tier_requirement(user_tier, required_tier):
        raise HTTPException(403, "Insufficient permissions")

    # Execute tool
    try:
        body = await request.json()
        result = await self.mcp.call_tool(tool_name, body)
        return {"result": result}
    except Exception as e:
        raise HTTPException(500, f"Tool execution failed: {str(e)}")
```

### Python Client for Remote MCPRAG Server Usage and Authentication

Here's a Python client implementation for interacting with your remote MCP server:

```python
import asyncio
import json
import os
from typing import Optional, Dict, Any, AsyncIterator
from pathlib import Path

try:
    import aiohttp
    from aiohttp_sse_client import client as sse_client
except ImportError:
    raise ImportError("Please install aiohttp and aiohttp-sse-client: pip install aiohttp aiohttp-sse-client")

class MCPRAGError(Exception):
    """Base exception for MCPRAG client errors."""
    pass

class AuthenticationError(MCPRAGError):
    """Authentication related errors."""
    pass

class PermissionError(MCPRAGError):
    """Permission denied errors."""
    pass

class ToolExecutionError(MCPRAGError):
    """Tool execution errors."""
    pass

class MCPRAGClient:
    """Client for remote mcprag server."""

    def __init__(self, base_url: str = None, config_file: str = None):
        """
        Initialize client.

        Args:
            base_url: Server URL (defaults to env var or localhost)
            config_file: Path to config file with saved session
        """
        self.base_url = base_url or os.getenv("MCPRAG_SERVER", "http://localhost:8001")
        self.base_url = self.base_url.rstrip("/")

        self.config_file = Path(config_file or os.path.expanduser("~/.mcprag/config.json"))
        self.session_token: Optional[str] = None
        self.session: Optional[aiohttp.ClientSession] = None

        # Load saved session if exists
        self._load_config()

    def _load_config(self):
        """Load saved configuration."""
        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    config = json.load(f)
                    self.session_token = config.get("token")
                    if config.get("server"):
                        self.base_url = config["server"]
            except Exception:
                pass  # Ignore config errors

    def _save_config(self):
        """Save configuration."""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, "w") as f:
            json.dump({
                "token": self.session_token,
                "server": self.base_url
            }, f, indent=2)

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def health_check(self) -> Dict[str, Any]:
        """
        Check server health.

        Returns:
            Health status information
        """
        async with self.session.get(f"{self.base_url}/health") as resp:
            return await resp.json()

    async def authenticate(self, email: str) -> Dict[str, Any]:
        """
        Send magic link for authentication.

        Args:
            email: User's email address

        Returns:
            Authentication status
        """
        async with self.session.post(
            f"{self.base_url}/auth/login",
            json={"email": email}
        ) as resp:
            if resp.status != 200:
                error = await resp.text()
                raise AuthenticationError(f"Failed to send magic link: {error}")

            result = await resp.json()
            print(f"Magic link sent to {email}. Check your email.")
            return result

    async def complete_auth(self, token: str) -> Dict[str, Any]:
        """
        Complete authentication with token from email.

        Args:
            token: Authentication token from magic link

        Returns:
            Session information
        """
        async with self.session.get(
            f"{self.base_url}/auth/callback",
            params={"token": token}
        ) as resp:
            if resp.status != 200:
                error = await resp.text()
                raise AuthenticationError(f"Authentication failed: {error}")

            result = await resp.json()
            self.session_token = result["token"]

            # Save session
            self._save_config()

            return result

    async def verify_mfa(self, user_id: str, totp_code: str) -> Dict[str, Any]:
        """
        Verify MFA for admin operations.

        Args:
            user_id: User ID
            totp_code: TOTP code from authenticator app

        Returns:
            Verification result
        """
        if not self.session_token:
            raise AuthenticationError("Not authenticated")

        headers = {"Authorization": f"Bearer {self.session_token}"}

        async with self.session.post(
            f"{self.base_url}/auth/verify-mfa",
            json={"user_id": user_id, "totp_code": totp_code},
            headers=headers
        ) as resp:
            if resp.status != 200:
                error = await resp.text()
                raise AuthenticationError(f"MFA verification failed: {error}")

            return await resp.json()

    async def list_tools(self) -> Dict[str, Any]:
        """
        List available tools for the authenticated user.

        Returns:
            List of available tools
        """
        if not self.session_token:
            raise AuthenticationError("Not authenticated")

        headers = {"Authorization": f"Bearer {self.session_token}"}

        async with self.session.get(
            f"{self.base_url}/mcp/tools",
            headers=headers
        ) as resp:
            if resp.status == 401:
                raise AuthenticationError("Session expired or invalid")

            resp.raise_for_status()
            return await resp.json()

    async def search_code(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Search code using mcprag.

        Args:
            query: Search query
            **kwargs: Additional search parameters

        Returns:
            Search results
        """
        return await self.execute_tool("search_code", {
            "query": query,
            **kwargs
        })

    async def generate_code(self, description: str, **kwargs) -> Dict[str, Any]:
        """
        Generate code using mcprag.

        Args:
            description: Code description
            **kwargs: Additional parameters

        Returns:
            Generated code
        """
        return await self.execute_tool("generate_code", {
            "description": description,
            **kwargs
        })

    async def analyze_context(self, file_path: str, **kwargs) -> Dict[str, Any]:
        """
        Analyze file context.

        Args:
            file_path: Path to file
            **kwargs: Additional parameters

        Returns:
            Context analysis
        """
        return await self.execute_tool("analyze_context", {
            "file_path": file_path,
            **kwargs
        })

    async def execute_tool(self, tool_name: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute any mcprag tool.

        Args:
            tool_name: Name of the tool
            params: Tool parameters

        Returns:
            Tool execution result
        """
        if not self.session_token:
            raise AuthenticationError("Not authenticated")

        headers = {"Authorization": f"Bearer {self.session_token}"}
        params = params or {}

        async with self.session.post(
            f"{self.base_url}/mcp/tool/{tool_name}",
            json=params,
            headers=headers
        ) as resp:
            if resp.status == 401:
                raise AuthenticationError("Session expired or invalid")
            elif resp.status == 403:
                error = await resp.text()
                raise PermissionError(f"Access denied: {error}")
            elif resp.status == 404:
                raise ToolExecutionError(f"Tool '{tool_name}' not found")
            elif resp.status != 200:
                error = await resp.text()
                raise ToolExecutionError(f"Tool execution failed: {error}")

            return await resp.json()

    async def stream_events(self) -> AsyncIterator[Dict[str, Any]]:
        """
        Connect to SSE stream for real-time events.

        Yields:
            Server events
        """
        if not self.session_token:
            raise AuthenticationError("Not authenticated")

        headers = {"Authorization": f"Bearer {self.session_token}"}

        async with sse_client.EventSource(
            f"{self.base_url}/mcp/sse",
            headers=headers,
            session=self.session
        ) as event_source:
            async for event in event_source:
                if event.data:
                    try:
                        yield json.loads(event.data)
                    except json.JSONDecodeError:
                        pass  # Skip malformed events

# Convenience functions
async def quick_search(query: str, base_url: str = None) -> Dict[str, Any]:
    """
    Quick search without persistent client.

    Args:
        query: Search query
        base_url: Server URL

    Returns:
        Search results
    """
    async with MCPRAGClient(base_url) as client:
        # Try to use saved session
        if not client.session_token:
            raise AuthenticationError("No saved session. Please authenticate first.")

        return await client.search_code(query)

# Example CLI usage
async def main():
    """Example usage."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m mcprag_client [auth|search|tool] ...")
        return

    command = sys.argv[1]

    async with MCPRAGClient() as client:
        if command == "auth":
            if len(sys.argv) < 3:
                print("Usage: python -m mcprag_client auth <email>")
                return

            email = sys.argv[2]
            await client.authenticate(email)

            print("Enter the token from your email:")
            token = input().strip()

            result = await client.complete_auth(token)
            print(f"Authenticated as {result['email']} (tier: {result['tier']})")

        elif command == "search":
            if len(sys.argv) < 3:
                print("Usage: python -m mcprag_client search <query>")
                return

            query = " ".join(sys.argv[2:])
            results = await client.search_code(query)

            print(json.dumps(results, indent=2))

        elif command == "tool":
            if len(sys.argv) < 4:
                print("Usage: python -m mcprag_client tool <name> <json_params>")
                return

            tool_name = sys.argv[2]
            params = json.loads(sys.argv[3])

            result = await client.execute_tool(tool_name, params)
            print(json.dumps(result, indent=2))

        elif command == "list":
            tools = await client.list_tools()
            print(f"Available tools ({tools['total']} total):")
            for tool in tools['tools']:
                print(f"  - {tool['name']} (tier: {tool['tier']})")

        elif command == "health":
            health = await client.health_check()
            print(json.dumps(health, indent=2))

        else:
            print(f"Unknown command: {command}")

if __name__ == "__main__":
    asyncio.run(main())
```

This comprehensive approach will help you build a robust, secure, and efficient remote MCP server with all the necessary features for AI integration.

#### Sources:

- [[MCP Architecture Component Overview]]
- [[Core Tool Categories and Roles in MCP Architecture]]
- [[mcp-expert-agent-azure-ai-search-rag-code-tools]]
- [[prompt-engineer]]
- [[mcp-testing-engineer-azure-ai-search-rag-debug-validation]]
- [[MCP Python SDK Overview]]
