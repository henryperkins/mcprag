#!/usr/bin/env python3
"""
MCP Bridge Server - Translates MCP protocol to REST API calls
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional

import httpx
from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Remote server configuration
REMOTE_BASE_URL = os.getenv("MCPRAG_REMOTE_URL", "http://localhost:8002")
SESSION_TOKEN = os.getenv("MCPRAG_SESSION_TOKEN", "dev-mode")

# Initialize FastMCP server
mcp = FastMCP("mcprag-bridge")

# HTTP client for API calls
http_client = None

async def get_http_client():
    """Get or create HTTP client"""
    global http_client
    if http_client is None:
        http_client = httpx.AsyncClient(
            base_url=REMOTE_BASE_URL,
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"},
            timeout=30.0
        )
    return http_client

async def call_remote_tool(tool_name: str, **params) -> Dict[str, Any]:
    """Call a tool on the remote REST API"""
    try:
        client = await get_http_client()
        response = await client.post(
            f"/mcp/tool/{tool_name}",
            json=params
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error calling remote tool {tool_name}: {e}")
        return {"error": str(e)}

@mcp.tool()
async def search_code(
    query: str,
    intent: str = "understand",
    file_types: Optional[List[str]] = None,
    repository: Optional[str] = None,
    context_files: Optional[List[str]] = None,
    max_results: int = 10
) -> Dict[str, Any]:
    """Search for code snippets using semantic and keyword search"""
    params = {
        "query": query,
        "intent": intent,
        "max_results": max_results
    }

    if file_types:
        params["file_types"] = file_types
    if repository:
        params["repository"] = repository
    if context_files:
        params["context_files"] = context_files

    return await call_remote_tool("search_code", **params)

@mcp.tool()
async def analyze_code_structure(
    file_path: str,
    repository: Optional[str] = None
) -> Dict[str, Any]:
    """Analyze the structure and dependencies of a code file"""
    params = {"file_path": file_path}
    if repository:
        params["repository"] = repository

    return await call_remote_tool("analyze_code_structure", **params)

@mcp.tool()
async def get_implementation_examples(
    pattern: str,
    language: Optional[str] = None,
    repository: Optional[str] = None,
    max_results: int = 5
) -> Dict[str, Any]:
    """Find implementation examples for a specific pattern or concept"""
    params = {
        "pattern": pattern,
        "max_results": max_results
    }

    if language:
        params["language"] = language
    if repository:
        params["repository"] = repository

    return await call_remote_tool("get_implementation_examples", **params)

@mcp.tool()
async def explain_code_context(
    file_path: str,
    line_range: Optional[List[int]] = None,
    repository: Optional[str] = None
) -> Dict[str, Any]:
    """Explain the context and purpose of code in a specific file or line range"""
    params = {"file_path": file_path}

    if line_range:
        params["line_range"] = json.dumps(line_range)
    if repository:
        params["repository"] = repository

    return await call_remote_tool("explain_code_context", **params)

@mcp.tool()
async def suggest_improvements(
    code_snippet: str,
    language: Optional[str] = None,
    context: Optional[str] = None
) -> Dict[str, Any]:
    """Suggest improvements for a code snippet"""
    params = {"code_snippet": code_snippet}

    if language:
        params["language"] = language
    if context:
        params["context"] = context

    return await call_remote_tool("suggest_improvements", **params)

@mcp.tool()
async def find_related_functions(
    function_name: str,
    repository: Optional[str] = None,
    max_results: int = 10
) -> Dict[str, Any]:
    """Find functions related to a given function"""
    params = {
        "function_name": function_name,
        "max_results": max_results
    }

    if repository:
        params["repository"] = repository

    return await call_remote_tool("find_related_functions", **params)

@mcp.tool()
async def generate_code_documentation(
    code_snippet: str,
    language: Optional[str] = None,
    style: str = "google"
) -> Dict[str, Any]:
    """Generate documentation for a code snippet"""
    params = {
        "code_snippet": code_snippet,
        "style": style
    }

    if language:
        params["language"] = language

    return await call_remote_tool("generate_code_documentation", **params)

@mcp.tool()
async def list_repositories() -> Dict[str, Any]:
    """List all indexed repositories"""
    return await call_remote_tool("list_repositories")

@mcp.tool()
async def get_repository_stats(repository: str) -> Dict[str, Any]:
    """Get statistics for a specific repository"""
    return await call_remote_tool("get_repository_stats", repository=repository)

@mcp.tool()
async def health_check() -> Dict[str, Any]:
    """Check the health status of the remote server"""
    try:
        client = await get_http_client()
        response = await client.get("/health")
        response.raise_for_status()
        return {"status": "healthy", "remote_url": REMOTE_BASE_URL}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e), "remote_url": REMOTE_BASE_URL}

# Resource for providing server information
@mcp.resource("server://info")
async def get_server_info() -> str:
    """Get information about this bridge server"""
    info = {
        "name": "mcprag-bridge",
        "description": "MCP Bridge Server for MCPRAG Remote API",
        "remote_url": REMOTE_BASE_URL,
        "session_token": "configured" if SESSION_TOKEN != "dev-mode" else "dev-mode",
        "tools_count": 10
    }
    return json.dumps(info, indent=2)

async def cleanup():
    """Cleanup resources on shutdown"""
    global http_client
    if http_client:
        await http_client.aclose()
        http_client = None

def main():
    """Main entry point"""
    logger.info(f"Starting MCP Bridge Server...")
    logger.info(f"Remote URL: {REMOTE_BASE_URL}")
    logger.info(f"Session Token: {'configured' if SESSION_TOKEN != 'dev-mode' else 'dev-mode'}")

    try:
        # Run the MCP server
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        # Cleanup
        try:
            asyncio.run(cleanup())
        except:
            pass

if __name__ == "__main__":
    main()
