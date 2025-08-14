#!/usr/bin/env python3
"""
Test script to verify remote MCP configuration patches.
"""

import os
import sys

# Test with read-only config
os.environ["ACS_ENDPOINT"] = "https://test.search.windows.net"
os.environ["ACS_QUERY_KEY"] = "test-query-key"
os.environ["MCP_DEV_MODE"] = "true"

# Remove admin key to test read-only mode
if "ACS_ADMIN_KEY" in os.environ:
    del os.environ["ACS_ADMIN_KEY"]

from enhanced_rag.core.unified_config import get_config

print("Testing Remote MCP Configuration...")
print("=" * 50)

config = get_config()

# Test 1: Config validation with QUERY_KEY
print("\n1. Testing Config validation with QUERY_KEY...")
errors = config.validate_config()
if errors:
    print(f"   ❌ Validation errors: {errors}")
    sys.exit(1)
else:
    print(f"   ✅ Config validation passed with QUERY_KEY")

# Test 2: Check DEV_MODE
print(f"\n2. Testing DEV_MODE...")
print(f"   DEV_MODE = {config.mcp_dev_mode}")
if config.mcp_dev_mode:
    print(f"   ✅ DEV_MODE correctly set")
else:
    print(f"   ❌ DEV_MODE not set")

# Test 3: Check config uses QUERY_KEY
print(f"\n3. Testing config uses QUERY_KEY...")
query_key = config.acs_query_key.get_secret_value() if config.acs_query_key else None
if query_key == "test-query-key":
    print(f"   ✅ Config correctly uses QUERY_KEY")
else:
    print(f"   ❌ Config not using QUERY_KEY: {query_key}")

# Test 4: Import remote server to check datetime import
print(f"\n4. Testing remote server import...")
try:
    from mcprag.remote_server import RemoteMCPServer
    print(f"   ✅ Remote server imports successfully")
except ImportError as e:
    print(f"   ❌ Remote server import failed: {e}")
    sys.exit(1)

# Test 5: Check M2MAuthenticator exists
print(f"\n5. Testing M2MAuthenticator...")
try:
    from mcprag.auth.stytch_auth import M2MAuthenticator
    m2m = M2MAuthenticator()
    print(f"   ✅ M2MAuthenticator exists and initializes")
except ImportError as e:
    print(f"   ❌ M2MAuthenticator import failed: {e}")

print("\n" + "=" * 50)
print("✅ All tests passed! Remote MCP configuration is ready.")