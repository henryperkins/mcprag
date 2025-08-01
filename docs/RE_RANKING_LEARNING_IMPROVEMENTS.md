# Re-ranking & Learning Systems - Implementation Improvements

## 🎯 Overview

This document outlines concrete improvements needed to fully integrate the re-ranking and learning systems based on the comprehensive review.

## 1. Pattern Matching Integration

### Current Gap
The `ContextualRanker` references `pattern_match` scoring but doesn't implement it.

### Implementation

```python
# enhanced_rag/ranking/pattern_matcher_integration.py

from typing import List, Dict, Float
from ..code_understanding.pattern_recognizer import PatternRecognizer
from ..retrieval.pattern_matcher import PatternMatcher

class PatternMatchScorer:
    """Calculate pattern matching scores for ranking"""
    
    def __init__(self):
        self.recognizer = PatternRecognizer({})
        self.matcher = PatternMatcher({})
    
    async def calculate_pattern_score(
        self,
        result: SearchResult,
        query: str,
        context: Optional[EnhancedContext]
    ) -> float:
        """Calculate pattern match score between query and result"""
        
        # Extract patterns from result
        result_patterns = await self.recognizer.recognize_patterns(
            result.content,
            result.language
        )
        
        # Extract expected patterns from query
        query_patterns = await self._extract_query_patterns(query, context)
        
        # Calculate similarity
        score = 0.0
        
        # Exact pattern matches
        exact_matches = set(result_patterns.keys()) & set(query_patterns)
        score += len(exact_matches) * 0.5
        
        # Similar pattern matches
        for q_pattern in query_patterns:
            for r_pattern, r_confidence in result_patterns.items():
                similarity = self._pattern_similarity(q_pattern, r_pattern)
                score += similarity * r_confidence * 0.3
        
        # Normalize to 0-1
        return min(score / max(len(query_patterns), 1), 1.0)
    
    async def _extract_query_patterns(
        self,
        query: str,
        context: Optional[EnhancedContext]
    ) -> List[str]:
        """Extract expected patterns from query"""
        patterns = []
        
        # Pattern keywords in query
        pattern_keywords = {
            'singleton': ['singleton', 'instance'],
            'factory': ['factory', 'create', 'builder'],
            'observer': ['observer', 'listener', 'event'],
            'decorator': ['decorator', 'wrapper'],
            'async': ['async', 'await', 'concurrent'],
            'cache': ['cache', 'memoize'],
            'retry': ['retry', 'resilient', 'fallback']
        }
        
        query_lower = query.lower()
        for pattern, keywords in pattern_keywords.items():
            if any(kw in query_lower for kw in keywords):
                patterns.append(pattern)
        
        # Add context-based patterns
        if context and context.current_patterns:
            patterns.extend(context.current_patterns[:3])
        
        return patterns
    
    def _pattern_similarity(self, pattern1: str, pattern2: str) -> float:
        """Calculate similarity between two patterns"""
        if pattern1 == pattern2:
            return 1.0
        
        # Related patterns
        pattern_relations = {
            'factory': ['builder', 'abstract_factory'],
            'observer': ['pub_sub', 'event_emitter'],
            'decorator': ['wrapper', 'proxy']
        }
        
        for base, related in pattern_relations.items():
            if pattern1 == base and pattern2 in related:
                return 0.7
            if pattern2 == base and pattern1 in related:
                return 0.7
        
        return 0.0
```

### Update ContextualRanker

```python
# In contextual_ranker.py, add:

async def _calculate_all_factors(
    self,
    result: SearchResult,
    query: str,
    context: Optional[EnhancedContext]
) -> RankingFactors:
    """Calculate all ranking factors"""
    # ... existing code ...
    
    # Add pattern matching
    if not hasattr(self, 'pattern_scorer'):
        from .pattern_matcher_integration import PatternMatchScorer
        self.pattern_scorer = PatternMatchScorer()
    
    factors.pattern_match = await self.pattern_scorer.calculate_pattern_score(
        result, query, context
    )
    
    return factors
```

## 2. Feedback Loop Integration

### Add to Enhanced Search Tool

```python
# In enhanced_search_tool.py, update:

async def search(
    self,
    query: str,
    current_file: Optional[str] = None,
    workspace_root: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """Execute enhanced search through RAG pipeline"""
    
    # Generate query ID for tracking
    query_id = str(uuid.uuid4())
    
    # Track query start
    if hasattr(self.pipeline, 'feedback_collector'):
        await self.pipeline.feedback_collector.track_query(
            query_id=query_id,
            query=query,
            intent=kwargs.get('intent'),
            session_id=kwargs.get('session_id', 'default'),
            metadata={
                'current_file': current_file,
                'workspace_root': workspace_root
            }
        )
    
    # Build context
    context = QueryContext(
        current_file=current_file,
        workspace_root=workspace_root,
        session_id=kwargs.get('session_id', 'default'),
        user_preferences=kwargs.get('preferences', {})
    )
    
    # Process through pipeline
    result = await self.pipeline.process_query(
        query=query,
        context=context,
        generate_response=kwargs.get('generate_response', True)
    )
    
    # Add query_id to response for client-side tracking
    result['query_id'] = query_id
    
    # Format for MCP
    return self._format_mcp_response(result)
```

