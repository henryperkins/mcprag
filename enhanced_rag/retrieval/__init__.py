"""
Enhanced RAG Retrieval Module

Multi-stage retrieval pipeline for code search with:
- Hybrid search (vector + keyword)
- Dependency resolution
- Pattern matching
- Result fusion
"""

from .multi_stage_pipeline import MultiStageRetriever, SearchStage
from .hybrid_searcher import HybridSearcher, HybridSearchResult
from .dependency_resolver import DependencyResolver, Dependency
# DEPRECATED: Use pattern_registry instead
# from .pattern_matcher import PatternMatcher, Pattern, PatternType
from ..pattern_registry import get_pattern_registry, PatternType, PatternMatch

__all__ = [
    'MultiStageRetriever',
    'SearchStage',
    'HybridSearcher',
    'HybridSearchResult',
    'DependencyResolver',
    'Dependency',
    'get_pattern_registry',
    'PatternMatch',
    'PatternType'
]