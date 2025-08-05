"""
Azure AI Search Integration Module - Consolidated Architecture

This module provides comprehensive integration with Azure Search features
through a consolidated, non-duplicated architecture.

RECOMMENDED USAGE (New Consolidated API):
    from azure_integration import UnifiedConfig, ClientFactory, FileProcessor
    
    # Configuration
    config = UnifiedConfig.from_env()
    
    # Client creation
    automation = ClientFactory.create_unified_automation(config)
    
    # File processing
    processor = FileProcessor()
    documents = processor.process_repository("./repo", "repo-name")

LEGACY USAGE (Deprecated but supported):
    from azure_integration import AzureSearchClient, ReindexOperations
    # ... legacy code continues to work
"""

# NEW CONSOLIDATED API (Recommended)
from .config import UnifiedConfig, ClientFactory, get_default_config
from .processing import FileProcessor

# REST-based components
from .rest_index_builder import EnhancedIndexBuilder
from .rest import AzureSearchClient, SearchOperations

# Core functionality
from .embedding_provider import IEmbeddingProvider, AzureOpenAIEmbeddingProvider, NullEmbeddingProvider
from .reindex_operations import ReindexOperations, ReindexMethod

# Automation components (consolidated)
from .automation import (
    IndexAutomation,
    DataAutomation,
    IndexerAutomation,
    HealthMonitor,
    ReindexAutomation,
    EmbeddingAutomation,
    CLIAutomation,
    UnifiedAutomation
)

# Legacy configuration (deprecated)
from .config import AzureSearchConfig, IndexConfig, AutomationConfig

__all__ = [
    # NEW CONSOLIDATED API (Recommended)
    'UnifiedConfig',
    'ClientFactory', 
    'FileProcessor',
    'get_default_config',
    
    # REST components
    'AzureSearchClient',
    'SearchOperations',
    
    # Index builder
    'EnhancedIndexBuilder',
    
    # Embedding providers
    'IEmbeddingProvider',
    'AzureOpenAIEmbeddingProvider',
    'NullEmbeddingProvider',
    
    # Reindexing operations
    'ReindexOperations',
    'ReindexMethod',
    
    # Automation managers
    'IndexAutomation',
    'DataAutomation',
    'IndexerAutomation',
    'HealthMonitor',
    'ReindexAutomation',
    'EmbeddingAutomation',
    'CLIAutomation',
    'UnifiedAutomation',
    
    # Legacy configuration (deprecated)
    'AzureSearchConfig',
    'IndexConfig', 
    'AutomationConfig',
]