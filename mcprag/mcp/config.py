"""Configuration for MCP server."""
import os


class Config:
    """Configuration settings for MCP server."""

    # Admin mode controls destructive operations
    ADMIN_MODE = os.getenv("MCP_ADMIN_MODE", "false").lower() == "true"

    # Azure Search settings
    ACS_ENDPOINT = os.getenv("ACS_ENDPOINT", "")
    ACS_ADMIN_KEY = os.getenv("ACS_ADMIN_KEY", "")

    # Other settings can be added here
