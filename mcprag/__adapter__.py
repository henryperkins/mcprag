#!/usr/bin/env python3
"""
Entry point for MCP-REST adapter.

This script creates an MCP server that adapts the remote REST API
to work with Claude Code and other MCP clients.
"""

import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcprag.mcp_rest_adapter import main

if __name__ == "__main__":
    main()
