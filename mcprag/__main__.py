"""
Main entry point for the MCP server.

This replaces the direct execution of mcp_server_sota.py
"""

# Entry when running as a module: python -m mcprag
# Import main from local package server module
from .server import main

if __name__ == "__main__":
    main()
