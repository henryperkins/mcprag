"""
Configuration management for Azure Code Search MCP.

Centralizes all environment variable access.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Central configuration for the MCP server."""

    # Azure Search Configuration
    ENDPOINT: str = os.getenv("ACS_ENDPOINT", "")
    ADMIN_KEY: str = os.getenv("ACS_ADMIN_KEY", "")
    INDEX_NAME: str = os.getenv("ACS_INDEX_NAME", "codebase-mcp-sota")

    # Azure OpenAI Configuration (for vector search)
    AZURE_OPENAI_KEY: Optional[str] = os.getenv("AZURE_OPENAI_KEY") or os.getenv(
        "AZURE_OPENAI_API_KEY"
    )
    AZURE_OPENAI_ENDPOINT: Optional[str] = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_DEPLOYMENT: Optional[str] = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")

    # Cache Configuration
    CACHE_TTL_SECONDS: int = int(os.getenv("MCP_CACHE_TTL_SECONDS", "60"))
    CACHE_MAX_ENTRIES: int = int(os.getenv("MCP_CACHE_MAX_ENTRIES", "500"))

    # Admin Configuration
    ADMIN_MODE: bool = os.getenv("MCP_ADMIN_MODE", "1").lower() in {"1", "true", "yes"}

    # Feedback Configuration
    FEEDBACK_DIR: Path = Path(os.getenv("MCP_FEEDBACK_DIR", ".mcp_feedback"))

    # Debug Configuration
    DEBUG_TIMINGS: bool = os.getenv("MCP_DEBUG_TIMINGS", "").lower() in {"1", "true"}
    LOG_LEVEL: str = os.getenv("MCP_LOG_LEVEL", "INFO")

    @classmethod
    def validate(cls) -> Dict[str, str]:
        """Validate required configuration."""
        errors = {}

        if not cls.ENDPOINT:
            errors["endpoint"] = "ACS_ENDPOINT environment variable is required"

        if not cls.ADMIN_KEY:
            errors["admin_key"] = "ACS_ADMIN_KEY environment variable is required"

        # Create feedback directory
        try:
            cls.FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            errors["feedback_dir"] = str(e)

        return errors

    @classmethod
    def get_rag_config(cls) -> Dict[str, Any]:
        """Get configuration dict for enhanced_rag modules."""
        return {
            "azure_endpoint": cls.ENDPOINT,
            "azure_key": cls.ADMIN_KEY,
            "index_name": cls.INDEX_NAME,
            "enable_caching": True,
            "cache_ttl": cls.CACHE_TTL_SECONDS,
            "cache_max_entries": cls.CACHE_MAX_ENTRIES,
            "feedback_dir": str(cls.FEEDBACK_DIR),
        }

    @classmethod
    def get_openai_config(cls) -> Optional[Dict[str, str]]:
        """Get OpenAI configuration if available."""
        if cls.AZURE_OPENAI_KEY and cls.AZURE_OPENAI_ENDPOINT:
            return {
                "api_key": cls.AZURE_OPENAI_KEY,
                "endpoint": cls.AZURE_OPENAI_ENDPOINT,
                "deployment": cls.AZURE_OPENAI_DEPLOYMENT or "text-embedding-ada-002",
                "provider": "azure",
            }
        elif cls.OPENAI_API_KEY:
            return {"api_key": cls.OPENAI_API_KEY, "provider": "openai"}
        return None
