"""
Context-aware result ranking with multi-factor scoring
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from ..core.interfaces import Ranker
from ..core.models import SearchResult, EnhancedContext, SearchIntent

logger = logging.getLogger(__name__)


@dataclass
class RankingFactors:
    """Factors used in ranking calculation"""
    text_relevance: float = 0.0
    semantic_similarity: float = 0.0
    context_overlap: float = 0.0
    import_similarity: float = 0.0
    proximity_score: float = 0.0
    recency_score: float = 0.0
    quality_score: float = 0.0


class ContextualRanker(Ranker):
    """
    Multi-factor ranking system that considers context and intent
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.weights = self._get_intent_weights()
        
    def _get_intent_weights(self) -> Dict[SearchIntent, Dict[str, float]]:
        """Get ranking weights for different intents"""
        return {
            SearchIntent.IMPLEMENT: {
                'text_relevance': 0.2,
                'semantic_similarity': 0.3,
                'import_similarity': 0.2,
                'quality_score': 0.3
            },
            SearchIntent.DEBUG: {
                'text_relevance': 0.4,
                'recency_score': 0.3,
                'context_overlap': 0.3
            },
            SearchIntent.UNDERSTAND: {
                'semantic_similarity': 0.4,
                'quality_score': 0.3,
                'proximity_score': 0.3
            },
            SearchIntent.REFACTOR: {
                'text_relevance': 0.2,
                'proximity_score': 0.3,
                'import_similarity': 0.2,
                'quality_score': 0.3
            },
            SearchIntent.TEST: {
                'text_relevance': 0.3,
                'proximity_score': 0.4,
                'quality_score': 0.3
            },
            SearchIntent.DOCUMENT: {
                'semantic_similarity': 0.4,
                'quality_score': 0.4,
                'recency_score': 0.2
            }
        }
    
    async def rank_results(
        self,
        results: List[SearchResult],
        context: EnhancedContext,
        intent: SearchIntent
    ) -> List[SearchResult]:
        """
        Rank results based on multiple factors and context
        """
        ranked_results = []
        
        for result in results:
            # Calculate all ranking factors
            factors = await self._calculate_factors(result, context)
            
            # Apply intent-specific weights
            weights = self.weights.get(intent, self.weights[SearchIntent.IMPLEMENT])
            final_score = self._calculate_weighted_score(factors, weights)
            
            # Update result with new score and explanation
            result.score = final_score
            result.ranking_explanation = self._generate_explanation(factors, weights)
            ranked_results.append(result)
        
        # Sort by final score
        ranked_results.sort(key=lambda x: x.score, reverse=True)
        
        return ranked_results
    
    async def _calculate_factors(
        self,
        result: SearchResult,
        context: EnhancedContext
    ) -> RankingFactors:
        """Calculate all ranking factors for a result"""
        factors = RankingFactors()
        
        # Text relevance (from search engine)
        factors.text_relevance = result.score
        
        # Semantic similarity (if vectors available)
        if hasattr(result, 'vector_score'):
            factors.semantic_similarity = result.vector_score
            
        # Context overlap (imports, dependencies, etc.)
        factors.context_overlap = self._calculate_context_overlap(result, context)
        
        # Import similarity
        factors.import_similarity = self._calculate_import_similarity(result, context)
        
        # Proximity score (same file/module/project)
        factors.proximity_score = self._calculate_proximity(result, context)
        
        # Recency score
        factors.recency_score = self._calculate_recency(result)
        
        # Quality score (from metadata)
        factors.quality_score = getattr(result, 'quality_score', 0.5)
        
        # Pattern matching score
        if not hasattr(self, 'pattern_scorer'):
            from .pattern_matcher_integration import PatternMatchScorer
            self.pattern_scorer = PatternMatchScorer(self.config)
        
        # Extract query from context or use default
        query = getattr(context, 'query', '')
        factors.pattern_match = await self.pattern_scorer.calculate_pattern_score(
            result, query, context
        )
        
        return factors
    
    def _calculate_context_overlap(
        self,
        result: SearchResult,
        context: EnhancedContext
    ) -> float:
        """Calculate overlap between result and current context"""
        overlap_score = 0.0
        
        # Check import overlap
        if context.imports and result.dependencies:
            common_imports = set(context.imports) & set(result.dependencies)
            if context.imports:
                overlap_score += len(common_imports) / len(context.imports) * 0.4
        
        # Check if result is in same module
        if context.current_file and result.file_path:
            if self._same_module(context.current_file, result.file_path):
                overlap_score += 0.3
        
        # Check framework overlap
        if context.framework and hasattr(result, 'framework'):
            if context.framework == getattr(result, 'framework', ''):
                overlap_score += 0.3
        
        return min(overlap_score, 1.0)
    
    def _calculate_import_similarity(
        self,
        result: SearchResult,
        context: EnhancedContext
    ) -> float:
        """Calculate import similarity between result and context"""
        if not context.imports or not result.dependencies:
            return 0.0
        
        context_imports = set(context.imports)
        result_imports = set(result.dependencies)
        
        # Jaccard similarity
        intersection = context_imports & result_imports
        union = context_imports | result_imports
        
        if not union:
            return 0.0
            
        return len(intersection) / len(union)
    
    def _calculate_proximity(
        self,
        result: SearchResult,
        context: EnhancedContext
    ) -> float:
        """Calculate proximity score based on file location"""
        if not context.current_file or not result.file_path:
            return 0.0
        
        current_parts = context.current_file.split('/')
        result_parts = result.file_path.split('/')
        
        # Same file
        if context.current_file == result.file_path:
            return 1.0
        
        # Same directory
        if current_parts[:-1] == result_parts[:-1]:
            return 0.8
        
        # Same module (one level up)
        if len(current_parts) > 2 and len(result_parts) > 2:
            if current_parts[:-2] == result_parts[:-2]:
                return 0.6
        
        # Same project (check repository)
        if context.project_root and result.repository:
            if context.project_root.endswith(result.repository):
                return 0.4
        
        # Different project
        return 0.2
    
    def _calculate_recency(self, result: SearchResult) -> float:
        """Calculate recency score based on last modification"""
        if not result.last_modified:
            return 0.5  # Default for unknown
        
        from datetime import datetime, timedelta
        
        now = datetime.utcnow()
        last_modified = result.last_modified
        
        # Convert string to datetime if needed
        if isinstance(last_modified, str):
            try:
                last_modified = datetime.fromisoformat(last_modified.replace('Z', '+00:00'))
            except:
                return 0.5
        
        age = now - last_modified
        
        # Score based on age
        if age < timedelta(days=1):
            return 1.0
        elif age < timedelta(days=7):
            return 0.9
        elif age < timedelta(days=30):
            return 0.7
        elif age < timedelta(days=90):
            return 0.5
        elif age < timedelta(days=365):
            return 0.3
        else:
            return 0.1
    
    def _calculate_weighted_score(
        self,
        factors: RankingFactors,
        weights: Dict[str, float]
    ) -> float:
        """Calculate weighted score from factors"""
        score = 0.0
        total_weight = 0.0
        
        factor_values = {
            'text_relevance': factors.text_relevance,
            'semantic_similarity': factors.semantic_similarity,
            'context_overlap': factors.context_overlap,
            'import_similarity': factors.import_similarity,
            'proximity_score': factors.proximity_score,
            'recency_score': factors.recency_score,
            'quality_score': factors.quality_score
        }
        
        for factor_name, factor_value in factor_values.items():
            weight = weights.get(factor_name, 0.0)
            score += factor_value * weight
            total_weight += weight
        
        # Normalize by total weight
        if total_weight > 0:
            score /= total_weight
        
        return min(score, 1.0)
    
    def _generate_explanation(
        self,
        factors: RankingFactors,
        weights: Dict[str, float]
    ) -> str:
        """Generate human-readable explanation of ranking"""
        explanations = []
        
        factor_names = {
            'text_relevance': 'Text match',
            'semantic_similarity': 'Semantic similarity',
            'context_overlap': 'Context overlap',
            'import_similarity': 'Import similarity',
            'proximity_score': 'File proximity',
            'recency_score': 'Recent modification',
            'quality_score': 'Code quality'
        }
        
        factor_values = {
            'text_relevance': factors.text_relevance,
            'semantic_similarity': factors.semantic_similarity,
            'context_overlap': factors.context_overlap,
            'import_similarity': factors.import_similarity,
            'proximity_score': factors.proximity_score,
            'recency_score': factors.recency_score,
            'quality_score': factors.quality_score
        }
        
        # Sort factors by contribution
        contributions = []
        for factor_name, factor_value in factor_values.items():
            weight = weights.get(factor_name, 0.0)
            contribution = factor_value * weight
            if contribution > 0.05:  # Only show significant factors
                contributions.append((factor_name, factor_value, contribution))
        
        contributions.sort(key=lambda x: x[2], reverse=True)
        
        # Generate explanation
        for factor_name, factor_value, contribution in contributions[:3]:
            human_name = factor_names.get(factor_name, factor_name)
            explanations.append(f"{human_name}: {factor_value:.2f}")
        
        return " | ".join(explanations) if explanations else "Default ranking"
    
    def _same_module(self, path1: str, path2: str) -> bool:
        """Check if two paths are in the same module"""
        parts1 = path1.split('/')
        parts2 = path2.split('/')
        
        # Remove filename
        if parts1:
            parts1 = parts1[:-1]
        if parts2:
            parts2 = parts2[:-1]
        
        # Check if same directory
        return parts1 == parts2
