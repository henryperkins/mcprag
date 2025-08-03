"""
Model updater for adaptive learning from user feedback
"""

import asyncio
import logging
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path

from ..core.models import SearchIntent

logger = logging.getLogger(__name__)


class ModelUpdater:
    """
    Updates model weights based on user feedback signals
    """
    
    def __init__(
        self,
        update_frequency: str = "daily",
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize model updater
        
        Args:
            update_frequency: How often to update ("realtime", "hourly", "daily")
            config: Additional configuration
        """
        self.update_frequency = update_frequency
        self.config = config or {}
        
        # Model update settings
        self.min_feedback_per_intent = self.config.get('min_feedback_per_intent', 5)
        self.decay_factor = self.config.get('decay_factor', 0.95)
        self.reward_click_top3 = self.config.get('reward_click_top3', 0.3)
        self.reward_click_top5 = self.config.get('reward_click_top5', 0.1)
        self.penalty_no_click = self.config.get('penalty_no_click', -0.05)
        self.reward_code_copy = self.config.get('reward_code_copy', 0.5)
        
        # Weight factors we optimize
        self.weight_factors = [
            'semantic_similarity',
            'bm25_score',
            'signature_relevance',
            'context_match',
            'dependency_relevance',
            'recency',
            'path_relevance'
        ]
        
        # Learning state
        self.update_history = []
        self.current_weights = self._initialize_weights()
        self.feedback_buffer = defaultdict(list)
        
        # Load persisted state if available
        self._load_state()
    
    def _initialize_weights(self) -> Dict[SearchIntent, Dict[str, float]]:
        """Initialize default weight configurations"""
        return {
            SearchIntent.IMPLEMENT: {
                'semantic_similarity': 0.25,
                'bm25_score': 0.20,
                'signature_relevance': 0.25,
                'context_match': 0.15,
                'dependency_relevance': 0.10,
                'recency': 0.03,
                'path_relevance': 0.02
            },
            SearchIntent.DEBUG: {
                'semantic_similarity': 0.20,
                'bm25_score': 0.25,
                'signature_relevance': 0.20,
                'context_match': 0.20,
                'dependency_relevance': 0.08,
                'recency': 0.05,
                'path_relevance': 0.02
            },
            SearchIntent.UNDERSTAND: {
                'semantic_similarity': 0.30,
                'bm25_score': 0.15,
                'signature_relevance': 0.20,
                'context_match': 0.20,
                'dependency_relevance': 0.10,
                'recency': 0.03,
                'path_relevance': 0.02
            },
            SearchIntent.REFACTOR: {
                'semantic_similarity': 0.25,
                'bm25_score': 0.20,
                'signature_relevance': 0.20,
                'context_match': 0.15,
                'dependency_relevance': 0.15,
                'recency': 0.03,
                'path_relevance': 0.02
            }
        }
    
    async def calculate_weight_updates(
        self,
        intent: SearchIntent,
        feedback_data: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        Calculate weight updates based on feedback
        
        Args:
            intent: Search intent
            feedback_data: List of feedback items
            
        Returns:
            Dict of weight factor -> adjustment value
        """
        if not feedback_data:
            return {}
        
        # Group feedback by query
        queries_feedback = defaultdict(list)
        for feedback in feedback_data:
            query_id = feedback.get('query_id')
            if query_id:
                queries_feedback[query_id].append(feedback)
        
        # Calculate rewards/penalties for each query
        weight_gradients = defaultdict(float)
        total_queries = len(queries_feedback)
        
        for query_id, feedbacks in queries_feedback.items():
            # Calculate query-level reward
            query_reward = self._calculate_query_reward(feedbacks)
            
            # Get the ranking factors that contributed to results
            ranking_factors = self._extract_ranking_factors(feedbacks)
            
            # Distribute reward/penalty across factors
            if ranking_factors:
                factor_contributions = self._calculate_factor_contributions(
                    ranking_factors, 
                    query_reward
                )
                
                for factor, contribution in factor_contributions.items():
                    weight_gradients[factor] += contribution / total_queries
        
        # Apply decay to prevent overfitting
        current_weights = self.current_weights.get(intent, {})
        updates = {}
        
        for factor in self.weight_factors:
            gradient = weight_gradients.get(factor, 0)
            current = current_weights.get(factor, 0.1)
            
            # Update with momentum and bounds
            update = gradient * (1 - self.decay_factor) + current * self.decay_factor
            
            # Ensure weights stay positive and reasonable
            update = max(0.01, min(0.5, update))
            updates[factor] = update
        
        # Normalize updates to sum to 1
        total = sum(updates.values())
        if total > 0:
            updates = {k: v/total for k, v in updates.items()}
        
        # Store in history
        self.update_history.append({
            'timestamp': datetime.now(),
            'intent': intent.value,
            'feedback_count': len(feedback_data),
            'updates': updates.copy()
        })
        
        return updates
    
    def _calculate_query_reward(self, feedbacks: List[Dict[str, Any]]) -> float:
        """Calculate reward signal for a query based on user actions"""
        reward = 0.0
        
        # Check different feedback signals
        clicks = [f for f in feedbacks if f['signal_type'] == 'result_selected']
        copies = [f for f in feedbacks if f['signal_type'] == 'code_copied']
        refinements = [f for f in feedbacks if f['signal_type'] == 'query_refined']
        
        # Reward for clicks based on position
        for click in clicks:
            position = click['metadata'].get('position', 10)
            if position <= 3:
                reward += self.reward_click_top3
            elif position <= 5:
                reward += self.reward_click_top5
            else:
                reward += 0.05  # Small reward for any click
        
        # Strong reward for code copying
        reward += len(copies) * self.reward_code_copy
        
        # Penalty for query refinement (suggests initial results were poor)
        if refinements:
            reward += self.penalty_no_click * 0.5
        
        # Penalty if no clicks at all
        if not clicks and not copies:
            reward += self.penalty_no_click
        
        return reward
    
    def _extract_ranking_factors(
        self, 
        feedbacks: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Extract ranking factors that contributed to results"""
        factors = defaultdict(float)
        
        for feedback in feedbacks:
            # Get result metadata
            result_meta = feedback.get('metadata', {}).get('result_metadata', {})
            
            # Extract factor scores if available
            if 'ranking_factors' in result_meta:
                for factor, score in result_meta['ranking_factors'].items():
                    if factor in self.weight_factors:
                        factors[factor] += score
            else:
                # Fallback: estimate from result properties
                if result_meta.get('similarity_score', 0) > 0.5:
                    factors['semantic_similarity'] += 1.0
                if result_meta.get('bm25_score', 0) > 0:
                    factors['bm25_score'] += 1.0
                if result_meta.get('has_signature_match'):
                    factors['signature_relevance'] += 1.0
        
        # Normalize
        total = sum(factors.values())
        if total > 0:
            factors = {k: v/total for k, v in factors.items()}
        
        return dict(factors)
    
    def _calculate_factor_contributions(
        self,
        ranking_factors: Dict[str, float],
        query_reward: float
    ) -> Dict[str, float]:
        """Calculate how much each factor should be adjusted"""
        contributions = {}
        
        # Positive reward: reinforce factors that contributed
        # Negative reward: reduce factors that contributed
        for factor, weight in ranking_factors.items():
            contributions[factor] = weight * query_reward
        
        return contributions
    
    async def update_model(self, feedback_batch: List[Dict[str, Any]]):
        """
        Process a batch of feedback and update model
        
        Args:
            feedback_batch: List of feedback items
        """
        # Group by intent
        by_intent = defaultdict(list)
        for feedback in feedback_batch:
            intent_str = feedback.get('intent', 'understand')
            try:
                intent = SearchIntent(intent_str)
                by_intent[intent].append(feedback)
            except ValueError:
                logger.warning(f"Unknown intent: {intent_str}")
        
        # Update weights for each intent
        for intent, feedbacks in by_intent.items():
            if len(feedbacks) >= self.min_feedback_per_intent:
                updates = await self.calculate_weight_updates(intent, feedbacks)
                
                # Apply updates
                for factor, new_weight in updates.items():
                    self.current_weights[intent][factor] = new_weight
                
                logger.info(
                    f"Updated weights for {intent.value} based on "
                    f"{len(feedbacks)} feedback items"
                )
        
        # Persist state
        self._save_state()
    
    def get_current_weights(self, intent: SearchIntent) -> Dict[str, float]:
        """Get current weights for an intent"""
        return self.current_weights.get(intent, self._initialize_weights()[intent])
    
    def _save_state(self):
        """Save current state to disk"""
        state_file = Path(self.config.get('state_file', 'model_updater_state.json'))
        
        try:
            state = {
                'current_weights': {
                    intent.value: weights 
                    for intent, weights in self.current_weights.items()
                },
                'update_history': self.update_history[-100:],  # Keep last 100 updates
                'last_update': datetime.now().isoformat()
            }
            
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save model updater state: {e}")
    
    def _load_state(self):
        """Load state from disk"""
        state_file = Path(self.config.get('state_file', 'model_updater_state.json'))
        
        if not state_file.exists():
            return
        
        try:
            with open(state_file, 'r') as f:
                state = json.load(f)
            
            # Restore weights
            for intent_str, weights in state.get('current_weights', {}).items():
                try:
                    intent = SearchIntent(intent_str)
                    self.current_weights[intent] = weights
                except ValueError:
                    pass
            
            # Restore history
            self.update_history = state.get('update_history', [])
            
            logger.info(f"Loaded model updater state from {state_file}")
            
        except Exception as e:
            logger.error(f"Failed to load model updater state: {e}")
    
    def get_update_stats(self) -> Dict[str, Any]:
        """Get statistics about model updates"""
        stats = {
            'total_updates': len(self.update_history),
            'last_update': None,
            'updates_by_intent': defaultdict(int),
            'average_feedback_per_update': 0
        }
        
        if self.update_history:
            stats['last_update'] = self.update_history[-1]['timestamp']
            
            total_feedback = 0
            for update in self.update_history:
                intent = update.get('intent', 'unknown')
                stats['updates_by_intent'][intent] += 1
                total_feedback += update.get('feedback_count', 0)
            
            stats['average_feedback_per_update'] = (
                total_feedback / len(self.update_history)
            )
        
        # Current weights
        stats['current_weights'] = {
            intent.value: weights
            for intent, weights in self.current_weights.items()
        }
        
        return stats
    
    async def simulate_update(
        self,
        intent: SearchIntent,
        feedback_data: List[Dict[str, Any]]
    ) -> Tuple[Dict[str, float], Dict[str, float]]:
        """
        Simulate a weight update without applying it
        
        Returns:
            Tuple of (current_weights, proposed_weights)
        """
        current = self.get_current_weights(intent).copy()
        proposed = await self.calculate_weight_updates(intent, feedback_data)
        
        return current, proposed