"""
Improved context-aware result ranking with multi-factor scoring
Fixes critical issues: normalization, tie-breaking, complete weights
"""

import logging
import math
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from ..core.interfaces import Ranker
from ..core.models import (
    SearchResult, EnhancedContext, SearchIntent, CodeContext,
    RankingMetrics, SearchQuery
)

logger = logging.getLogger(__name__)


@dataclass
class ValidatedFactor:
    """Validated ranking factor with confidence and source tracking"""
    value: float
    confidence: float = 1.0  # 0-1 confidence in the measurement
    source: str = "calculated"  # Where the value came from
    
    def __post_init__(self):
        # Ensure value is normalized to [0,1] range
        self.value = max(0.0, min(1.0, self.value))
        self.confidence = max(0.0, min(1.0, self.confidence))


@dataclass
class RankingFactors:
    """Factors used in ranking calculation with validation"""
    text_relevance: ValidatedFactor = field(default_factory=lambda: ValidatedFactor(0.0))
    semantic_similarity: ValidatedFactor = field(default_factory=lambda: ValidatedFactor(0.0))
    context_overlap: ValidatedFactor = field(default_factory=lambda: ValidatedFactor(0.0))
    import_similarity: ValidatedFactor = field(default_factory=lambda: ValidatedFactor(0.0))
    proximity_score: ValidatedFactor = field(default_factory=lambda: ValidatedFactor(0.0))
    recency_score: ValidatedFactor = field(default_factory=lambda: ValidatedFactor(0.0))
    quality_score: ValidatedFactor = field(default_factory=lambda: ValidatedFactor(0.5))
    pattern_match: ValidatedFactor = field(default_factory=lambda: ValidatedFactor(0.0))


