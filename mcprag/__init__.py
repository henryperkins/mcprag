"""
Azure Code Search MCP Server.

A modular implementation that leverages enhanced_rag
for advanced search capabilities.
"""

from .server import MCPServer, create_server
from .config import Config

__version__ = "3.0.0"

__all__ = ["MCPServer", "create_server", "Config"]
