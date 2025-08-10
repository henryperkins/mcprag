"""Tests for create_skillset MCP tool"""
import pytest
import asyncio
from mcprag.server import MCPServer
from mcprag.mcp.tools._helpers import create_skillset_impl  # Update import path

@pytest.fixture
async def server():
    """Create test server"""
    server = MCPServer()
    await server.start_async_components()
    yield server
    await server.cleanup_async_components()

@pytest.mark.asyncio
async def test_create_skillset_basic(server):
    """Test basic create_skillset functionality"""
    result = await create_skillset_impl(
        server=server,
        # Add required parameters
                name=...,
        skills=...,
        knowledge_store=...,
    )
    
    assert result["status"] != "error"
    assert "data" in result
    # Add specific assertions

@pytest.mark.asyncio  
async def test_create_skillset_error_handling(server):
    """Test create_skillset error handling"""
    result = await create_skillset_impl(
        server=server,
        # Invalid parameters to trigger error
    )
    
    assert result["status"] == "error"
    assert "message" in result
