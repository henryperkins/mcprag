"""
Azure AI Search Integration Module
Provides comprehensive integration with Azure Search features
"""

from .indexer_integration import IndexerIntegration, DataSourceType, LocalRepositoryIndexer
from .enhanced_index_builder import EnhancedIndexBuilder
from .custom_skill_vectorizer import (
    CodeAnalyzerSkill,
    EmbeddingGeneratorSkill,
    CustomWebApiVectorizer,
    GitMetadataExtractorSkill,
    ContextAwareChunkingSkill,
    create_code_analysis_endpoint
)
from .embedding_provider import IEmbeddingProvider, AzureOpenAIEmbeddingProvider
from .standard_skills import (
    TextSplitSkill,
    AzureOpenAIEmbeddingSkill,
    StandardSkillsetBuilder,
    create_standard_skillset
)
from .reindex_operations import ReindexOperations, ReindexMethod
from .index_management import IndexManagement, IndexStats, DocumentStats

__all__ = [
    # Indexer components
    'IndexerIntegration',
    'DataSourceType',
    'LocalRepositoryIndexer',
    
    # Index builder
    'EnhancedIndexBuilder',
    
    # Custom skills
    'CodeAnalyzerSkill',
    'EmbeddingGeneratorSkill',
    'CustomWebApiVectorizer',
    'GitMetadataExtractorSkill',
    'ContextAwareChunkingSkill',
    'create_code_analysis_endpoint',
    
    # Embedding providers
    'IEmbeddingProvider',
    'AzureOpenAIEmbeddingProvider',
    
    # Standard skills
    'TextSplitSkill',
    'AzureOpenAIEmbeddingSkill',
    'StandardSkillsetBuilder',
    'create_standard_skillset',
    
    # Reindexing operations
    'ReindexOperations',
    'ReindexMethod',
    
    # Index management
    'IndexManagement',
    'IndexStats',
    'DocumentStats'
]