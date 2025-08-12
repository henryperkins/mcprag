"""
Azure AI Search Integration Module - Consolidated Architecture

This module provides comprehensive integration with Azure Search features
through a consolidated, non-duplicated architecture.

RECOMMENDED USAGE (New Consolidated API):
    from azure_integration import UnifiedConfig, FileProcessor
    
    # Configuration
    config = UnifiedConfig()
    
    # File processing
    processor = FileProcessor()
    documents = processor.process_repository("./repo", "repo-name")

"""

# NEW CONSOLIDATED API (Recommended)
from ..core.unified_config import UnifiedConfig
from .processing import FileProcessor

# REST-based components
from .rest import AzureSearchClient, SearchOperations

# Core functionality
from .embedding_provider import IEmbeddingProvider, AzureOpenAIEmbeddingProvider, NullEmbeddingProvider

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


__all__ = [
    # NEW CONSOLIDATED API (Recommended)
    'UnifiedConfig',
    'FileProcessor',
    
    # REST components
    'AzureSearchClient',
    'SearchOperations',
    
    # Embedding providers
    'IEmbeddingProvider',
    'AzureOpenAIEmbeddingProvider',
    'NullEmbeddingProvider',
    
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
