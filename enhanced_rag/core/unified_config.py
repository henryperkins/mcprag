"""
Unified Configuration System for MCP RAG

This module provides a single source of truth for all configuration across:
- MCP Server (mcprag/)
- Enhanced RAG Pipeline (enhanced_rag/)
- Azure Integration (enhanced_rag/azure_integration/)

All environment variables and settings are defined here with Pydantic validation.
"""

import os
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings
from enum import Enum

logger = logging.getLogger(__name__)


class LogLevel(str, Enum):
    """Log level enumeration"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class UnifiedConfig(BaseSettings):
    """
    Unified configuration for the entire MCP RAG system.
    
    This consolidates:
    - mcprag/config.py (MCP server settings)
    - enhanced_rag/core/config.py (RAG pipeline settings)
    - enhanced_rag/azure_integration/config.py (Azure Search settings)
    """
    
    # ============================================================
    # Azure Search Configuration (Required)
    # ============================================================
    acs_endpoint: str = Field(
        ...,
        env="ACS_ENDPOINT",
        description="Azure Cognitive Search endpoint URL"
    )
    acs_admin_key: SecretStr = Field(
        ...,
        env="ACS_ADMIN_KEY",
        description="Azure Search admin key (write access)"
    )
    acs_query_key: Optional[SecretStr] = Field(
        None,
        env="ACS_QUERY_KEY",
        description="Azure Search query key (read-only access)"
    )
    acs_index_name: str = Field(
        "codebase-mcp-sota",
        env="ACS_INDEX_NAME",
        description="Name of the Azure Search index"
    )
    acs_api_version: str = Field(
        "2024-07-01",
        env="ACS_API_VERSION",
        description="Azure Search API version"
    )
    acs_semantic_config: str = Field(
        "enhanced-semantic-config",
        env="ACS_SEMANTIC_CONFIG",
        description="Semantic search configuration name"
    )
    acs_timeout: int = Field(
        30,
        env="ACS_TIMEOUT",
        description="Request timeout in seconds"
    )
    
    # Azure resource settings
    azure_resource_group: Optional[str] = Field(
        None,
        env="AZURE_RESOURCE_GROUP",
        description="Azure resource group name"
    )
    azure_search_service_name: Optional[str] = Field(
        None,
        env="AZURE_SEARCH_SERVICE_NAME",
        description="Azure Search service name (inferred from endpoint if not set)"
    )
    
    # ============================================================
    # Azure OpenAI Configuration (Optional - for embeddings)
    # ============================================================
    azure_openai_endpoint: Optional[str] = Field(
        None,
        env="AZURE_OPENAI_ENDPOINT",
        description="Azure OpenAI endpoint URL"
    )
    azure_openai_key: Optional[SecretStr] = Field(
        None,
        env="AZURE_OPENAI_KEY",
        description="Azure OpenAI API key"
    )
    azure_openai_deployment: str = Field(
        "text-embedding-3-large",
        env="AZURE_OPENAI_DEPLOYMENT",
        description="Azure OpenAI deployment name for embeddings"
    )
    azure_openai_api_version: str = Field(
        "2024-10-21",
        env="AZURE_OPENAI_API_VERSION",
        description="Azure OpenAI API version"
    )
    
    # Fallback OpenAI settings
    openai_api_key: Optional[SecretStr] = Field(
        None,
        env="OPENAI_API_KEY",
        description="OpenAI API key (fallback if Azure OpenAI not configured)"
    )
    
    # ============================================================
    # MCP Server Configuration
    # ============================================================
    mcp_admin_mode: bool = Field(
        False,
        env="MCP_ADMIN_MODE",
        description="Enable admin mode for destructive operations"
    )
    mcp_log_level: LogLevel = Field(
        LogLevel.INFO,
        env="MCP_LOG_LEVEL",
        description="Logging level for MCP server"
    )
    mcp_host: str = Field(
        "0.0.0.0",
        env="MCP_HOST",
        description="Host to bind MCP server to"
    )
    mcp_port: int = Field(
        8001,
        env="MCP_PORT",
        description="Port for MCP server"
    )
    mcp_base_url: str = Field(
        "http://localhost:8001",
        env="MCP_BASE_URL",
        description="Base URL for MCP server"
    )
    mcp_allowed_origins: str = Field(
        "*",
        env="MCP_ALLOWED_ORIGINS",
        description="CORS allowed origins"
    )
    mcp_dev_mode: bool = Field(
        False,
        env="MCP_DEV_MODE",
        description="Enable development mode (bypass auth)"
    )
    
    # ============================================================
    # Cache Configuration
    # ============================================================
    cache_ttl_seconds: int = Field(
        60,
        env="MCP_CACHE_TTL_SECONDS",
        description="Cache TTL in seconds"
    )
    cache_max_entries: int = Field(
        500,
        env="MCP_CACHE_MAX_ENTRIES",
        description="Maximum number of cache entries"
    )
    cache_enabled: bool = Field(
        True,
        env="MCP_CACHE_ENABLED",
        description="Enable caching"
    )
    
    # ============================================================
    # Feedback & Monitoring
    # ============================================================
    feedback_dir: Path = Field(
        Path(".mcp_feedback"),
        env="MCP_FEEDBACK_DIR",
        description="Directory for feedback storage"
    )
    debug_timings: bool = Field(
        False,
        env="MCP_DEBUG_TIMINGS",
        description="Enable timing debug logs"
    )
    
    # ============================================================
    # Authentication Configuration (Optional)
    # ============================================================
    stytch_project_id: Optional[str] = Field(
        None,
        env="STYTCH_PROJECT_ID",
        description="Stytch project ID for auth"
    )
    stytch_secret: Optional[SecretStr] = Field(
        None,
        env="STYTCH_SECRET",
        description="Stytch secret key"
    )
    stytch_env: str = Field(
        "test",
        env="STYTCH_ENV",
        description="Stytch environment"
    )
    session_duration_minutes: int = Field(
        480,
        env="SESSION_DURATION_MINUTES",
        description="Session duration in minutes"
    )
    
    # Redis for session storage
    redis_url: Optional[str] = Field(
        None,
        env="REDIS_URL",
        description="Redis URL for session storage"
    )
    
    # User tier configuration
    admin_emails: List[str] = Field(
        default_factory=list,
        env="MCP_ADMIN_EMAILS",
        description="Comma-separated list of admin emails"
    )
    developer_domains: List[str] = Field(
        default_factory=list,
        env="MCP_DEVELOPER_DOMAINS",
        description="Comma-separated list of developer domains"
    )
    require_mfa_for_admin: bool = Field(
        True,
        env="MCP_REQUIRE_MFA",
        description="Require MFA for admin access"
    )
    
    # ============================================================
    # RAG Pipeline Configuration
    # ============================================================
    # Embedding settings
    embedding_provider: str = Field(
        "azure_openai_http",
        env="EMBEDDING_PROVIDER",
        description="Embedding provider (azure_openai_http, client, none)"
    )
    embedding_model: str = Field(
        "text-embedding-3-small",
        env="EMBEDDING_MODEL",
        description="Embedding model name"
    )
    embedding_dimensions: int = Field(
        1536,
        env="EMBEDDING_DIMENSIONS",
        description="Embedding vector dimensions"
    )
    embedding_batch_size: int = Field(
        16,
        env="EMBEDDING_BATCH_SIZE",
        description="Batch size for embedding generation"
    )
    
    # Search settings
    search_top_k: int = Field(
        50,
        env="SEARCH_TOP_K",
        description="Number of results for semantic ranker"
    )
    search_timeout_seconds: int = Field(
        30,
        env="SEARCH_TIMEOUT_SECONDS",
        description="Search timeout in seconds"
    )
    enable_semantic_search: bool = Field(
        True,
        env="ENABLE_SEMANTIC_SEARCH",
        description="Enable semantic search"
    )
    enable_vector_search: bool = Field(
        True,
        env="ENABLE_VECTOR_SEARCH",
        description="Enable vector search"
    )
    enable_keyword_search: bool = Field(
        True,
        env="ENABLE_KEYWORD_SEARCH",
        description="Enable keyword search"
    )
    
    # Context extraction
    max_context_depth: int = Field(
        3,
        env="MAX_CONTEXT_DEPTH",
        description="Maximum context extraction depth"
    )
    include_git_history: bool = Field(
        True,
        env="INCLUDE_GIT_HISTORY",
        description="Include git history in context"
    )
    git_history_days: int = Field(
        7,
        env="GIT_HISTORY_DAYS",
        description="Days of git history to include"
    )
    
    # File processing
    max_file_size_mb: int = Field(
        10,
        env="MAX_FILE_SIZE_MB",
        description="Maximum file size in MB to process"
    )
    max_index_files: int = Field(
        10000,
        env="MCP_MAX_INDEX_FILES",
        description="Maximum number of files to index"
    )
    
    # ============================================================
    # Index Configuration
    # ============================================================
    index_replica_count: int = Field(
        1,
        env="INDEX_REPLICA_COUNT",
        description="Number of index replicas"
    )
    index_partition_count: int = Field(
        1,
        env="INDEX_PARTITION_COUNT",
        description="Number of index partitions"
    )
    
    class Config:
        """Pydantic configuration"""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
        @classmethod
        def customise_sources(
            cls,
            init_settings,
            env_settings,
            file_secret_settings,
        ):
            """
            Define the priority of settings sources.
            Priority (highest to lowest):
            1. Environment variables
            2. .env file
            3. Default values
            """
            return (
                env_settings,
                file_secret_settings,
                init_settings,
            )
    
    @field_validator("admin_emails", "developer_domains", mode='before')
    @classmethod
    def split_comma_separated(cls, v):
        """Convert comma-separated strings to lists"""
        if isinstance(v, str):
            return [x.strip() for x in v.split(",") if x.strip()]
        return v or []
    
    @property
    def resolved_azure_search_service_name(self) -> Optional[str]:
        """Get the Azure Search service name, inferring from endpoint if needed."""
        if self.azure_search_service_name:
            return self.azure_search_service_name
        if self.acs_endpoint and ".search.windows.net" in self.acs_endpoint:
            # Extract service name from https://xxx.search.windows.net
            return self.acs_endpoint.split("//")[1].split(".")[0]
        return None
    
    @field_validator("azure_openai_key", mode='before')
    @classmethod
    def resolve_openai_key(cls, v):
        """Try multiple environment variable names for Azure OpenAI key"""
        if v:
            return v
        # Try alternative env var names
        for env_var in ["AZURE_OPENAI_API_KEY", "OPENAI_API_KEY"]:
            key = os.getenv(env_var)
            if key:
                return SecretStr(key)
        return None
    
    def validate_config(self) -> Dict[str, str]:
        """
        Validate configuration and return any errors.
        
        Returns:
            Dictionary of field names to error messages
        """
        errors = {}
        
        # Required fields
        if not self.acs_endpoint:
            errors["acs_endpoint"] = "ACS_ENDPOINT is required"
        
        if not self.acs_admin_key and not self.acs_query_key:
            errors["api_key"] = "Either ACS_ADMIN_KEY or ACS_QUERY_KEY is required"
        
        # Validate embeddings config if enabled
        if self.enable_vector_search:
            if self.embedding_provider == "azure_openai_http":
                if not self.azure_openai_endpoint:
                    errors["azure_openai_endpoint"] = (
                        "AZURE_OPENAI_ENDPOINT required for vector search"
                    )
                if not self.azure_openai_key and not self.openai_api_key:
                    errors["azure_openai_key"] = (
                        "AZURE_OPENAI_KEY or OPENAI_API_KEY required for vector search"
                    )
        
        return errors
    
    def to_legacy_azure_config(self) -> Dict[str, Any]:
        """
        Convert to legacy AzureSearchConfig format for backward compatibility.
        
        Returns:
            Dictionary compatible with old AzureSearchConfig
        """
        return {
            "endpoint": self.acs_endpoint,
            "api_key": self.acs_admin_key.get_secret_value() if self.acs_admin_key else "",
            "api_version": self.acs_api_version,
            "timeout": float(self.acs_timeout),
            "index_name": self.acs_index_name,
        }
    
    def to_legacy_mcp_config(self) -> Dict[str, Any]:
        """
        Convert to legacy MCP Config format for backward compatibility.
        
        Returns:
            Dictionary compatible with old Config class attributes
        """
        return {
            "ENDPOINT": self.acs_endpoint,
            "ADMIN_KEY": self.acs_admin_key.get_secret_value() if self.acs_admin_key else "",
            "QUERY_KEY": self.acs_query_key.get_secret_value() if self.acs_query_key else "",
            "INDEX_NAME": self.acs_index_name,
            "AZURE_OPENAI_KEY": self.azure_openai_key.get_secret_value() if self.azure_openai_key else None,
            "AZURE_OPENAI_ENDPOINT": self.azure_openai_endpoint,
            "AZURE_OPENAI_DEPLOYMENT": self.azure_openai_deployment,
            "OPENAI_API_KEY": self.openai_api_key.get_secret_value() if self.openai_api_key else None,
            "CACHE_TTL_SECONDS": self.cache_ttl_seconds,
            "CACHE_MAX_ENTRIES": self.cache_max_entries,
            "ADMIN_MODE": self.mcp_admin_mode,
            "FEEDBACK_DIR": self.feedback_dir,
            "DEBUG_TIMINGS": self.debug_timings,
            "LOG_LEVEL": self.mcp_log_level.value,
            "HOST": self.mcp_host,
            "PORT": self.mcp_port,
            "BASE_URL": self.mcp_base_url,
            "ALLOWED_ORIGINS": self.mcp_allowed_origins,
            "STYTCH_PROJECT_ID": self.stytch_project_id or "",
            "STYTCH_SECRET": self.stytch_secret.get_secret_value() if self.stytch_secret else "",
            "STYTCH_ENV": self.stytch_env,
            "SESSION_DURATION_MINUTES": self.session_duration_minutes,
            "REDIS_URL": self.redis_url or "redis://localhost:6379",
            "ADMIN_EMAILS": ",".join(self.admin_emails),
            "DEVELOPER_DOMAINS": ",".join(self.developer_domains),
            "REQUIRE_MFA_FOR_ADMIN": self.require_mfa_for_admin,
            "DEV_MODE": self.mcp_dev_mode,
        }
    
    @classmethod
    def get_instance(cls) -> "UnifiedConfig":
        """
        Get or create singleton instance.
        
        Returns:
            UnifiedConfig instance
        """
        if not hasattr(cls, "_instance"):
            cls._instance = cls()
        return cls._instance


# Convenience function for getting config
def get_config() -> UnifiedConfig:
    """Get the unified configuration instance."""
    return UnifiedConfig.get_instance()