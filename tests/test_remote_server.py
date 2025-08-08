"""
Tests for remote MCP server functionality.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from mcprag.remote_server import RemoteMCPServer, create_app
from mcprag.auth.tool_security import SecurityTier, get_tool_tier
from mcprag.auth.stytch_auth import StytchAuthenticator


@pytest.fixture
async def remote_server():
    """Create a remote server instance for testing."""
    server = RemoteMCPServer()
    # Mock components
    server.enhanced_search = Mock()
    server.pipeline = Mock()
    server.cache_manager = Mock()
    server.redis = None  # Use in-memory storage
    
    # Initialize auth without Redis
    await server.auth.initialize(None)
    
    yield server
    
    # Cleanup
    await server.shutdown()


@pytest.fixture
async def test_client(remote_server):
    """Create a test client for the FastAPI app."""
    from httpx import AsyncClient
    
    app = remote_server.create_app()
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


class TestToolSecurity:
    """Test tool security classification."""
    
    def test_tool_tier_mapping(self):
        """Test that tools are correctly mapped to security tiers."""
        # Public tools
        assert get_tool_tier("search_code") == SecurityTier.PUBLIC
        assert get_tool_tier("health_check") == SecurityTier.PUBLIC
        assert get_tool_tier("index_status") == SecurityTier.PUBLIC
        
        # Developer tools
        assert get_tool_tier("generate_code") == SecurityTier.DEVELOPER
        assert get_tool_tier("analyze_context") == SecurityTier.DEVELOPER
        
        # Admin tools
        assert get_tool_tier("index_rebuild") == SecurityTier.ADMIN
        assert get_tool_tier("manage_index") == SecurityTier.ADMIN
        assert get_tool_tier("rebuild_index") == SecurityTier.ADMIN
        
        # Unknown tools default to admin
        assert get_tool_tier("unknown_tool") == SecurityTier.ADMIN
    
    def test_tier_hierarchy(self):
        """Test that tier hierarchy is enforced correctly."""
        from mcprag.auth.tool_security import user_meets_tier_requirement
        
        # Public user can only access public tools
        assert user_meets_tier_requirement(SecurityTier.PUBLIC, SecurityTier.PUBLIC)
        assert not user_meets_tier_requirement(SecurityTier.PUBLIC, SecurityTier.DEVELOPER)
        assert not user_meets_tier_requirement(SecurityTier.PUBLIC, SecurityTier.ADMIN)
        
        # Developer can access public and developer tools
        assert user_meets_tier_requirement(SecurityTier.DEVELOPER, SecurityTier.PUBLIC)
        assert user_meets_tier_requirement(SecurityTier.DEVELOPER, SecurityTier.DEVELOPER)
        assert not user_meets_tier_requirement(SecurityTier.DEVELOPER, SecurityTier.ADMIN)
        
        # Admin can access all tools
        assert user_meets_tier_requirement(SecurityTier.ADMIN, SecurityTier.PUBLIC)
        assert user_meets_tier_requirement(SecurityTier.ADMIN, SecurityTier.DEVELOPER)
        assert user_meets_tier_requirement(SecurityTier.ADMIN, SecurityTier.ADMIN)
        
        # Service accounts have admin access
        assert user_meets_tier_requirement(SecurityTier.SERVICE, SecurityTier.ADMIN)


class TestAuthentication:
    """Test authentication functionality."""
    
    @pytest.mark.asyncio
    async def test_health_check_unauthenticated(self, test_client):
        """Test that health check works without authentication."""
        response = await test_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "components" in data
    
    @pytest.mark.asyncio
    async def test_magic_link_flow(self, test_client):
        """Test magic link authentication flow."""
        with patch('mcprag.auth.stytch_auth.STYTCH_AVAILABLE', False):
            # Send magic link (will fail without Stytch)
            response = await test_client.post(
                "/auth/login",
                json={"email": "test@example.com"}
            )
            
            # Should return 503 when Stytch not configured
            assert response.status_code == 503
    
    @pytest.mark.asyncio
    async def test_dev_mode_auth(self, remote_server):
        """Test development mode authentication bypass."""
        with patch.dict('os.environ', {'MCP_DEV_MODE': 'true'}):
            auth = StytchAuthenticator()
            auth.enabled = False  # Simulate no Stytch
            
            # Complete auth should work in dev mode
            result = await auth.complete_authentication("dev_token")
            
            assert result["user_id"] == "dev_user"
            assert result["tier"] == "admin"
            assert result["mfa_required"] == False
    
    @pytest.mark.asyncio
    async def test_session_management(self, remote_server):
        """Test session storage and retrieval."""
        auth = remote_server.auth
        
        # Store a test session
        session_data = {
            "session_id": "test_session",
            "user_id": "test_user",
            "email": "test@example.com",
            "tier": "developer",
            "expires_at": (datetime.utcnow() + timedelta(hours=8)).isoformat(),
            "mfa_verified": False
        }
        
        await auth._store_session("test_session", session_data)
        
        # Retrieve session
        retrieved = await auth._get_session("test_session")
        
        assert retrieved["user_id"] == "test_user"
        assert retrieved["tier"] == "developer"


class TestToolExecution:
    """Test tool execution with permissions."""
    
    @pytest.mark.asyncio
    async def test_tool_list_with_permissions(self, test_client, remote_server):
        """Test listing tools based on user tier."""
        # Mock user with developer tier
        async def mock_get_user(authorization=None):
            return {
                "user_id": "test",
                "email": "test@example.com",
                "tier": "developer",
                "session_id": "test",
                "mfa_verified": False
            }
        
        with patch.object(remote_server.auth, 'get_current_user', mock_get_user):
            # Mock some tools on the mcp instance
            remote_server.mcp.tool_search_code = AsyncMock()
            remote_server.mcp.tool_generate_code = AsyncMock()
            remote_server.mcp.tool_manage_index = AsyncMock()
            
            app = remote_server.create_app()
            from httpx import AsyncClient
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get(
                    "/mcp/tools",
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 200
                data = response.json()
                
                # Developer should see public and developer tools
                tool_names = [t["name"] for t in data["tools"]]
                assert "search_code" in tool_names  # Public tool
                assert "generate_code" in tool_names  # Developer tool
                assert "manage_index" not in tool_names  # Admin tool (should not be visible)
    
    @pytest.mark.asyncio
    async def test_permission_denied(self, test_client, remote_server):
        """Test that insufficient permissions are properly handled."""
        # Mock user with public tier
        async def mock_get_user(authorization=None):
            return {
                "user_id": "test",
                "email": "test@example.com",
                "tier": "public",
                "session_id": "test",
                "mfa_verified": False
            }
        
        with patch.object(remote_server.auth, 'get_current_user', mock_get_user):
            # Mock the tool
            remote_server.mcp.tool_manage_index = AsyncMock()
            
            app = remote_server.create_app()
            from httpx import AsyncClient
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                # Try to execute admin tool as public user
                response = await client.post(
                    "/mcp/tool/manage_index",
                    json={"action": "list"},
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 403
                assert "Insufficient permissions" in response.text
    
    @pytest.mark.asyncio
    async def test_mfa_required_for_admin(self, test_client, remote_server):
        """Test that MFA is required for admin operations."""
        # Mock user with admin tier but no MFA
        async def mock_get_user(authorization=None):
            return {
                "user_id": "test",
                "email": "admin@example.com",
                "tier": "admin",
                "session_id": "test",
                "mfa_verified": False
            }
        
        with patch.object(remote_server.auth, 'get_current_user', mock_get_user):
            # Mock the tool
            remote_server.mcp.tool_rebuild_index = AsyncMock()
            
            app = remote_server.create_app()
            from httpx import AsyncClient
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                # Try to execute admin tool without MFA
                response = await client.post(
                    "/mcp/tool/rebuild_index",
                    json={"confirm": True},
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 403
                assert "MFA verification required" in response.text
    
    @pytest.mark.asyncio
    async def test_successful_tool_execution(self, test_client, remote_server):
        """Test successful tool execution with proper permissions."""
        # Mock user with developer tier
        async def mock_get_user(authorization=None):
            return {
                "user_id": "test",
                "email": "dev@example.com",
                "tier": "developer",
                "session_id": "test",
                "mfa_verified": False
            }
        
        async def mock_search(**kwargs):
            return {"results": ["result1", "result2"], "total": 2}
        
        with patch.object(remote_server.auth, 'get_current_user', mock_get_user):
            # Mock the tool
            remote_server.mcp.tool_search_code = mock_search
            
            app = remote_server.create_app()
            from httpx import AsyncClient
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                # Execute search tool as developer
                response = await client.post(
                    "/mcp/tool/search_code",
                    json={"query": "test"},
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["total"] == 2
                assert len(data["results"]) == 2


class TestSSEStreaming:
    """Test Server-Sent Events streaming."""
    
    @pytest.mark.asyncio
    async def test_sse_connection(self, remote_server):
        """Test SSE connection and event broadcasting."""
        # Add a test user queue
        user_id = "test_user"
        queue = asyncio.Queue()
        remote_server._user_queues[user_id] = queue
        
        # Broadcast an event
        await remote_server.broadcast_to_user(
            user_id,
            "test_event",
            {"message": "Hello, SSE!"}
        )
        
        # Check that event was queued
        event = await queue.get()
        assert event["type"] == "test_event"
        assert event["data"]["message"] == "Hello, SSE!"
        
        # Cleanup
        del remote_server._user_queues[user_id]


class TestM2MAuthentication:
    """Test machine-to-machine authentication."""
    
    @pytest.mark.asyncio
    async def test_m2m_token_generation(self, test_client):
        """Test M2M token generation."""
        with patch('mcprag.auth.stytch_auth.STYTCH_AVAILABLE', False):
            # In dev mode, should return mock token
            response = await test_client.post(
                "/auth/m2m/token",
                json={
                    "client_id": "test_client",
                    "client_secret": "test_secret"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert data["tier"] == "service"


class TestAuditLogging:
    """Test audit logging functionality."""
    
    @pytest.mark.asyncio
    async def test_audit_log_creation(self, remote_server):
        """Test that audit logs are created for tool executions."""
        # Mock feedback collector
        remote_server.feedback_collector = AsyncMock()
        
        # Create test user and tool data
        user = {
            "user_id": "test_user",
            "email": "test@example.com",
            "tier": "developer"
        }
        
        # Log a successful execution
        await remote_server._audit_log(
            user,
            "search_code",
            {"query": "test"},
            {"success": True}
        )
        
        # Verify feedback collector was called
        if remote_server.feedback_collector:
            remote_server.feedback_collector.track_tool_usage.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])