### Add Feedback Collection Tool

```python
# New file: enhanced_rag/mcp_integration/feedback_tool.py

class FeedbackTool:
    """MCP tool for collecting user feedback"""
    
    def __init__(self, config: Dict[str, Any]):
        self.feedback_collector = FeedbackCollector(config)
    
    async def track_selection(
        self,
        query_id: str,
        result_id: str,
        position: int,
        dwell_time: Optional[float] = None
    ) -> Dict[str, Any]:
        """Track when user selects a result"""
        signal = FeedbackSignal(
            query_id=query_id,
            session_id=self._get_session_id(),
            signal_type=FeedbackType.RESULT_SELECTED,
            result_id=result_id,
            value=1.0,
            metadata={
                'position': position,
                'dwell_time': dwell_time
            }
        )
        
        await self.feedback_collector.collect(signal)
        
        return {'status': 'tracked', 'query_id': query_id}
    
    async def track_copy(
        self,
        query_id: str,
        result_id: str,
        copied_content: str
    ) -> Dict[str, Any]:
        """Track when user copies code from result"""
        signal = FeedbackSignal(
            query_id=query_id,
            session_id=self._get_session_id(),
            signal_type=FeedbackType.CODE_COPIED,
            result_id=result_id,
            value=1.0,
            metadata={
                'content_length': len(copied_content)
            }
        )
        
        await self.feedback_collector.collect(signal)
        
        return {'status': 'tracked', 'query_id': query_id}
```

## 3. Real-time Weight Adaptation

### Adaptive Ranker Implementation

```python
# New file: enhanced_rag/ranking/adaptive_ranker.py

import asyncio
from typing import Dict, Optional
from collections import defaultdict
from datetime import datetime, timedelta

class AdaptiveRanker:
    """Ranker that adapts weights based on user feedback"""
    
    def __init__(
        self,
        base_ranker: ContextualRanker,
        model_updater: ModelUpdater,
        feedback_collector: FeedbackCollector,
        config: Optional[Dict[str, Any]] = None
    ):
        self.base_ranker = base_ranker
        self.model_updater = model_updater
        self.feedback_collector = feedback_collector
        
        # Configuration
        self.config = config or {}
        self.update_interval = self.config.get('update_interval', 100)  # queries
        self.min_feedback_threshold = self.config.get('min_feedback', 10)
        
        # State
        self.queries_since_update = 0
        self.weight_adjustments = defaultdict(lambda: defaultdict(float))
        self.last_update = datetime.now()
        
        # Start background updater
        self._start_background_updater()
    
    async def rank(
        self,
        results: List[SearchResult],
        query: str,
        context: Optional[EnhancedContext] = None,
        intent: Optional[SearchIntent] = None
    ) -> List[SearchResult]:
        """Rank with adaptive weights"""
        # Get current adaptive weights
        weights = await self._get_adaptive_weights(intent or SearchIntent.UNDERSTAND)
        
        # Apply weights to base ranker
        original_weights = self.base_ranker.intent_weights.get(intent, {})
        self.base_ranker.intent_weights[intent] = weights
        
        try:
            # Rank with adapted weights
            ranked = await self.base_ranker.rank(results, query, context, intent)
            
            # Track ranking for learning
            self.queries_since_update += 1
            
            return ranked
        finally:
            # Restore original weights
            self.base_ranker.intent_weights[intent] = original_weights
    
    async def _get_adaptive_weights(self, intent: SearchIntent) -> Dict[str, float]:
        """Get current adaptive weights for intent"""
        base_weights = self.base_ranker._get_intent_weights(intent)
        
        # Apply learned adjustments
        adjustments = self.weight_adjustments.get(intent, {})
        
        adapted_weights = {}
        total = 0
        
        for factor, base_weight in base_weights.items():
            # Apply adjustment with bounds
            adjustment = adjustments.get(factor, 0)
            adapted = base_weight + adjustment
            adapted = max(0.05, min(0.5, adapted))  # Keep weights in reasonable range
            adapted_weights[factor] = adapted
            total += adapted
        
        # Normalize to sum to 1
        if total > 0:
            adapted_weights = {k: v/total for k, v in adapted_weights.items()}
        
        return adapted_weights
    
    async def _update_weights(self):
        """Update weights based on recent feedback"""
        # Get recent feedback
        recent_feedback = await self.feedback_collector.get_feedback_summary(
            since=self.last_update
        )
        
        if len(recent_feedback) < self.min_feedback_threshold:
            return
        
        # Calculate weight updates for each intent
        for intent in SearchIntent:
            updates = await self.model_updater.calculate_weight_updates(
                intent=intent,
                feedback_data=recent_feedback
            )
            
            # Apply updates with learning rate
            learning_rate = 0.1
            for factor, update in updates.items():
                current = self.weight_adjustments[intent][factor]
                self.weight_adjustments[intent][factor] = (
                    current * 0.9 + update * learning_rate
                )
        
        self.last_update = datetime.now()
        self.queries_since_update = 0
        
        # Log updates
        logger.info(f"Updated adaptive weights based on {len(recent_feedback)} feedback items")
    
    def _start_background_updater(self):
        """Start background task for periodic weight updates"""
        async def updater():
            while True:
                await asyncio.sleep(300)  # Update every 5 minutes
                if self.queries_since_update >= self.update_interval:
                    try:
                        await self._update_weights()
                    except Exception as e:
                        logger.error(f"Error updating weights: {e}")
        
        asyncio.create_task(updater())
    
    def get_adaptation_stats(self) -> Dict[str, Any]:
        """Get statistics about adaptation"""
        return {
            'queries_since_update': self.queries_since_update,
            'last_update': self.last_update.isoformat(),
            'weight_adjustments': {
                intent.value: dict(adjustments)
                for intent, adjustments in self.weight_adjustments.items()
            }
        }
```

