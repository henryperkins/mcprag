"""Tests for manage_documents MCP tool"""
import pytest
import asyncio
from mcprag.server import MCPServer
from mcprag.mcp.tools._helpers import manage_documents_impl  # Update import path

@pytest.fixture
async def server():
    """Create test server"""
    server = MCPServer()
    await server.start_async_components()
    yield server
    await server.cleanup_async_components()

@pytest.mark.asyncio
async def test_manage_documents_basic(server):
    """Test basic manage_documents functionality"""
    result = await manage_documents_impl(
        server=server,
        # Add required parameters
                action=...,
        index_name=...,
        documents=...,
    )
    
    assert result["status"] != "error"
    assert "data" in result
    # Add specific assertions

@pytest.mark.asyncio  
async def test_manage_documents_error_handling(server):
    """Test manage_documents error handling"""
    result = await manage_documents_impl(
        server=server,
        # Invalid parameters to trigger error
    )
    
    assert result["status"] == "error"
    assert "message" in result
