"""
MCP integration module.

Provides tool, resource, and prompt registration for the MCP server.
"""

from .tools import register_tools
from .resources import register_resources
from .prompts import register_prompts

__all__ = ["register_tools", "register_resources", "register_prompts"]