## 4. Monitoring & Validation

### Weight Validation

```python
# Add to model_updater.py:

def validate_weight_updates(
    self,
    current_weights: Dict[str, float],
    proposed_updates: Dict[str, float]
) -> Dict[str, float]:
    """Validate weight updates to prevent degradation"""
    validated = {}
    
    for factor, update in proposed_updates.items():
        current = current_weights.get(factor, 0.2)
        
        # Limit change magnitude
        max_change = 0.05
        change = update - current
        if abs(change) > max_change:
            change = max_change if change > 0 else -max_change
        
        new_weight = current + change
        
        # Enforce bounds
        new_weight = max(0.05, min(0.5, new_weight))
        
        validated[factor] = new_weight
    
    # Ensure weights sum to 1
    total = sum(validated.values())
    if total > 0:
        validated = {k: v/total for k, v in validated.items()}
    
    return validated
```

### Rollback Capability

```python
# New file: enhanced_rag/learning/weight_history.py

class WeightHistory:
    """Track weight history for rollback"""
    
    def __init__(self, max_history: int = 10):
        self.history = []
        self.max_history = max_history
    
    def save_weights(self, weights: Dict[SearchIntent, Dict[str, float]], metrics: Dict[str, float]):
        """Save current weights with performance metrics"""
        entry = {
            'timestamp': datetime.now(),
            'weights': weights.copy(),
            'metrics': metrics.copy()
        }
        
        self.history.append(entry)
        
        # Keep only recent history
        if len(self.history) > self.max_history:
            self.history.pop(0)
    
    def get_best_weights(self, metric: str = 'success_rate') -> Optional[Dict[SearchIntent, Dict[str, float]]]:
        """Get weights with best performance"""
        if not self.history:
            return None
        
        best_entry = max(self.history, key=lambda x: x['metrics'].get(metric, 0))
        return best_entry['weights']
    
    def rollback_to(self, timestamp: datetime) -> Optional[Dict[SearchIntent, Dict[str, float]]]:
        """Rollback to weights at specific time"""
        for entry in reversed(self.history):
            if entry['timestamp'] <= timestamp:
                return entry['weights']
        return None
```

## 5. Integration into Pipeline

### Update RAGPipeline

```python
# In pipeline.py, add:

def __init__(self, config: Dict[str, Any]):
    # ... existing init ...
    
    # Initialize learning components
    self.feedback_collector = FeedbackCollector(config)
    self.usage_analyzer = UsageAnalyzer(config)
    self.model_updater = ModelUpdater(config)
    
    # Use adaptive ranker if enabled
    if config.get('enable_adaptive_ranking', True):
        base_ranker = ContextualRanker(config)
        self.ranker = AdaptiveRanker(
            base_ranker=base_ranker,
            model_updater=self.model_updater,
            feedback_collector=self.feedback_collector,
            config=config
        )
    else:
        self.ranker = ContextualRanker(config)
```

## Summary

These improvements will:
1. ✅ Complete pattern matching integration
2. ✅ Enable automatic feedback collection
3. ✅ Implement real-time weight adaptation
4. ✅ Add validation and rollback capabilities
5. ✅ Create monitoring infrastructure

The system will truly learn from user interactions and continuously improve its ranking quality.