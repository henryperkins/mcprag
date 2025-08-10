"""
Configuration management for Enhanced RAG system
Centralizes all configuration with environment variable support
"""

import logging
import os
from typing import Optional, List
from pydantic import BaseModel, Field
from pathlib import Path
import json

logger = logging.getLogger(__name__)

# Field name constants
CONTENT_VECTOR_FIELD = "content_vector"
CONTENT_FIELD = "content"
FILE_PATH_FIELD = "file_path"
FUNCTION_NAME_FIELD = "function_name"
REPOSITORY_FIELD = "repository"


class AzureConfig(BaseModel):
    """Azure AI Search configuration"""
    endpoint: str = Field(
        default_factory=lambda: os.getenv("ACS_ENDPOINT", "")
    )
    admin_key: str = Field(
        default_factory=lambda: os.getenv("ACS_ADMIN_KEY", "")
    )
    index_name: str = Field(
        default_factory=lambda: os.getenv("ACS_INDEX_NAME", "codebase-mcp-sota")
    )
    semantic_config_name: str = Field(default="enhanced-semantic-config")
    embedding_dimensions: int = Field(default=1536)
    api_version: str = Field(default="2024-07-01")

    # Index settings
    replica_count: int = Field(default=1)
    partition_count: int = Field(default=1)

    # Search settings
    top_k: int = Field(default=50)  # For semantic ranker
    search_timeout_seconds: int = Field(default=30)


class EmbeddingConfig(BaseModel):
    """Embedding generation configuration"""
    provider: str = Field(default="azure_openai_http")  # Options: azure_openai_http, client, none
    # Align model and dimensions with Azure vector field defaults (1536)
    model: str = Field(default="text-embedding-3-small")
    dimensions: int = Field(default=1536)
    batch_size: int = Field(default=16)
    max_concurrent_requests: int = Field(default=5)
    circuit_breaker_threshold: int = Field(default=5)
    circuit_breaker_reset_seconds: int = Field(default=30)

    # Azure OpenAI settings
    azure_endpoint: str = Field(
        default_factory=lambda: os.getenv("AZURE_OPENAI_ENDPOINT", "")
    )
    api_key: str = Field(
        default_factory=lambda: os.getenv("AZURE_OPENAI_KEY",
                                         os.getenv("AZURE_OPENAI_API_KEY",
                                                  os.getenv("OPENAI_API_KEY", "")))
    )
    api_version: str = Field(
        default_factory=lambda: os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
    )


class ContextConfig(BaseModel):
    """Context extraction configuration"""
    max_context_depth: int = Field(default=3)
    include_git_history: bool = Field(default=True)
    git_history_days: int = Field(default=7)

    # Context weights
    file_weight: float = Field(default=1.0)
    module_weight: float = Field(default=0.7)
    project_weight: float = Field(default=0.5)
    cross_project_weight: float = Field(default=0.3)

    # Performance settings
    cache_enabled: bool = Field(default=True)
    cache_ttl_seconds: int = Field(default=300)


class RetrievalConfig(BaseModel):
    """Multi-stage retrieval configuration"""
    enable_semantic_search: bool = Field(default=True)
    enable_vector_search: bool = Field(default=True)
    enable_keyword_search: bool = Field(default=True)
    enable_hybrid_search: bool = Field(default=True)

    # Stage weights
    semantic_weight: float = Field(default=0.7)
    vector_weight: float = Field(default=0.8)
    keyword_weight: float = Field(default=0.5)

    # Retrieval settings
    max_results_per_stage: int = Field(default=100)
    min_relevance_score: float = Field(default=0.5)
    include_dependencies: bool = Field(default=True)
    dependency_depth: int = Field(default=2)


class RankingConfig(BaseModel):
    """Result ranking configuration"""
    # Scoring factors
    enable_context_boost: bool = Field(default=True)
    context_boost_factor: float = Field(default=2.0)

    enable_recency_boost: bool = Field(default=True)
    recency_boost_days: int = Field(default=30)
    recency_boost_factor: float = Field(default=1.5)

    enable_quality_boost: bool = Field(default=True)
    quality_metrics: List[str] = Field(default_factory=lambda: [
        "test_coverage", "documentation_score", "complexity_score"
    ])

    # Result filtering
    max_results: int = Field(default=20)
    diversity_threshold: float = Field(default=0.3)
    explanation_enabled: bool = Field(default=True)


class LearningConfig(BaseModel):
    """Learning system configuration"""
    enabled: bool = Field(default=True)

    # Feedback collection
    min_interactions_for_learning: int = Field(default=10)
    success_weight: float = Field(default=1.0)
    failure_weight: float = Field(default=0.3)

    # Model updates
    update_frequency_hours: int = Field(default=24)
    min_confidence_for_update: float = Field(default=0.7)

    # Storage
    feedback_storage_days: int = Field(default=90)
    anonymize_data: bool = Field(default=True)


class PerformanceConfig(BaseModel):
    """Performance and monitoring configuration"""
    # Timeouts
    context_timeout_ms: int = Field(default=200)
    search_timeout_ms: int = Field(default=500)
    ranking_timeout_ms: int = Field(default=100)

    # Caching
    enable_result_cache: bool = Field(default=True)
    cache_size_mb: int = Field(default=100)

    # Monitoring
    enable_metrics: bool = Field(default=True)
    metrics_sample_rate: float = Field(default=0.1)
    log_slow_queries: bool = Field(default=True)
    slow_query_threshold_ms: int = Field(default=1000)


