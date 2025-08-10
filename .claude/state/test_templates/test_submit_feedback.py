"""Tests for submit_feedback MCP tool"""
import pytest
import asyncio
from mcprag.server import MCPServer
from mcprag.mcp.tools._helpers import submit_feedback_impl  # Update import path

@pytest.fixture
async def server():
    """Create test server"""
    server = MCPServer()
    await server.start_async_components()
    yield server
    await server.cleanup_async_components()

@pytest.mark.asyncio
async def test_submit_feedback_basic(server):
    """Test basic submit_feedback functionality"""
    result = await submit_feedback_impl(
        server=server,
        # Add required parameters
                target_id=...,
        kind=...,
        rating=...,
    )
    
    assert result["status"] != "error"
    assert "data" in result
    # Add specific assertions

@pytest.mark.asyncio  
async def test_submit_feedback_error_handling(server):
    """Test submit_feedback error handling"""
    result = await submit_feedback_impl(
        server=server,
        # Invalid parameters to trigger error
    )
    
    assert result["status"] == "error"
    assert "message" in result
