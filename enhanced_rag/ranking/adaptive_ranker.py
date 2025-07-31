"""
Adaptive ranker that learns from user feedback
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from collections import defaultdict
from datetime import datetime, timedelta

from ..core.models import SearchResult, EnhancedContext, SearchIntent
from ..learning.feedback_collector import FeedbackCollector
from ..learning.model_updater import ModelUpdater
from .contextual_ranker import ContextualRanker

logger = logging.getLogger(__name__)


class AdaptiveRanker:
    """
    Ranker that adapts weights based on user feedback
    """
    
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
        self.learning_rate = self.config.get('learning_rate', 0.1)
        self.enable_background_updates = self.config.get('enable_background_updates', True)
        
        # State
        self.queries_since_update = 0
        self.weight_adjustments = defaultdict(lambda: defaultdict(float))
        self.last_update = datetime.now()
        self.performance_history = []
        
        # Weight bounds
        self.min_weight = 0.05
        self.max_weight = 0.5
        
        # Start background updater
        if self.enable_background_updates:
            self._start_background_updater()
    
    async def rank(
        self,
        results: List[SearchResult],
        query: str,
        context: Optional[EnhancedContext] = None,
        intent: Optional[SearchIntent] = None
    ) -> List[SearchResult]:
        """
        Rank results with adaptive weights
        
        Args:
            results: Search results to rank
            query: Original search query
            context: Enhanced context with query information
            intent: Search intent
            
        Returns:
            Ranked results
        """
        if not results:
            return results
        
        # Ensure context has query for pattern matching
        if context and not hasattr(context, 'query'):
            context.query = query
        
        # Get current adaptive weights
        intent = intent or SearchIntent.UNDERSTAND
        weights = await self._get_adaptive_weights(intent)
        
        # Store original weights
        original_weights = self.base_ranker.weights.get(intent, {}).copy()
        
        try:
            # Apply adaptive weights
            self.base_ranker.weights[intent] = weights
            
            # Rank with adapted weights
            ranked = await self.base_ranker.rank(results, intent, context)
            
            # Track ranking for learning
            self.queries_since_update += 1
            
            # Check if we should trigger an update
            if self.queries_since_update >= self.update_interval:
                asyncio.create_task(self._update_weights())
            
            return ranked
            
        finally:
            # Restore original weights
            self.base_ranker.weights[intent] = original_weights
    
    async def _get_adaptive_weights(self, intent: SearchIntent) -> Dict[str, float]:
        """Get current adaptive weights for intent"""
        # Get base weights
        base_weights = self.base_ranker._get_intent_weights(intent)
        
        # Apply learned adjustments
        adjustments = self.weight_adjustments.get(intent, {})
        
        adapted_weights = {}
        total = 0
        
        for factor, base_weight in base_weights.items():
            # Apply adjustment with bounds
            adjustment = adjustments.get(factor, 0)
            adapted = base_weight + adjustment
            
            # Keep weights in reasonable range
            adapted = max(self.min_weight, min(self.max_weight, adapted))
            adapted_weights[factor] = adapted
            total += adapted
        
        # Normalize to sum to 1
        if total > 0:
            adapted_weights = {k: v/total for k, v in adapted_weights.items()}
        
        return adapted_weights
    
    async def _update_weights(self):
        """Update weights based on recent feedback"""
        try:
            # Get recent feedback
            since = self.last_update
            recent_feedback = await self.feedback_collector.get_feedback_summary(
                since=since,
                min_items=self.min_feedback_threshold
            )
            
            if len(recent_feedback) < self.min_feedback_threshold:
                logger.info(f"Not enough feedback for update: {len(recent_feedback)} < {self.min_feedback_threshold}")
                return
            
            # Calculate performance metrics
            performance = await self._calculate_performance_metrics(recent_feedback)
            self.performance_history.append({
                'timestamp': datetime.now(),
                'metrics': performance,
                'feedback_count': len(recent_feedback)
            })
            
            # Update weights for each intent
            for intent in SearchIntent:
                intent_feedback = [f for f in recent_feedback if f.get('intent') == intent.value]
                
                if len(intent_feedback) < 5:  # Need minimum feedback per intent
                    continue
                
                # Calculate weight updates
                updates = await self.model_updater.calculate_weight_updates(
                    intent=intent,
                    feedback_data=intent_feedback
                )
                
                # Validate updates
                updates = self._validate_weight_updates(
                    self.weight_adjustments[intent],
                    updates
                )
                
                # Apply updates with learning rate
                for factor, update in updates.items():
                    current = self.weight_adjustments[intent][factor]
                    # Exponential moving average
                    self.weight_adjustments[intent][factor] = (
                        current * (1 - self.learning_rate) + update * self.learning_rate
                    )
            
            self.last_update = datetime.now()
            self.queries_since_update = 0
            
            logger.info(f"✅ Updated adaptive weights based on {len(recent_feedback)} feedback items")
            
        except Exception as e:
            logger.error(f"Error updating weights: {e}")
    
    def _validate_weight_updates(
        self,
        current_adjustments: Dict[str, float],
        proposed_updates: Dict[str, float]
    ) -> Dict[str, float]:
        """Validate weight updates to prevent degradation"""
        validated = {}
        
        for factor, update in proposed_updates.items():
            current = current_adjustments.get(factor, 0)
            
            # Limit change magnitude per update
            max_change = 0.05
            change = update - current
            if abs(change) > max_change:
                change = max_change if change > 0 else -max_change
            
            new_adjustment = current + change
            
            # Keep total adjustment reasonable
            if abs(new_adjustment) > 0.2:
                new_adjustment = 0.2 if new_adjustment > 0 else -0.2
            
            validated[factor] = new_adjustment
        
        return validated
    
    async def _calculate_performance_metrics(
        self,
        feedback_data: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Calculate performance metrics from feedback"""
        metrics = {
            'click_through_rate': 0.0,
            'average_position_clicked': 0.0,
            'refinement_rate': 0.0,
            'success_rate': 0.0,
            'copy_rate': 0.0
        }
        
        if not feedback_data:
            return metrics
        
        # Calculate metrics
        total_queries = len(set(f['query_id'] for f in feedback_data))
        clicks = [f for f in feedback_data if f['signal_type'] == 'result_selected']
        refinements = [f for f in feedback_data if f['signal_type'] == 'query_refined']
        copies = [f for f in feedback_data if f['signal_type'] == 'code_copied']
        
        if total_queries > 0:
            metrics['click_through_rate'] = len(clicks) / total_queries
            metrics['refinement_rate'] = len(refinements) / total_queries
            metrics['copy_rate'] = len(copies) / total_queries
            
        if clicks:
            positions = [f['metadata'].get('position', 0) for f in clicks]
            metrics['average_position_clicked'] = sum(positions) / len(positions)
            
        # Success rate (clicked in top 3)
        top_clicks = [c for c in clicks if c['metadata'].get('position', 10) <= 3]
        metrics['success_rate'] = len(top_clicks) / total_queries if total_queries > 0 else 0
        
        return metrics
    
    def _start_background_updater(self):
        """Start background task for periodic weight updates"""
        async def updater():
            while True:
                await asyncio.sleep(300)  # Update every 5 minutes
                if self.queries_since_update >= self.update_interval:
                    try:
                        await self._update_weights()
                    except Exception as e:
                        logger.error(f"Background update error: {e}")
        
        asyncio.create_task(updater())
    
    def get_adaptation_stats(self) -> Dict[str, Any]:
        """Get statistics about adaptation"""
        stats = {
            'queries_since_update': self.queries_since_update,
            'last_update': self.last_update.isoformat(),
            'weight_adjustments': {
                intent.value: dict(adjustments)
                for intent, adjustments in self.weight_adjustments.items()
            },
            'performance_history': self.performance_history[-10:]  # Last 10 entries
        }
        
        # Add current performance if available
        if self.performance_history:
            stats['current_performance'] = self.performance_history[-1]['metrics']
        
        return stats
    
    async def rollback_weights(self, hours: int = 1):
        """Rollback weight adjustments to previous state"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        # Find the last good state
        for entry in reversed(self.performance_history):
            if entry['timestamp'] < cutoff_time:
                # Reset to this state's adjustments if stored
                logger.info(f"Rolling back to state from {entry['timestamp']}")
                # In a real implementation, we'd store the full state
                self.weight_adjustments.clear()
                self.last_update = datetime.now()
                return True
        
        return False