"""Consolidated configuration for Azure AI Search automation.

This module provides a unified configuration system that consolidates the
previously separate AzureSearchConfig, IndexConfig, and AutomationConfig
classes into a cohesive configuration hierarchy.

Usage:
    # Unified approach (recommended)
    config = UnifiedConfig.from_env()
    client = ClientFactory.create_client(config.azure_search)
    
    # Legacy approach (deprecated but supported)
    search_config = AzureSearchConfig.from_env()
"""

import os
import warnings
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List


@dataclass
class AzureSearchConfig:
    """Simple configuration for Azure Search."""
    endpoint: str
    api_key: str
    api_version: str = "2025-05-01-preview"
    timeout: float = 30.0
    
    @classmethod
    def from_env(cls) -> "AzureSearchConfig":
        """Load configuration from environment variables.
        
        Environment variables:
            ACS_ENDPOINT: Azure Search endpoint URL
            ACS_ADMIN_KEY: Admin API key
            ACS_API_VERSION: API version (optional)
            ACS_TIMEOUT: Request timeout in seconds (optional)
            
        Returns:
            AzureSearchConfig instance
            
        Raises:
            ValueError: If required environment variables are missing
        """
        endpoint = os.environ.get("ACS_ENDPOINT")
        api_key = os.environ.get("ACS_ADMIN_KEY")
        
        if not endpoint:
            raise ValueError("ACS_ENDPOINT environment variable is required")
        if not api_key:
            raise ValueError("ACS_ADMIN_KEY environment variable is required")
        
        return cls(
            endpoint=endpoint,
            api_key=api_key,
            api_version=os.environ.get("ACS_API_VERSION", "2025-05-01-preview"),
            timeout=float(os.environ.get("ACS_TIMEOUT", "30.0"))
        )
    
    @classmethod
    def from_dict(cls, config_dict: dict) -> "AzureSearchConfig":
        """Create configuration from dictionary.
        
        Args:
            config_dict: Configuration dictionary
            
        Returns:
            AzureSearchConfig instance
        """
        return cls(
            endpoint=config_dict["endpoint"],
            api_key=config_dict["api_key"],
            api_version=config_dict.get("api_version", "2025-05-01-preview"),
            timeout=config_dict.get("timeout", 30.0)
        )
    
    def to_dict(self) -> dict:
        """Convert configuration to dictionary.
        
        Returns:
            Configuration as dictionary
        """
        return {
            "endpoint": self.endpoint,
            "api_key": self.api_key,
            "api_version": self.api_version,
            "timeout": self.timeout
        }


@dataclass
class IndexConfig:
    """Configuration for a search index."""
    name: str
    fields: list
    vector_search: Optional[dict] = None
    semantic_search: Optional[dict] = None
    scoring_profiles: Optional[list] = None
    cors_options: Optional[dict] = None
    
    def to_index_definition(self) -> dict:
        """Convert to Azure Search index definition.
        
        Returns:
            Index definition dictionary
        """
        definition = {
            "name": self.name,
            "fields": self.fields
        }
        
        if self.vector_search:
            definition["vectorSearch"] = self.vector_search
        if self.semantic_search:
            definition["semanticSearch"] = self.semantic_search
        if self.scoring_profiles:
            definition["scoringProfiles"] = self.scoring_profiles
        if self.cors_options:
            definition["corsOptions"] = self.cors_options
            
        return definition


@dataclass
class AutomationConfig:
    """Configuration for automation tasks."""
    batch_size: int = 1000
    retry_attempts: int = 3
    retry_delay_seconds: float = 1.0
    rate_limit_delay_seconds: float = 0.5
    log_level: str = "INFO"
    
    @classmethod
    def from_env(cls) -> "AutomationConfig":
        """Load automation config from environment variables.
        
        Returns:
            AutomationConfig instance
        """
        return cls(
            batch_size=int(os.environ.get("ACS_BATCH_SIZE", "1000")),
            retry_attempts=int(os.environ.get("ACS_RETRY_ATTEMPTS", "3")),
            retry_delay_seconds=float(os.environ.get("ACS_RETRY_DELAY", "1.0")),
            rate_limit_delay_seconds=float(os.environ.get("ACS_RATE_LIMIT_DELAY", "0.5")),
            log_level=os.environ.get("ACS_LOG_LEVEL", "INFO")
        )


@dataclass
class UnifiedConfig:
    """Unified configuration consolidating all Azure Search settings."""
    
    azure_search: AzureSearchConfig
    automation: AutomationConfig = field(default_factory=AutomationConfig)
    index_defaults: Optional[Dict[str, Any]] = None
    
    @classmethod
    def from_env(cls) -> "UnifiedConfig":
        """Load unified configuration from environment variables."""
        return cls(
            azure_search=AzureSearchConfig.from_env(),
            automation=AutomationConfig.from_env(),
            index_defaults={}
        )
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "UnifiedConfig":
        """Create unified configuration from dictionary."""
        return cls(
            azure_search=AzureSearchConfig.from_dict(config_dict.get("azure_search", {})),
            automation=AutomationConfig(**config_dict.get("automation", {})),
            index_defaults=config_dict.get("index_defaults")
        )


class ClientFactory:
    """Factory for creating Azure Search clients and operations."""
    
    @classmethod
    def create_client(cls, config: AzureSearchConfig):
        """Create AzureSearchClient from configuration."""
        from .rest import AzureSearchClient
        return AzureSearchClient(
            endpoint=config.endpoint,
            api_key=config.api_key,
            api_version=config.api_version,
            timeout=config.timeout
        )
    
    @classmethod
    def create_operations(cls, config: AzureSearchConfig):
        """Create SearchOperations from configuration."""
        from .rest import SearchOperations
        client = cls.create_client(config)
        return SearchOperations(client)
    
    @classmethod
    def create_unified_automation(cls, config: UnifiedConfig):
        """Create UnifiedAutomation from unified configuration."""
        from .automation import UnifiedAutomation
        return UnifiedAutomation(
            endpoint=config.azure_search.endpoint,
            api_key=config.azure_search.api_key,
            api_version=config.azure_search.api_version
        )


# Global default configuration for convenience
_default_config: Optional[UnifiedConfig] = None

def get_default_config() -> UnifiedConfig:
    """Get or create default configuration from environment."""
    global _default_config
    if _default_config is None:
        _default_config = UnifiedConfig.from_env()
    return _default_config

def set_default_config(config: UnifiedConfig):
    """Set the default configuration."""
    global _default_config
    _default_config = config