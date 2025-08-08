"""
Configuration management for Azure Code Search MCP.

Centralizes all environment variable access.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

load_dotenv()


class Config:
    """Central configuration for the MCP server."""

    # Azure Search Configuration
    ENDPOINT: str = os.getenv("ACS_ENDPOINT", "")
    # Admin key (write access)
    ADMIN_KEY: str = os.getenv("ACS_ADMIN_KEY", "")
    if not ADMIN_KEY:
        try:
            import keyring  # type: ignore
            ADMIN_KEY = keyring.get_password("mcprag", "ACS_ADMIN_KEY") or ""
            if ADMIN_KEY:
                logger.info("Loaded ACS_ADMIN_KEY from keyring")
        except Exception:
            # Keyring not available or not configured – continue with empty default
            pass
    # Query key (read-only access)
    QUERY_KEY: str = os.getenv("ACS_QUERY_KEY", "")
    INDEX_NAME: str = os.getenv("ACS_INDEX_NAME", "codebase-mcp-sota")

    # Azure OpenAI Configuration (for vector search)
    AZURE_OPENAI_KEY: Optional[str] = os.getenv("AZURE_OPENAI_KEY") or os.getenv(
        "AZURE_OPENAI_API_KEY"
    )
    if not AZURE_OPENAI_KEY:
        try:
            import keyring  # type: ignore
            AZURE_OPENAI_KEY = keyring.get_password("mcprag", "AZURE_OPENAI_KEY")
        except Exception:
            pass
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

    # Remote Server Configuration
    HOST: str = os.getenv("MCP_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("MCP_PORT", "8001"))
    BASE_URL: str = os.getenv("MCP_BASE_URL", "http://localhost:8001")
    ALLOWED_ORIGINS: str = os.getenv("MCP_ALLOWED_ORIGINS", "*")
    
    # Stytch Authentication Configuration
    STYTCH_PROJECT_ID: str = os.getenv("STYTCH_PROJECT_ID", "")
    STYTCH_SECRET: str = os.getenv("STYTCH_SECRET", "")
    STYTCH_ENV: str = os.getenv("STYTCH_ENV", "test")
    SESSION_DURATION_MINUTES: int = int(os.getenv("SESSION_DURATION_MINUTES", "480"))
    
    # Redis Configuration
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # User Tier Configuration
    ADMIN_EMAILS: str = os.getenv("MCP_ADMIN_EMAILS", "")
    DEVELOPER_DOMAINS: str = os.getenv("MCP_DEVELOPER_DOMAINS", "")
    
    # Security Configuration
    REQUIRE_MFA_FOR_ADMIN: bool = os.getenv("MCP_REQUIRE_MFA", "true").lower() == "true"
    # Development mode (bypass auth for localhost/dev)
    DEV_MODE: bool = os.getenv("MCP_DEV_MODE", "").lower() in {"1", "true", "yes"}

    @classmethod
    def validate(cls) -> Dict[str, str]:
        """Validate required configuration."""
        errors = {}

        if not cls.ENDPOINT:
            errors["endpoint"] = "ACS_ENDPOINT environment variable is required"

        # Accept either ADMIN_KEY (write) or QUERY_KEY (read-only)
        if not cls.ADMIN_KEY and not cls.QUERY_KEY:
            errors["api_key"] = "Provide ACS_ADMIN_KEY (admin) or ACS_QUERY_KEY (read-only)"

        # Create feedback directory
        try:
            cls.FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            errors["feedback_dir"] = str(e)

        return errors

    @classmethod
    def get_rag_config(cls) -> Dict[str, Any]:
        """Get configuration dict for enhanced_rag modules."""
        # Prefer ADMIN_KEY if present; fall back to QUERY_KEY for read-only servers
        key = cls.ADMIN_KEY or cls.QUERY_KEY
        return {
            "azure_endpoint": cls.ENDPOINT,
            "azure_key": key,
            "index_name": cls.INDEX_NAME,
            "enable_caching": True,
            "cache_ttl": cls.CACHE_TTL_SECONDS,
            "cache_max_entries": cls.CACHE_MAX_ENTRIES,
            "feedback_dir": str(cls.FEEDBACK_DIR),
        }

    @classmethod
    def validate_remote(cls) -> Dict[str, str]:
        """Validate remote server configuration."""
        errors = {}
        
        if cls.PORT < 1 or cls.PORT > 65535:
            errors["port"] = f"Invalid PORT: {cls.PORT}"
        
        if not cls.BASE_URL:
            errors["base_url"] = "BASE_URL not configured"
        
        # Stytch is optional but warn if not configured
        if not cls.STYTCH_PROJECT_ID or not cls.STYTCH_SECRET:
            logger.warning("Stytch not configured - authentication will be disabled")
        
        return errors

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
