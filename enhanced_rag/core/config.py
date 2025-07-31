"""
Configuration management for Enhanced RAG system
Centralizes all configuration with environment variable support
"""

import os
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from pathlib import Path
import json


class AzureConfig(BaseModel):
    """Azure AI Search configuration"""
    endpoint: str = Field(default_factory=lambda: os.getenv("ACS_ENDPOINT", ""))
    admin_key: str = Field(default_factory=lambda: os.getenv("ACS_ADMIN_KEY", ""))
    index_name: str = Field(default="enhanced-rag-index")
    semantic_config_name: str = Field(default="enhanced-semantic-config")
    
    # Index settings
    replica_count: int = Field(default=1)
    partition_count: int = Field(default=1)
    
    # Search settings
    top_k: int = Field(default=50)  # For semantic ranker
    search_timeout_seconds: int = Field(default=30)


class EmbeddingConfig(BaseModel):
    """Embedding generation configuration"""
    provider: str = Field(default="azure_openai")
    model: str = Field(default="text-embedding-3-large")
    dimensions: int = Field(default=1536)
    batch_size: int = Field(default=16)
    
    # Azure OpenAI settings
    azure_endpoint: str = Field(default_factory=lambda: os.getenv("AZURE_OPENAI_ENDPOINT", ""))
    api_key: str = Field(default_factory=lambda: os.getenv("AZURE_OPENAI_KEY", ""))
    api_version: str = Field(default="2024-02-15-preview")


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
    debug: bool = Field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")
    log_level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    
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