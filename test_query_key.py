#!/usr/bin/env python3
"""Test that QUERY_KEY works when ADMIN_KEY is not available."""

import os
import sys

# Save original admin key
original_admin = os.environ.get("ACS_ADMIN_KEY")

# Remove admin key from environment
if "ACS_ADMIN_KEY" in os.environ:
    del os.environ["ACS_ADMIN_KEY"]

# Set query key
os.environ["ACS_QUERY_KEY"] = "fqoIBpHBOr7M2N1LA91fxgoi4XeW2XGF6l1F7ZBysGAzSeD1Z10w"
os.environ["ACS_ENDPOINT"] = "https://test.search.windows.net"
os.environ["MCP_DEV_MODE"] = "true"

# Now import after env is set
from mcprag.config import Config

print("Testing QUERY_KEY fallback...")
print("=" * 50)

print(f"ADMIN_KEY: {Config.ADMIN_KEY or 'NOT SET'}")
print(f"QUERY_KEY: {Config.QUERY_KEY or 'NOT SET'}")

# Test validation accepts query key
errors = Config.validate()
if errors:
    print(f"❌ Validation failed: {errors}")
else:
    print(f"✅ Validation passed with QUERY_KEY only")

# Test RAG config uses query key
rag_config = Config.get_rag_config()
print(f"RAG config key: {rag_config['azure_key']}")
if rag_config['azure_key'] == "fqoIBpHBOr7M2N1LA91fxgoi4XeW2XGF6l1F7ZBysGAzSeD1Z10w":
    print("✅ RAG config correctly uses QUERY_KEY")
else:
    print("❌ RAG config not using QUERY_KEY")

# Restore original admin key if it existed
if original_admin:
    os.environ["ACS_ADMIN_KEY"] = original_admin