class Config(BaseModel):
    """Main configuration container"""
    azure: AzureConfig = Field(default_factory=AzureConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    context: ContextConfig = Field(default_factory=ContextConfig)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    ranking: RankingConfig = Field(default_factory=RankingConfig)
    learning: LearningConfig = Field(default_factory=LearningConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)

    # Global settings
    debug: bool = Field(
        default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true"
    )
    log_level: str = Field(
        default_factory=lambda: os.getenv("LOG_LEVEL", "INFO")
    )

    @classmethod
    def from_file(cls, path: str) -> "Config":
        """Load configuration from JSON file"""
        with open(path, 'r') as f:
            data = json.load(f)
        return cls(**data)

    def save_to_file(self, path: str) -> None:
        """Save configuration to JSON file"""
        with open(path, 'w') as f:
            json.dump(self.model_dump(), f, indent=2)

    @classmethod
    def from_env(cls) -> "Config":
        """Create configuration from environment variables"""
        config_file = os.getenv("ENHANCED_RAG_CONFIG")
        if config_file and Path(config_file).exists():
            return cls.from_file(config_file)
        return cls()


# Global configuration instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get or create global configuration instance"""
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config


def set_config(config: Config) -> None:
    """Set global configuration instance"""
    global _config
    _config = config


def validate_config(cfg: Config) -> None:
    """
    Validate required configuration values and raise ValueError on problems.
    """
    # Azure Search required
    if not cfg.azure.endpoint or not cfg.azure.admin_key:
        raise ValueError(
            "ACS_ENDPOINT and ACS_ADMIN_KEY must be set and non-empty"
        )

    # Embedding configuration when using Azure OpenAI or client providers
    if cfg.embedding.provider.lower() in ["azure_openai", "azure_openai_http", "client"]:
        if cfg.embedding.provider.lower() == "client":
            # Client provider needs api_key but may use either Azure or OpenAI endpoint
            if not cfg.embedding.api_key:
                raise ValueError(
                    "API key must be set for client embedding provider"
                )
        else:
            # Azure OpenAI HTTP provider needs endpoint and key
            if not cfg.embedding.azure_endpoint or not cfg.embedding.api_key:
                raise ValueError(
                    "AZURE_OPENAI_ENDPOINT and API key must be set "
                    "for Azure OpenAI provider"
                )
        if cfg.embedding.dimensions <= 0:
            raise ValueError("Embedding dimensions must be positive")
        if cfg.embedding.max_concurrent_requests <= 0:
            raise ValueError("max_concurrent_requests must be positive")

    # Hard check: embedding dims must match Azure vector field dims
    if cfg.embedding.dimensions != cfg.azure.embedding_dimensions:
        raise ValueError(
            f"Embedding dimension mismatch: embedding.dimensions={cfg.embedding.dimensions} "
            f"!= azure.embedding_dimensions={cfg.azure.embedding_dimensions}. "
            "Align these values (e.g., 1536 for text-embedding-3-small)."
        )

    # Soft warning: hybrid enabled but a component is off
    if cfg.retrieval.enable_hybrid_search and (
        not cfg.retrieval.enable_vector_search or not cfg.retrieval.enable_keyword_search
    ):
        logger.warning(
            "Hybrid search is enabled but vector or keyword search is disabled. "
            "Enable both for proper hybrid behavior."
        )


def analyze_search_technology_issues(cfg: Optional[Config] = None) -> dict:
    """
    Analyze configuration for concrete search-technology issues.

    Returns:
        dict with keys: ok (bool), issues (list[str]), warnings (list[str])
    """
    if cfg is None:
        cfg = get_config()

    issues = []
    warnings = []

    # Required Azure Search settings
    if not cfg.azure.endpoint:
        issues.append("Azure Search endpoint (ACS_ENDPOINT) is missing or empty")
    if not cfg.azure.admin_key:
        issues.append("Azure Search admin key (ACS_ADMIN_KEY) is missing or empty")

    # Embedding provider requirements
    provider = cfg.embedding.provider.lower()
    if provider in ["azure_openai", "azure_openai_http", "client"]:
        if provider == "client":
            if not cfg.embedding.api_key:
                issues.append("Client embedding provider requires API key")
        else:
            if not cfg.embedding.azure_endpoint:
                issues.append("AZURE_OPENAI_ENDPOINT is missing for Azure OpenAI embedding provider")
            if not cfg.embedding.api_key:
                issues.append("AZURE_OPENAI_KEY/AZURE_OPENAI_API_KEY/OPENAI_API_KEY is missing for embedding provider")

    # Dimension alignment
    if cfg.embedding.dimensions != cfg.azure.embedding_dimensions:
        issues.append(
            f"Embedding dimension mismatch: embedding.dimensions={cfg.embedding.dimensions} "
            f"vs azure.embedding_dimensions={cfg.azure.embedding_dimensions}"
        )

    # Hybrid configuration sanity
    if cfg.retrieval.enable_hybrid_search and (
        not cfg.retrieval.enable_vector_search or not cfg.retrieval.enable_keyword_search
    ):
        warnings.append(
            "Hybrid search enabled but either vector or keyword search disabled; enable both"
        )

    return {
        "ok": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
    }
