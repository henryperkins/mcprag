"""
Azure AI Search Integration Module
Provides comprehensive integration with Azure Search features
"""

# REST-based components
from .rest_index_builder import EnhancedIndexBuilder
from .rest import AzureSearchClient, SearchOperations

# Core functionality
from .embedding_provider import IEmbeddingProvider, AzureOpenAIEmbeddingProvider, NullEmbeddingProvider
from .reindex_operations import ReindexOperations, ReindexMethod

# Automation components
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

__all__ = [
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
]