class ImprovedContextualRanker(Ranker):
    """
    Improved multi-factor ranking system with normalization, validation, and tie-breaking
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.weights = self._get_complete_intent_weights()
        self._normalization_cache = {}

    def _get_complete_intent_weights(self) -> Dict[SearchIntent, Dict[str, float]]:
        """Get complete ranking weights for all intents (all factors covered)"""
        return {
            SearchIntent.IMPLEMENT: {
                'text_relevance': 0.15,
                'semantic_similarity': 0.25,
                'context_overlap': 0.10,
                'import_similarity': 0.15,
                'proximity_score': 0.05,
                'recency_score': 0.05,
                'quality_score': 0.20,
                'pattern_match': 0.05
            },
            SearchIntent.DEBUG: {
                'text_relevance': 0.30,
                'semantic_similarity': 0.15,
                'context_overlap': 0.15,
                'import_similarity': 0.05,
                'proximity_score': 0.10,
                'recency_score': 0.15,
                'quality_score': 0.05,
                'pattern_match': 0.05
            },
            SearchIntent.UNDERSTAND: {
                'text_relevance': 0.10,
                'semantic_similarity': 0.35,
                'context_overlap': 0.10,
                'import_similarity': 0.05,
                'proximity_score': 0.15,
                'recency_score': 0.05,
                'quality_score': 0.15,
                'pattern_match': 0.05
            },
            SearchIntent.REFACTOR: {
                'text_relevance': 0.15,
                'semantic_similarity': 0.15,
                'context_overlap': 0.10,
                'import_similarity': 0.15,
                'proximity_score': 0.20,
                'recency_score': 0.05,
                'quality_score': 0.15,
                'pattern_match': 0.05
            },
            SearchIntent.TEST: {
                'text_relevance': 0.20,
                'semantic_similarity': 0.10,
                'context_overlap': 0.10,
                'import_similarity': 0.10,
                'proximity_score': 0.25,
                'recency_score': 0.05,
                'quality_score': 0.15,
                'pattern_match': 0.05
            },
            SearchIntent.DOCUMENT: {
                'text_relevance': 0.15,
                'semantic_similarity': 0.30,
                'context_overlap': 0.05,
                'import_similarity': 0.05,
                'proximity_score': 0.10,
                'recency_score': 0.10,
                'quality_score': 0.20,
                'pattern_match': 0.05
            }
        }

    def _normalize_factor(self, value: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
        """Normalize factor to [0,1] range with validation"""
        if math.isnan(value) or math.isinf(value):
            logger.warning(f"Invalid factor value: {value}, using neutral score")
            return 0.5
        
        if max_val == min_val:
            return 0.5
            
        normalized = (value - min_val) / (max_val - min_val)
        return max(0.0, min(1.0, normalized))

    async def rank_results(
        self,
        results: List[SearchResult],
        context: EnhancedContext,
        intent: SearchIntent
    ) -> List[SearchResult]:
        """
        Rank results based on multiple factors with proper normalization
        """
        if not results:
            return []

        # Calculate normalization bounds from all results
        normalization_bounds = self._calculate_normalization_bounds(results)
        
        ranked_results = []

        for result in results:
            # Calculate all ranking factors with validation
            factors = await self._calculate_factors(result, context, normalization_bounds)

            # Apply intent-specific weights
            weights = self.weights.get(intent, self.weights[SearchIntent.IMPLEMENT])
            final_score = self._calculate_weighted_score(factors, weights)

            # Update result with new score and explanation
            result.score = final_score
            result.ranking_explanation = self._generate_explanation(factors, weights)
            
            # Populate ranking factor fields in SearchResult
            result.context_similarity = factors.semantic_similarity.value
            result.import_overlap = factors.import_similarity.value
            result.pattern_match = factors.pattern_match.value
            
            ranked_results.append(result)

        # Sort with tie-breaking rules
        ranked_results.sort(key=lambda x: self._sort_key(x), reverse=True)

        return ranked_results

    def _calculate_normalization_bounds(self, results: List[SearchResult]) -> Dict[str, Tuple[float, float]]:
        """Calculate min/max bounds for normalization"""
        bounds = {
            'text_relevance': (float('inf'), float('-inf')),
            'recency': (float('inf'), float('-inf')),
            'complexity': (float('inf'), float('-inf'))
        }
        
        for result in results:
            # Text relevance bounds (prefer bm25_score or _original_score if available to match factor input)
            try:
                base_val = getattr(result, 'bm25_score', None)
                if base_val is None:
                    base_val = getattr(result, '_original_score', None)
                if base_val is None:
                    base_val = getattr(result, 'score', 0.0)
                base_f = float(base_val)
            except Exception:
                base_f = getattr(result, 'score', 0.0)
            bounds['text_relevance'] = (
                min(bounds['text_relevance'][0], base_f),
                max(bounds['text_relevance'][1], base_f)
            )
            
            # Recency bounds (convert to timestamp)
            if result.last_modified:
                try:
                    if isinstance(result.last_modified, str):
                        timestamp = datetime.fromisoformat(result.last_modified.replace('Z', '+00:00')).timestamp()
                    else:
                        timestamp = result.last_modified.timestamp()
                    bounds['recency'] = (
                        min(bounds['recency'][0], timestamp),
                        max(bounds['recency'][1], timestamp)
                    )
                except:
                    pass
            
            # Complexity bounds
            if hasattr(result, 'complexity_score') and result.complexity_score is not None:
                bounds['complexity'] = (
                    min(bounds['complexity'][0], result.complexity_score),
                    max(bounds['complexity'][1], result.complexity_score)
                )
        
        # Ensure valid bounds
        for key in bounds:
            if bounds[key][0] == float('inf'):
                bounds[key] = (0.0, 1.0)
                
        return bounds

    def _sort_key(self, result: SearchResult) -> Tuple:
        """Multi-level sort key for consistent ordering with tie-breaking"""
        return (
            result.score,  # Primary: final score
            getattr(result, '_original_score', 0.0),  # Secondary: original search score
            -len(result.code_snippet),  # Tertiary: prefer more context
            result.file_path  # Quaternary: alphabetical stability
        )

    async def _calculate_factors(
        self,
        result: SearchResult,
        context: EnhancedContext,
        normalization_bounds: Dict[str, Tuple[float, float]]
    ) -> RankingFactors:
        """Calculate all ranking factors with validation and normalization"""
        factors = RankingFactors()
        
        # Store original score for tie-breaking
        result._original_score = result.score

        # Text relevance (normalized from original search engine score; prefer BM25 if present)
        try:
            orig_score = getattr(result, 'bm25_score', None)
            if orig_score is None:
                orig_score = getattr(result, '_original_score', result.score)
            base_val = float(orig_score) if isinstance(orig_score, (int, float)) else result.score
        except Exception:
            base_val = result.score
        text_score = self._normalize_factor(
            base_val,
            normalization_bounds['text_relevance'][0],
            normalization_bounds['text_relevance'][1]
        )
        factors.text_relevance = ValidatedFactor(text_score, 1.0, "search_engine")

        # Semantic similarity with fallback
        factors.semantic_similarity = await self._calculate_semantic_similarity_with_fallback(
            result, context
        )

        # Context overlap
        overlap_score = self._calculate_context_overlap(result, context)
        factors.context_overlap = ValidatedFactor(overlap_score, 0.9, "calculated")

        # Import similarity
        import_score = self._calculate_import_similarity(result, context)
        factors.import_similarity = ValidatedFactor(import_score, 0.9, "calculated")

        # Proximity score with bias mitigation
        proximity_score = self._calculate_proximity_fair(result, context)
        factors.proximity_score = ValidatedFactor(proximity_score, 0.8, "calculated")

        # Recency score (normalized)
        recency_score = self._calculate_recency_normalized(
            result, normalization_bounds['recency']
        )
        factors.recency_score = ValidatedFactor(recency_score, 0.9, "calculated")

        # Quality score with proper calculation
        quality_score = await self._calculate_quality_score(result)
        factors.quality_score = quality_score

        # Pattern matching score
        if not hasattr(self, 'pattern_scorer'):
            from .pattern_matcher_integration import PatternMatchScorer
            self.pattern_scorer = PatternMatchScorer(self.config)

        query = getattr(context, 'query', '')
        pattern_score = await self.pattern_scorer.calculate_pattern_score(
            result, query, context
        )
        factors.pattern_match = ValidatedFactor(pattern_score, 0.7, "pattern_matcher")

        return factors

    async def _calculate_semantic_similarity_with_fallback(
        self,
        result: SearchResult,
        context: EnhancedContext
    ) -> ValidatedFactor:
        """Calculate semantic similarity with fallback strategies"""
        # 1) Cross-encoder reranker score (if available)
        if hasattr(result, 'cross_encoder_score') and result.cross_encoder_score is not None:
            try:
                val = float(result.cross_encoder_score)
            except Exception:
                val = result.cross_encoder_score
            return ValidatedFactor(
                self._normalize_factor(val),
                1.0,
                "cross_encoder"
            )

        # 2) Azure semantic reranker score (if available)
        if hasattr(result, 'semantic_score') and result.semantic_score is not None:
            try:
                val = float(result.semantic_score)
            except Exception:
                val = result.semantic_score
            return ValidatedFactor(
                self._normalize_factor(val),
                0.9,
                "azure_reranker"
            )

        # 3) Vector similarity (dense embeddings)
        if hasattr(result, 'vector_score') and result.vector_score is not None:
            try:
                val = float(result.vector_score)
            except Exception:
                val = result.vector_score
            return ValidatedFactor(
                self._normalize_factor(val),
                0.8,
                "vector_embeddings"
            )

        # 4) Fallback: Keyword overlap
        if hasattr(context, 'query'):
            keywords = self._extract_keywords(result.code_snippet)
            query_keywords = self._extract_keywords(context.query)

            if keywords and query_keywords:
                overlap = len(keywords & query_keywords) / len(keywords | query_keywords)
                return ValidatedFactor(overlap, 0.6, "keyword_overlap")

        # Final fallback
        return ValidatedFactor(0.0, 0.3, "no_data")

    def _calculate_proximity_fair(self, result: SearchResult, context: EnhancedContext) -> float:
        """Calculate proximity score with logarithmic dampening to reduce bias"""
        base_score = self._calculate_proximity_base(result, context)
        
        # Apply logarithmic dampening to reduce extreme values
        if base_score > 0:
            dampened = math.log(1 + base_score * 4) / math.log(5)
            return min(dampened, 1.0)
        
        return 0.0

    def _calculate_proximity_base(
        self,
        result: SearchResult,
        context: EnhancedContext
    ) -> float:
        """Base proximity calculation"""
        if not context.current_file or not result.file_path:
            return 0.0

        current_parts = context.current_file.split('/')
        result_parts = result.file_path.split('/')

        # Same file
        if context.current_file == result.file_path:
            return 1.0

        # Same directory
        if current_parts[:-1] == result_parts[:-1]:
            return 0.7

        # Same module (one level up)
        if len(current_parts) > 2 and len(result_parts) > 2:
            if current_parts[:-2] == result_parts[:-2]:
                return 0.5

        # Same project
        if context.project_root and result.repository:
            if context.project_root.endswith(result.repository):
                return 0.3

        # Different project but same language
        if context.language == result.language:
            return 0.1

        return 0.0

    def _calculate_recency_normalized(
        self,
        result: SearchResult,
        bounds: Tuple[float, float]
    ) -> float:
        """Calculate normalized recency score"""
        if not result.last_modified:
            return 0.5  # Neutral score for unknown
        
        try:
            # Convert to timestamp
            if isinstance(result.last_modified, str):
                timestamp = datetime.fromisoformat(
                    result.last_modified.replace('Z', '+00:00')
                ).timestamp()
            else:
                timestamp = result.last_modified.timestamp()
            
            # Normalize using bounds
            if bounds[1] > bounds[0]:
                normalized = (timestamp - bounds[0]) / (bounds[1] - bounds[0])
                return self._normalize_factor(normalized)
            else:
                return 0.5
                
        except Exception as e:
            logger.warning(f"Error calculating recency: {e}")
            return 0.5

    async def _calculate_quality_score(self, result: SearchResult) -> ValidatedFactor:
        """Calculate quality score from multiple signals"""
        scores = []
        confidence = 0.0
        
        # Check for explicit quality score
        if hasattr(result, 'quality_score') and result.quality_score is not None:
            return ValidatedFactor(
                self._normalize_factor(result.quality_score),
                0.8,
                "explicit_score"
            )
        
        # Calculate from other signals
        if hasattr(result, 'test_coverage') and result.test_coverage is not None:
            scores.append(self._normalize_factor(result.test_coverage))
            confidence += 0.3
        
        if hasattr(result, 'complexity_score') and result.complexity_score is not None:
            # Lower complexity is better
            complexity_normalized = 1.0 - self._normalize_factor(result.complexity_score, 0, 50)
            scores.append(complexity_normalized)
            confidence += 0.2
        
        # Check for documentation
        if result.semantic_context or (hasattr(result, 'caption') and result.caption):
            scores.append(0.7)
            confidence += 0.2
        
        # Check for tests
        if any('test' in tag.lower() for tag in result.tags):
            scores.append(0.8)
            confidence += 0.1
        
        if scores:
            avg_score = sum(scores) / len(scores)
            return ValidatedFactor(avg_score, min(confidence, 1.0), "calculated")
        
        # Default with low confidence
        return ValidatedFactor(0.3, 0.3, "default")

    def _calculate_context_overlap(
        self,
        result: SearchResult,
        context: EnhancedContext
    ) -> float:
        """Calculate context overlap with clear distinctions"""
        overlap_score = 0.0
        weights_sum = 0.0

        # Import overlap (distinct from import_similarity)
        if context.imports and result.imports:
            common_imports = set(context.imports) & set(result.imports)
            if context.imports:
                import_overlap = len(common_imports) / len(context.imports)
                overlap_score += import_overlap * 0.3
                weights_sum += 0.3

        # Function/class usage overlap
        if context.functions and hasattr(result, 'dependencies'):
            common_functions = set(context.functions) & set(result.dependencies)
            if context.functions:
                function_overlap = len(common_functions) / len(context.functions)
                overlap_score += function_overlap * 0.3
                weights_sum += 0.3

        # Framework match
        if context.framework and hasattr(result, 'framework'):
            if context.framework == getattr(result, 'framework', ''):
                overlap_score += 0.2
                weights_sum += 0.2

        # Language match
        if context.language == result.language:
            overlap_score += 0.2
            weights_sum += 0.2

        # Normalize by actual weights used
        if weights_sum > 0:
            return overlap_score / weights_sum
        
        return 0.0

    def _calculate_import_similarity(
        self,
        result: SearchResult,
        context: EnhancedContext
    ) -> float:
        """Calculate import similarity (Jaccard coefficient)"""
        if not context.imports or not result.imports:
            return 0.0

        context_imports = set(context.imports)
        result_imports = set(result.imports)

        # Jaccard similarity
        intersection = context_imports & result_imports
        union = context_imports | result_imports

        if not union:
            return 0.0

        return len(intersection) / len(union)

    def _extract_keywords(self, text: str) -> set:
        """Extract keywords from text for fallback similarity calculation"""
        # Simple keyword extraction (can be improved with NLP)
        import re
        
        # Remove common code symbols and split on word boundaries
        words = re.findall(r'\b[a-zA-Z_]\w*\b', text.lower())
        
        # Filter out common stop words and very short words
        stop_words = {'the', 'is', 'at', 'which', 'on', 'and', 'a', 'an', 'as', 'by', 'for', 'if', 'in', 'it', 'of', 'or', 'to'}
        keywords = {w for w in words if len(w) > 2 and w not in stop_words}
        
        return keywords

    def _calculate_weighted_score(
        self,
        factors: RankingFactors,
        weights: Dict[str, float]
    ) -> float:
        """Calculate weighted score with confidence adjustment"""
        score = 0.0
        total_weight = 0.0
        
        factor_map = {
            'text_relevance': factors.text_relevance,
            'semantic_similarity': factors.semantic_similarity,
            'context_overlap': factors.context_overlap,
            'import_similarity': factors.import_similarity,
            'proximity_score': factors.proximity_score,
            'recency_score': factors.recency_score,
            'quality_score': factors.quality_score,
            'pattern_match': factors.pattern_match
        }
        
        for factor_name, factor in factor_map.items():
            weight = weights.get(factor_name, 0.0)
            if weight > 0:
                # Adjust contribution by confidence
                contribution = factor.value * weight * factor.confidence
                score += contribution
                total_weight += weight * factor.confidence
        
        # Normalize by total weight
        if total_weight > 0:
            return score / total_weight
        
        return 0.0

    def _generate_explanation(
        self,
        factors: RankingFactors,
        weights: Dict[str, float]
    ) -> str:
        """Generate detailed explanation of ranking with confidence"""
        explanations = []

        factor_names = {
            'text_relevance': 'Text match',
            'semantic_similarity': 'Semantic similarity',
            'context_overlap': 'Context overlap',
            'import_similarity': 'Import similarity',
            'proximity_score': 'File proximity',
            'recency_score': 'Recent modification',
            'quality_score': 'Code quality',
            'pattern_match': 'Pattern match'
        }

        factor_map = {
            'text_relevance': factors.text_relevance,
            'semantic_similarity': factors.semantic_similarity,
            'context_overlap': factors.context_overlap,
            'import_similarity': factors.import_similarity,
            'proximity_score': factors.proximity_score,
            'recency_score': factors.recency_score,
            'quality_score': factors.quality_score,
            'pattern_match': factors.pattern_match
        }

        # Calculate contributions
        contributions = []
        for factor_name, factor in factor_map.items():
            weight = weights.get(factor_name, 0.0)
            if weight > 0:
                contribution = factor.value * weight * factor.confidence
                contributions.append((
                    factor_name,
                    factor.value,
                    contribution,
                    factor.confidence,
                    factor.source
                ))

        # Sort by contribution
        contributions.sort(key=lambda x: x[2], reverse=True)

        # Generate explanation for top factors
        for factor_name, value, contribution, confidence, source in contributions[:3]:
            if contribution > 0.01:  # Only show meaningful contributions
                human_name = factor_names.get(factor_name, factor_name)
                confidence_str = f" ({int(confidence * 100)}% conf)" if confidence < 1.0 else ""
                explanations.append(f"{human_name}: {value:.2f}{confidence_str}")

        return " | ".join(explanations) if explanations else "Default ranking"

    async def explain_ranking(
        self,
        result: SearchResult,
        query: SearchQuery,
        context: CodeContext
    ) -> Dict[str, Any]:
        """Explain why a result is relevant with full details"""
        # Convert CodeContext to EnhancedContext
        enhanced_context = EnhancedContext(
            current_file=context.current_file,
            file_content=context.file_content,
            imports=context.imports,
            functions=context.functions,
            classes=context.classes,
            recent_changes=context.recent_changes,
            git_branch=context.git_branch,
            language=context.language,
            framework=context.framework,
            project_root=context.project_root,
            open_files=context.open_files,
            session_id=context.session_id
        )

        # Calculate normalization bounds
        normalization_bounds = self._calculate_normalization_bounds([result])
        
        # Calculate ranking factors
        factors = await self._calculate_factors(result, enhanced_context, normalization_bounds)
        weights = self.weights.get(query.intent, self.weights[SearchIntent.IMPLEMENT])

        return {
            'explanation': self._generate_explanation(factors, weights),
            'factors': {
                'text_relevance': {
                    'value': factors.text_relevance.value,
                    'confidence': factors.text_relevance.confidence,
                    'source': factors.text_relevance.source
                },
                'semantic_similarity': {
                    'value': factors.semantic_similarity.value,
                    'confidence': factors.semantic_similarity.confidence,
                    'source': factors.semantic_similarity.source
                },
                'context_overlap': {
                    'value': factors.context_overlap.value,
                    'confidence': factors.context_overlap.confidence,
                    'source': factors.context_overlap.source
                },
                'import_similarity': {
                    'value': factors.import_similarity.value,
                    'confidence': factors.import_similarity.confidence,
                    'source': factors.import_similarity.source
                },
                'proximity_score': {
                    'value': factors.proximity_score.value,
                    'confidence': factors.proximity_score.confidence,
                    'source': factors.proximity_score.source
                },
                'recency_score': {
                    'value': factors.recency_score.value,
                    'confidence': factors.recency_score.confidence,
                    'source': factors.recency_score.source
                },
                'quality_score': {
                    'value': factors.quality_score.value,
                    'confidence': factors.quality_score.confidence,
                    'source': factors.quality_score.source
                },
                'pattern_match': {
                    'value': factors.pattern_match.value,
                    'confidence': factors.pattern_match.confidence,
                    'source': factors.pattern_match.source
                }
            },
            'weights': weights,
            'final_score': self._calculate_weighted_score(factors, weights)
        }

    async def get_ranking_metrics(
        self,
        results: List[SearchResult]
    ) -> RankingMetrics:
        """Get detailed ranking metrics with additional statistics"""
        if not results:
            return RankingMetrics(
                total_results=0,
                filtered_count=0,
                context_boost_applied=0,
                average_score=0.0,
                score_distribution={},
                ranking_factors={},
                processing_time_ms=0.0
            )

        # Calculate metrics
        scores = [r.score for r in results]
        avg_score = sum(scores) / len(scores)
        
        # Detect ties
        score_counts = {}
        for score in scores:
            score_rounded = round(score, 4)
            score_counts[score_rounded] = score_counts.get(score_rounded, 0) + 1
        
        tie_count = sum(1 for count in score_counts.values() if count > 1)

        # Score distribution
        score_ranges = {
            '0.0-0.2': 0,
            '0.2-0.4': 0,
            '0.4-0.6': 0,
            '0.6-0.8': 0,
            '0.8-1.0': 0
        }

        for score in scores:
            if score < 0.2:
                score_ranges['0.0-0.2'] += 1
            elif score < 0.4:
                score_ranges['0.2-0.4'] += 1
            elif score < 0.6:
                score_ranges['0.4-0.6'] += 1
            elif score < 0.8:
                score_ranges['0.6-0.8'] += 1
            else:
                score_ranges['0.8-1.0'] += 1

        # Factor statistics
        factor_stats = {
            'average_confidence': 0.85,  # Would be calculated from actual factors
            'factors_with_low_confidence': 0,
            'factors_using_fallback': 0
        }

        return RankingMetrics(
            total_results=len(results),
            filtered_count=len([r for r in results if r.score > 0.5]),
            context_boost_applied=len([r for r in results if hasattr(r, 'context_similarity') and r.context_similarity and r.context_similarity > 0.3]),
            average_score=avg_score,
            score_distribution=score_ranges,
            ranking_factors={
                'tie_count': tie_count,
                'score_variance': sum((s - avg_score) ** 2 for s in scores) / len(scores) if len(scores) > 1 else 0,
                **factor_stats
            },
            processing_time_ms=0.0  # Would be measured in real implementation
        )