"""
MCP Protocol to REST API Adapter.

STATUS: Experimental helper not used by the core server. This adapter translates
MCP protocol messages to remote HTTP calls and can be run as a standalone MCP
server to proxy to the remote API. It’s useful for demos or bridging clients,
but safe to remove if you standardize on the built-in `mcp_bridge.py`.
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Literal, Union
import aiohttp
from dataclasses import dataclass

# MCP SDK imports with proper type handling
try:
    from mcp.server.fastmcp import FastMCP
    from mcp.types import TextContent
    MCP_SDK_AVAILABLE = True
except ImportError:
    MCP_SDK_AVAILABLE = False
    FastMCP = None  # type: ignore
    TextContent = None  # type: ignore

logger = logging.getLogger(__name__)


@dataclass
class RemoteServerConfig:
    """Configuration for the remote server."""
    base_url: str = "http://localhost:8002"
    session_token: str = "dev-mode"  # Default for development
    timeout: int = 30


class MCPRestAdapter:
    """Adapter that translates MCP protocol to REST API calls."""

    def __init__(self, config: Optional[RemoteServerConfig] = None):
        """Initialize the adapter."""
        self.config = config or RemoteServerConfig()
        self.session: Optional[aiohttp.ClientSession] = None
        self.name = "mcprag-remote-adapter"
        self.version = "1.0.0"

        # Initialize FastMCP with proper type handling
        if MCP_SDK_AVAILABLE and FastMCP is not None:
            self.mcp = FastMCP(self.name)
        else:
            # Create mock MCP for testing
            class MockMCP:
                def tool(self):
                    return lambda f: f
                def run(self, transport):
                    print(f"Mock MCP adapter running in {transport} mode")
            self.mcp = MockMCP()  # type: ignore

        # Cache for tools
        self._tools_cache: Optional[List[Dict[str, Any]]] = None

        self._register_mcp_handlers()

    async def _ensure_session(self):
        """Ensure HTTP session exists."""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    "Authorization": f"Bearer {self.config.session_token}",
                    "Content-Type": "application/json"
                }
            )

    async def _make_request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request to remote server."""
        await self._ensure_session()

        url = f"{self.config.base_url}{path}"

        if self.session is None:
            raise Exception("HTTP session not initialized")

        try:
            async with self.session.request(method, url, **kwargs) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 401:
                    raise Exception("Authentication failed - check session token")
                elif response.status == 403:
                    raise Exception("Access denied - insufficient permissions")
                elif response.status == 404:
                    raise Exception(f"Endpoint not found: {path}")
                else:
                    error_text = await response.text()
                    raise Exception(f"HTTP {response.status}: {error_text}")
        except aiohttp.ClientError as e:
            raise Exception(f"Connection error: {e}")

    def _register_mcp_handlers(self):
        """Register MCP protocol handlers."""

        @self.mcp.tool()
        async def search_code(query: str, intent: str = "understand") -> str:
            """
            Search for code using the remote server.

            Args:
                query: Search query
                intent: Search intent (understand, implement, debug, refactor)
            """
            try:
                response = await self._make_request(
                    "POST",
                    "/mcp/tool/search_code",
                    json={"query": query, "intent": intent}
                )

                if "result" in response:
                    return str(response["result"])
                else:
                    return "No results found"

            except Exception as e:
                logger.error(f"Search failed: {e}")
                return f"Search error: {e}"

        @self.mcp.tool()
        async def generate_code(
            description: str,
            language: str = "python",
            style: str = "clean"
        ) -> str:
            """
            Generate code using the remote server.

            Args:
                description: What to generate
                language: Programming language
                style: Code style (clean, minimal, verbose)
            """
            try:
                response = await self._make_request(
                    "POST",
                    "/mcp/tool/generate_code",
                    json={
                        "description": description,
                        "language": language,
                        "style": style
                    }
                )

                if "result" in response:
                    return str(response["result"])
                else:
                    return "No code generated"

            except Exception as e:
                logger.error(f"Code generation failed: {e}")
                return f"Generation error: {e}"

        @self.mcp.tool()
        async def analyze_code(
            code: str,
            analysis_type: str = "general"
        ) -> str:
            """
            Analyze code using the remote server.

            Args:
                code: Code to analyze
                analysis_type: Type of analysis (general, security, performance, style)
            """
            try:
                response = await self._make_request(
                    "POST",
                    "/mcp/tool/analyze_code",
                    json={
                        "code": code,
                        "analysis_type": analysis_type
                    }
                )

                if "result" in response:
                    return str(response["result"])
                else:
                    return "No analysis available"

            except Exception as e:
                logger.error(f"Code analysis failed: {e}")
                return f"Analysis error: {e}"

        @self.mcp.tool()
        async def get_context(
            file_path: str,
            context_type: str = "file"
        ) -> str:
            """
            Get contextual information using the remote server.

            Args:
                file_path: Path to file or directory
                context_type: Type of context (file, directory, project)
            """
            try:
                response = await self._make_request(
                    "POST",
                    "/mcp/tool/get_context",
                    json={
                        "file_path": file_path,
                        "context_type": context_type
                    }
                )

                if "result" in response:
                    return str(response["result"])
                else:
                    return "No context available"

            except Exception as e:
                logger.error(f"Context retrieval failed: {e}")
                return f"Context error: {e}"

        # Admin tools (require higher permissions)
        @self.mcp.tool()
        async def list_repositories() -> str:
            """List indexed repositories (admin tool)."""
            try:
                response = await self._make_request("GET", "/mcp/tool/list_repositories")
                if "result" in response:
                    return str(response["result"])
                else:
                    return "No repositories found"
            except Exception as e:
                logger.error(f"Repository listing failed: {e}")
                return f"Admin error: {e}"

        @self.mcp.tool()
        async def get_server_status() -> str:
            """Get remote server status."""
            try:
                response = await self._make_request("GET", "/health")
                return json.dumps(response, indent=2)
            except Exception as e:
                logger.error(f"Status check failed: {e}")
                return f"Status error: {e}"

    async def cleanup(self):
        """Clean up resources."""
        if self.session and not self.session.closed:
            await self.session.close()

    def run(self, transport: Literal["stdio", "sse", "streamable-http"] = "stdio"):
        """Run the MCP adapter."""
        logger.info(f"Starting MCP-REST adapter for {self.config.base_url}")

        try:
            self.mcp.run(transport=transport)
        finally:
            # Cleanup on exit
            asyncio.run(self.cleanup())


def create_adapter(base_url: str = "http://localhost:8002", session_token: str = "dev-mode") -> MCPRestAdapter:
    """Create MCP-REST adapter instance."""
    config = RemoteServerConfig(base_url=base_url, session_token=session_token)
    return MCPRestAdapter(config)


def main():
    """Main entry point for the adapter."""
    import sys

    # Parse command line arguments
    base_url = "http://localhost:8002"
    session_token = "dev-mode"

    if "--url" in sys.argv:
        idx = sys.argv.index("--url")
        if idx + 1 < len(sys.argv):
            base_url = sys.argv[idx + 1]

    if "--token" in sys.argv:
        idx = sys.argv.index("--token")
        if idx + 1 < len(sys.argv):
            session_token = sys.argv[idx + 1]

    # Create and run adapter
    adapter = create_adapter(base_url, session_token)
    adapter.run()


if __name__ == "__main__":
    main()
