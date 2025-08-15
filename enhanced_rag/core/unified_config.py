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
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# Known embedding dimensions for common models
_EMBED_DIMENSIONS = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
}


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
        default="",
        alias="ACS_ENDPOINT",
        description="Azure Cognitive Search endpoint URL"
    )
    acs_admin_key: Optional[SecretStr] = Field(
        default=None,
        alias="ACS_ADMIN_KEY",
        description="Azure Search admin key (write access)"
    )
    acs_query_key: Optional[SecretStr] = Field(
        default=None,
        alias="ACS_QUERY_KEY",
        description="Azure Search query key (read-only access)"
    )
    acs_index_name: str = Field(
        default="codebase-mcp-sota",
        alias="ACS_INDEX_NAME",
        description="Name of the Azure Search index"
    )
    acs_api_version: str = Field(
        default="2025-08-01-preview",
        alias="ACS_API_VERSION",
        description="Azure Search API version"
    )
    acs_semantic_config: str = Field(
        default="enhanced-semantic-config",
        alias="ACS_SEMANTIC_CONFIG",
        description="Semantic search configuration name"
    )
    acs_timeout: int = Field(
        default=30,
        alias="ACS_TIMEOUT",
        description="Request timeout in seconds"
    )

    # Azure resource settings
    azure_resource_group: Optional[str] = Field(
        default=None,
        alias="AZURE_RESOURCE_GROUP",
        description="Azure resource group name"
    )
    azure_search_service_name: Optional[str] = Field(
        default=None,
        alias="AZURE_SEARCH_SERVICE_NAME",
        description="Azure Search service name (inferred from endpoint if not set)"
    )

    # ============================================================
    # Azure OpenAI Configuration (Optional - for embeddings)
    # ============================================================
    azure_openai_endpoint: Optional[str] = Field(
        default=None,
        alias="AZURE_OPENAI_ENDPOINT",
        description="Azure OpenAI endpoint URL"
    )
    azure_openai_key: Optional[SecretStr] = Field(
        default=None,
        alias="AZURE_OPENAI_KEY",
        description="Azure OpenAI API key"
    )
    azure_openai_deployment: str = Field(
        default="text-embedding-3-small",  # align default with 1536 dims
        alias="AZURE_OPENAI_DEPLOYMENT",
        description="Azure OpenAI deployment name for embeddings"
    )
    azure_openai_api_version: str = Field(
        default="2024-10-21",
        alias="AZURE_OPENAI_API_VERSION",
        description="Azure OpenAI API version"
    )

    # Fallback OpenAI settings
    openai_api_key: Optional[SecretStr] = Field(
        default=None,
        alias="OPENAI_API_KEY",
        description="OpenAI API key (fallback if Azure OpenAI not configured)"
    )

    # ============================================================
    # MCP Server Configuration
    # ============================================================
    mcp_admin_mode: bool = Field(
        default=False,
        alias="MCP_ADMIN_MODE",
        description="Enable admin mode for destructive operations"
    )
    mcp_log_level: LogLevel = Field(
        default=LogLevel.INFO,
        alias="MCP_LOG_LEVEL",
        description="Logging level for MCP server"
    )
    mcp_host: str = Field(
        default="0.0.0.0",
        alias="MCP_HOST",
        description="Host to bind MCP server to"
    )
    mcp_port: int = Field(
        default=8001,
        alias="MCP_PORT",
        description="Port for MCP server"
    )
    mcp_base_url: str = Field(
        default="http://localhost:8001",
        alias="MCP_BASE_URL",
        description="Base URL for MCP server"
    )
    mcp_allowed_origins: str = Field(
        default="*",
        alias="MCP_ALLOWED_ORIGINS",
        description="CORS allowed origins"
    )
    mcp_dev_mode: bool = Field(
        default=False,
        alias="MCP_DEV_MODE",
        description="Enable development mode (bypass auth)"
    )

    # ============================================================
    # Cache Configuration
    # ============================================================
    cache_ttl_seconds: int = Field(
        default=60,
        alias="MCP_CACHE_TTL_SECONDS",
        description="Cache TTL in seconds"
    )
    cache_max_entries: int = Field(
        default=500,
        alias="MCP_CACHE_MAX_ENTRIES",
        description="Maximum number of cache entries"
    )
    cache_enabled: bool = Field(
        default=True,
        alias="MCP_CACHE_ENABLED",
        description="Enable caching"
    )

    # ============================================================
    # Feedback & Monitoring
    # ============================================================
    feedback_dir: Path = Field(
        default=Path(".mcp_feedback"),
        alias="MCP_FEEDBACK_DIR",
        description="Directory for feedback storage"
    )
    debug_timings: bool = Field(
        default=False,
        alias="MCP_DEBUG_TIMINGS",
        description="Enable timing debug logs"
    )

    # ============================================================
    # Authentication Configuration (Optional)
    # ============================================================
    stytch_project_id: Optional[str] = Field(
        default=None,
        alias="STYTCH_PROJECT_ID",
        description="Stytch project ID for auth"
    )
    stytch_secret: Optional[SecretStr] = Field(
        default=None,
        alias="STYTCH_SECRET",
        description="Stytch secret key"
    )
    stytch_env: str = Field(
        default="test",
        alias="STYTCH_ENV",
        description="Stytch environment"
    )
    session_duration_minutes: int = Field(
        default=480,
        alias="SESSION_DURATION_MINUTES",
        description="Session duration in minutes"
    )

    # Redis for session storage
    redis_url: Optional[str] = Field(
        default=None,
        alias="REDIS_URL",
        description="Redis URL for session storage"
    )

    # User tier configuration
    admin_emails: List[str] = Field(
        default_factory=list,
        alias="MCP_ADMIN_EMAILS",
        description="Comma-separated list of admin emails"
    )
    developer_domains: List[str] = Field(
        default_factory=list,
        alias="MCP_DEVELOPER_DOMAINS",
        description="Comma-separated list of developer domains"
    )
    require_mfa_for_admin: bool = Field(
        default=True,
        alias="MCP_REQUIRE_MFA",
        description="Require MFA for admin access"
    )

    # ============================================================
    # RAG Pipeline Configuration
    # ============================================================
    # Embedding settings
    embedding_provider: str = Field(
        default="azure_openai_http",
        alias="EMBEDDING_PROVIDER",
        description="Embedding provider (azure_openai_http, client, none)"
    )
    embedding_model: str = Field(
        default="text-embedding-3-small",
        alias="EMBEDDING_MODEL",
        description="Embedding model name"
    )
    embedding_dimensions: int = Field(
        default=1536,
        alias="EMBEDDING_DIMENSIONS",
        description="Embedding vector dimensions"
    )
    embedding_batch_size: int = Field(
        default=16,
        alias="EMBEDDING_BATCH_SIZE",
        description="Batch size for embedding generation"
    )

    # Search settings
    search_top_k: int = Field(
        default=50,
        alias="SEARCH_TOP_K",
        description="Number of results for semantic ranker"
    )
    search_timeout_seconds: int = Field(
        default=30,
        alias="SEARCH_TIMEOUT_SECONDS",
        description="Search timeout in seconds"
    )
    enable_semantic_search: bool = Field(
        default=True,
        alias="ENABLE_SEMANTIC_SEARCH",
        description="Enable semantic search"
    )
    enable_vector_search: bool = Field(
        default=True,
        alias="ENABLE_VECTOR_SEARCH",
        description="Enable vector search"
    )
    enable_keyword_search: bool = Field(
        default=True,
        alias="ENABLE_KEYWORD_SEARCH",
        description="Enable keyword search"
    )

    # Context extraction
    max_context_depth: int = Field(
        default=3,
        alias="MAX_CONTEXT_DEPTH",
        description="Maximum context extraction depth"
    )
    include_git_history: bool = Field(
        default=True,
        alias="INCLUDE_GIT_HISTORY",
        description="Include git history in context"
    )
    git_history_days: int = Field(
        default=7,
        alias="GIT_HISTORY_DAYS",
        description="Days of git history to include"
    )

    # File processing
    max_file_size_mb: int = Field(
        default=10,
        alias="MAX_FILE_SIZE_MB",
        description="Maximum file size in MB to process"
    )
    max_index_files: int = Field(
        default=10000,
        alias="MAX_INDEX_FILES",
        description="Maximum number of files to index"
    )

    # ============================================================
    # Index Configuration
    # ============================================================
    index_replica_count: int = Field(
        default=1,
        alias="INDEX_REPLICA_COUNT",
        description="Number of index replicas"
    )
    index_partition_count: int = Field(
        default=1,
        alias="INDEX_PARTITION_COUNT",
        description="Number of index partitions"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",  # Allow extra environment variables
        populate_by_name=True,  # Allow both field name and alias
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        """
        Define the priority of settings sources.
        Priority (highest to lowest):
        1. Environment variables
        2. .env file
        3. File secrets
        4. Default values
        """
        return (
            env_settings,
            dotenv_settings,
            file_secret_settings,
            init_settings,
        )

    @field_validator("admin_emails", "developer_domains", mode='before')
    @classmethod
    def split_comma_separated(cls, v):
        """Convert comma-separated strings to lists"""
        if isinstance(v, str):
            return [x.strip() for x in v.split(",") if x.strip()]
        if v is None:
            return []
        return v

    @property
    def resolved_azure_search_service_name(self) -> Optional[str]:
        """Get the Azure Search service name, inferring from endpoint if needed."""
        if self.azure_search_service_name:
            return self.azure_search_service_name
        if self.acs_endpoint and ".search.windows.net" in self.acs_endpoint:
            # Extract service name from https://xxx.search.windows.net
            return self.acs_endpoint.split("//")[1].split(".")[0]  # type: ignore
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

    @field_validator("acs_endpoint", mode="before")
    @classmethod
    def _normalize_endpoint(cls, v):
        # Normalize endpoint: strip spaces, remove trailing slashes
        if isinstance(v, str):
            v = v.strip()
            while v.endswith("/"):
                v = v[:-1]
        return v

    @model_validator(mode="after")
    def _harmonize_embedding_settings(self):
        """
        Ensure embedding_dimensions matches the selected embedding model/deployment
        when using known models. If user explicitly configured a different size,
        keep it; only auto-adjust when defaults are inconsistent.
        """
        # Prefer explicit embedding_model, else fall back to azure_openai_deployment
        chosen_model = (self.embedding_model or self.azure_openai_deployment or "").strip()
        if not chosen_model:
            return self

        expected = None
        # Map by known keys
        for key, dims in _EMBED_DIMENSIONS.items():
            if key in chosen_model:
                expected = dims
                break

        if expected is not None:
            # If deployment suggests large but dimensions still default-small, auto-fix;
            # or if deployment is small and dimensions mismatched, fix too.
            if self.embedding_dimensions != expected:
                # Heuristic: adjust if user didn't override via env (leave custom sizes alone)
                env_var = os.getenv("EMBEDDING_DIMENSIONS")
                if not env_var:
                    self.embedding_dimensions = expected
                    logger.info("Adjusted embedding_dimensions to %s for model '%s'", expected, chosen_model)
                else:
                    logger.warning(
                        "Configured EMBEDDING_DIMENSIONS=%s differs from expected %s for model '%s'; keeping user value",
                        self.embedding_dimensions, expected, chosen_model
                    )
        return self

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
        api_key = ""
        if self.acs_admin_key is not None:
            api_key = self.acs_admin_key.get_secret_value()

        return {
            "endpoint": self.acs_endpoint,
            "api_key": api_key,
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
            "ADMIN_KEY": self.acs_admin_key.get_secret_value() if self.acs_admin_key else "",  # type: ignore
            "QUERY_KEY": self.acs_query_key.get_secret_value() if self.acs_query_key else "",  # type: ignore
            "INDEX_NAME": self.acs_index_name,
            "AZURE_OPENAI_KEY": self.azure_openai_key.get_secret_value() if self.azure_openai_key else None,  # type: ignore
            "AZURE_OPENAI_ENDPOINT": self.azure_openai_endpoint,
            "AZURE_OPENAI_DEPLOYMENT": self.azure_openai_deployment,
            "OPENAI_API_KEY": self.openai_api_key.get_secret_value() if self.openai_api_key else None,  # type: ignore
            "CACHE_TTL_SECONDS": self.cache_ttl_seconds,
            "CACHE_MAX_ENTRIES": self.cache_max_entries,
            "ADMIN_MODE": self.mcp_admin_mode,
            "FEEDBACK_DIR": str(self.feedback_dir),
            "DEBUG_TIMINGS": self.debug_timings,
            "LOG_LEVEL": self.mcp_log_level.value,
            "HOST": self.mcp_host,
            "PORT": self.mcp_port,
            "BASE_URL": self.mcp_base_url,
            "ALLOWED_ORIGINS": self.mcp_allowed_origins,
            "STYTCH_PROJECT_ID": self.stytch_project_id or "",
            "STYTCH_SECRET": self.stytch_secret.get_secret_value() if self.stytch_secret else "",  # type: ignore
            "STYTCH_ENV": self.stytch_env,
            "SESSION_DURATION_MINUTES": self.session_duration_minutes,
            "REDIS_URL": self.redis_url or "redis://localhost:6379",
            "ADMIN_EMAILS": ",".join(self.admin_emails),
            "DEVELOPER_DOMAINS": ",".join(self.developer_domains),
            "REQUIRE_MFA_FOR_ADMIN": self.require_mfa_for_admin,
            "DEV_MODE": self.mcp_dev_mode,
        }

    @property
    def azure(self) -> Dict[str, Any]:
        """Return Azure configuration in legacy format."""
        return {
            "endpoint": self.acs_endpoint,
            "admin_key": self.acs_admin_key.get_secret_value() if self.acs_admin_key else "",
            "index_name": self.acs_index_name,
            "semantic_config_name": self.acs_semantic_config,
            "embedding_dimensions": self.embedding_dimensions,
            "api_version": self.acs_api_version,
            "replica_count": self.index_replica_count,
            "partition_count": self.index_partition_count,
            "top_k": self.search_top_k,
            "search_timeout_seconds": self.search_timeout_seconds,
        }

    @property
    def embedding(self) -> Dict[str, Any]:
        """Return embedding configuration in legacy format."""
        return {
            "provider": self.embedding_provider,
            "model": self.embedding_model,
            "dimensions": self.embedding_dimensions,
            "batch_size": self.embedding_batch_size,
            "max_concurrent_requests": 5,
            "circuit_breaker_threshold": 5,
            "circuit_breaker_reset_seconds": 30,
            "azure_endpoint": self.azure_openai_endpoint or "",
            "api_key": self.azure_openai_key.get_secret_value() if self.azure_openai_key else self.openai_api_key.get_secret_value() if self.openai_api_key else "",
            "api_version": self.azure_openai_api_version,
        }

    @property
    def context(self) -> Dict[str, Any]:
        """Return context configuration in legacy format."""
        return {
            "max_context_depth": self.max_context_depth,
            "include_git_history": self.include_git_history,
            "git_history_days": self.git_history_days,
            "file_weight": 1.0,
            "module_weight": 0.7,
            "project_weight": 0.5,
            "cross_project_weight": 0.3,
            "cache_enabled": self.cache_enabled,
            "cache_ttl_seconds": self.cache_ttl_seconds,
        }

    @property
    def retrieval(self) -> Dict[str, Any]:
        """Return retrieval configuration in legacy format."""
        return {
            "enable_semantic_search": self.enable_semantic_search,
            "enable_vector_search": self.enable_vector_search,
            "enable_keyword_search": self.enable_keyword_search,
            "enable_hybrid_search": self.enable_vector_search and self.enable_keyword_search,
            "semantic_weight": 0.7,
            "vector_weight": 0.8,
            "keyword_weight": 0.5,
            "max_results_per_stage": 100,
            "min_relevance_score": 0.5,
            "include_dependencies": True,
            "dependency_depth": 2,
        }

    @property
    def ranking(self) -> Dict[str, Any]:
        """Return ranking configuration in legacy format."""
        return {
            "enable_context_boost": True,
            "context_boost_factor": 2.0,
            "enable_recency_boost": True,
            "recency_boost_days": 30,
            "recency_boost_factor": 1.5,
            "enable_quality_boost": True,
            "quality_metrics": ["test_coverage", "documentation_score", "complexity_score"],
            "max_results": 20,
            "diversity_threshold": 0.3,
            "explanation_enabled": True,
        }

    @property
    def learning(self) -> Dict[str, Any]:
        """Return learning configuration in legacy format."""
        return {
            "enabled": True,
            "min_interactions_for_learning": 10,
            "success_weight": 1.0,
            "failure_weight": 0.3,
            "update_frequency_hours": 24,
            "min_confidence_for_update": 0.7,
            "feedback_storage_days": 90,
            "anonymize_data": True,
        }

    @property
    def performance(self) -> Dict[str, Any]:
        """Return performance configuration in legacy format."""
        return {
            "context_timeout_ms": 200,
            "search_timeout_ms": 500,
            "ranking_timeout_ms": 100,
            "enable_result_cache": self.cache_enabled,
            "cache_size_mb": 100,
            "enable_metrics": True,
            "metrics_sample_rate": 0.1,
            "log_slow_queries": True,
            "slow_query_threshold_ms": 1000,
        }

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """
        Override model_dump to include nested sections while preserving pydantic v2 signature.
        """
        base_dump = super().model_dump(**kwargs)

        # Add nested configuration sections for RAGPipeline compatibility
        base_dump["azure"] = self.azure
        base_dump["embedding"] = self.embedding
        base_dump["context"] = self.context
        base_dump["retrieval"] = self.retrieval
        base_dump["ranking"] = self.ranking
        base_dump["learning"] = self.learning
        base_dump["performance"] = self.performance

        return base_dump

    def get(self, key: str, default: Any = None) -> Any:
        """
        Dict-like get method for compatibility.
        """
        try:
            return getattr(self, key, default)
        except AttributeError:
            return default

    @classmethod
    def get_instance(cls) -> "UnifiedConfig":
        """
        Get or create singleton instance.

        Returns:
            UnifiedConfig instance
        """
        if not hasattr(cls, "_instance"):
            # Create instance; will load from environment variables and .env file
            try:
                cls._instance = cls()
            except Exception as e:
                # If ACS_ENDPOINT is not set, provide a helpful error
                raise ValueError(
                    "ACS_ENDPOINT environment variable is required. "
                    "Please set it or create a .env file with ACS_ENDPOINT=<your-endpoint>"
                ) from e
        return cls._instance


# Convenience function for getting config
def get_config() -> UnifiedConfig:
    """Get the unified configuration instance."""
    return UnifiedConfig.get_instance()
