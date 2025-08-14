"""
Azure Code Search MCP Server.

A modular implementation that leverages enhanced_rag
for advanced search capabilities.
"""

from .server import MCPServer, create_server
from enhanced_rag.core.unified_config import UnifiedConfig as Config

__version__ = "3.0.0"

__all__ = ["MCPServer", "create_server", "Config"]
