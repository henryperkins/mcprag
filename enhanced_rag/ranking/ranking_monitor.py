"""
Ranking system monitoring and analytics
Tracks performance, detects issues, and provides insights
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
import json
import statistics

from ..core.models import SearchResult, SearchQuery, SearchIntent, RankingMetrics

logger = logging.getLogger(__name__)


@dataclass
class RankingDecision:
    """Record of a single ranking decision"""
    query_id: str
    query_text: str
    intent: SearchIntent
    timestamp: datetime
    result_count: int
    factor_distributions: Dict[str, Dict[str, float]]  # factor -> {mean, std, min, max}
    score_variance: float
    tie_count: int
    average_confidence: float
    processing_time_ms: float
    user_feedback: Optional[Dict[str, Any]] = None
    

@dataclass
class RankingMetricsSnapshot:
    """Snapshot of ranking metrics over time"""
    timestamp: datetime
    click_through_rate: Dict[int, float]  # position -> CTR
    mean_reciprocal_rank: float
    ndcg_at_k: Dict[int, float]  # k -> NDCG@k
    tie_rate: float
    average_processing_time: float
    factor_importance: Dict[str, float]  # factor -> importance score


class RankingMonitor:
    """Monitor and analyze ranking system performance"""
    
    def __init__(self, storage_backend: Optional[Any] = None):
        self.storage = storage_backend or InMemoryStorage()
        self.metrics_buffer = []
        self.decision_buffer = []
        self.buffer_size = 100
        self.flush_interval = 60  # seconds
        self._start_flush_task()
        
    def _start_flush_task(self):
        """Start background task to periodically flush buffers"""
        asyncio.create_task(self._periodic_flush())
        
    async def _periodic_flush(self):
        """Periodically flush buffers to storage"""
        while True:
            await asyncio.sleep(self.flush_interval)
            await self.flush_buffers()
            
    async def flush_buffers(self):
        """Flush all buffers to storage"""
        if self.decision_buffer:
            await self.storage.store_decisions(self.decision_buffer)
            self.decision_buffer = []
            
        if self.metrics_buffer:
            await self.storage.store_metrics(self.metrics_buffer)
            self.metrics_buffer = []
    
    async def log_ranking_decision(
        self,
        query: SearchQuery,
        results: List[SearchResult],
        factors: List[Dict[str, Any]],
        processing_time_ms: float
    ):
        """Log a ranking decision for analysis"""
        # Calculate factor distributions
        factor_distributions = self._calculate_factor_distributions(factors)
        
        # Calculate score statistics
        scores = [r.score for r in results]
        score_variance = statistics.variance(scores) if len(scores) > 1 else 0.0
        
        # Count ties
        tie_count = self._count_ties(scores)
        
        # Calculate average confidence
        avg_confidence = self._calculate_average_confidence(factors)
        
        decision = RankingDecision(
            query_id=f"{query.user_id or 'anon'}_{int(query.timestamp.timestamp())}",
            query_text=query.query,
            intent=query.intent or SearchIntent.UNDERSTAND,
            timestamp=datetime.utcnow(),
            result_count=len(results),
            factor_distributions=factor_distributions,
            score_variance=score_variance,
            tie_count=tie_count,
            average_confidence=avg_confidence,
            processing_time_ms=processing_time_ms
        )
        
        self.decision_buffer.append(decision)
        
        # Flush if buffer is full
        if len(self.decision_buffer) >= self.buffer_size:
            await self.flush_buffers()
    
    def _calculate_factor_distributions(
        self,
        factors: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, float]]:
        """Calculate distribution statistics for each factor"""
        distributions = {}
        
        factor_names = [
            'text_relevance', 'semantic_similarity', 'context_overlap',
            'import_similarity', 'proximity_score', 'recency_score',
            'quality_score', 'pattern_match'
        ]
        
        for factor_name in factor_names:
            values = []
            for factor_set in factors:
                if factor_name in factor_set:
                    value = factor_set[factor_name]
                    if isinstance(value, dict) and 'value' in value:
                        values.append(value['value'])
                    elif isinstance(value, (int, float)):
                        values.append(value)
            
            if values:
                distributions[factor_name] = {
                    'mean': statistics.mean(values),
                    'std': statistics.stdev(values) if len(values) > 1 else 0.0,
                    'min': min(values),
                    'max': max(values)
                }
        
        return distributions
    
    def _count_ties(self, scores: List[float], precision: int = 4) -> int:
        """Count number of tied scores"""
        rounded_scores = [round(s, precision) for s in scores]
        score_counts = {}
        
        for score in rounded_scores:
            score_counts[score] = score_counts.get(score, 0) + 1
        
        return sum(count - 1 for count in score_counts.values() if count > 1)
    
    def _calculate_average_confidence(self, factors: List[Dict[str, Any]]) -> float:
        """Calculate average confidence across all factors"""
        confidences = []
        
        for factor_set in factors:
            for factor_value in factor_set.values():
                if isinstance(factor_value, dict) and 'confidence' in factor_value:
                    confidences.append(factor_value['confidence'])
        
        return statistics.mean(confidences) if confidences else 1.0
    
    async def record_user_feedback(
        self,
        query_id: str,
        clicked_position: Optional[int] = None,
        dwell_time_seconds: Optional[float] = None,
        rating: Optional[int] = None,
        success: Optional[bool] = None
    ):
        """Record user feedback on search results"""
        feedback = {
            'timestamp': datetime.utcnow().isoformat(),
            'clicked_position': clicked_position,
            'dwell_time_seconds': dwell_time_seconds,
            'rating': rating,
            'success': success
        }
        
        await self.storage.update_decision_feedback(query_id, feedback)
    
    async def calculate_metrics_snapshot(
        self,
        time_window: timedelta = timedelta(hours=1)
    ) -> RankingMetricsSnapshot:
        """Calculate current metrics snapshot"""
        end_time = datetime.utcnow()
        start_time = end_time - time_window
        
        # Get recent decisions
        decisions = await self.storage.get_decisions(start_time, end_time)
        
        if not decisions:
            return self._empty_snapshot()
        
        # Calculate CTR by position
        ctr_by_position = await self._calculate_ctr_by_position(decisions)
        
        # Calculate MRR
        mrr = await self._calculate_mrr(decisions)
        
        # Calculate NDCG@k
        ndcg_scores = await self._calculate_ndcg(decisions, k_values=[3, 5, 10])
        
        # Calculate tie rate
        tie_rate = sum(d.tie_count > 0 for d in decisions) / len(decisions)
        
        # Calculate average processing time
        avg_processing_time = statistics.mean(d.processing_time_ms for d in decisions)
        
        # Calculate factor importance (based on clicked results)
        factor_importance = await self._calculate_factor_importance(decisions)
        
        snapshot = RankingMetricsSnapshot(
            timestamp=end_time,
            click_through_rate=ctr_by_position,
            mean_reciprocal_rank=mrr,
            ndcg_at_k=ndcg_scores,
            tie_rate=tie_rate,
            average_processing_time=avg_processing_time,
            factor_importance=factor_importance
        )
        
        self.metrics_buffer.append(snapshot)
        return snapshot
    
    async def _calculate_ctr_by_position(
        self,
        decisions: List[RankingDecision]
    ) -> Dict[int, float]:
        """Calculate click-through rate by result position"""
        position_clicks = {}
        position_impressions = {}
        
        for decision in decisions:
            if decision.user_feedback and 'clicked_position' in decision.user_feedback:
                pos = decision.user_feedback['clicked_position']
                if pos is not None:
                    position_clicks[pos] = position_clicks.get(pos, 0) + 1
            
            # Count impressions for each position
            for pos in range(min(10, decision.result_count)):
                position_impressions[pos] = position_impressions.get(pos, 0) + 1
        
        # Calculate CTR
        ctr = {}
        for pos in range(10):
            if pos in position_impressions and position_impressions[pos] > 0:
                clicks = position_clicks.get(pos, 0)
                ctr[pos] = clicks / position_impressions[pos]
        
        return ctr
    
    async def _calculate_mrr(self, decisions: List[RankingDecision]) -> float:
        """Calculate Mean Reciprocal Rank"""
        reciprocal_ranks = []
        
        for decision in decisions:
            if decision.user_feedback and 'clicked_position' in decision.user_feedback:
                pos = decision.user_feedback['clicked_position']
                if pos is not None:
                    reciprocal_ranks.append(1.0 / (pos + 1))
                else:
                    reciprocal_ranks.append(0.0)
        
        return statistics.mean(reciprocal_ranks) if reciprocal_ranks else 0.0
    
    async def _calculate_ndcg(
        self,
        decisions: List[RankingDecision],
        k_values: List[int]
    ) -> Dict[int, float]:
        """Calculate Normalized Discounted Cumulative Gain at k"""
        # Simplified NDCG calculation
        # In practice, would need relevance scores for each result
        ndcg_scores = {}
        
        for k in k_values:
            scores = []
            for decision in decisions:
                if decision.user_feedback and 'clicked_position' in decision.user_feedback:
                    pos = decision.user_feedback['clicked_position']
                    if pos is not None and pos < k:
                        # Simple relevance: 1 if clicked, 0 otherwise
                        dcg = 1.0 / (1 + math.log2(pos + 1))
                        idcg = 1.0  # Ideal would be click at position 0
                        scores.append(dcg / idcg)
                    else:
                        scores.append(0.0)
            
            ndcg_scores[k] = statistics.mean(scores) if scores else 0.0
        
        return ndcg_scores
    
    async def _calculate_factor_importance(
        self,
        decisions: List[RankingDecision]
    ) -> Dict[str, float]:
        """Calculate relative importance of ranking factors based on clicks"""
        factor_scores = {}
        factor_counts = {}
        
        for decision in decisions:
            if decision.user_feedback and 'clicked_position' in decision.user_feedback:
                pos = decision.user_feedback['clicked_position']
                if pos is not None:
                    # Higher score for factors of clicked results
                    click_weight = 1.0 / (pos + 1)
                    
                    for factor, dist in decision.factor_distributions.items():
                        if factor not in factor_scores:
                            factor_scores[factor] = 0.0
                            factor_counts[factor] = 0
                        
                        # Weight by mean value and click position
                        factor_scores[factor] += dist['mean'] * click_weight
                        factor_counts[factor] += 1
        
        # Normalize scores
        importance = {}
        for factor, score in factor_scores.items():
            if factor_counts[factor] > 0:
                importance[factor] = score / factor_counts[factor]
        
        return importance
    
    def _empty_snapshot(self) -> RankingMetricsSnapshot:
        """Create empty metrics snapshot"""
        return RankingMetricsSnapshot(
            timestamp=datetime.utcnow(),
            click_through_rate={},
            mean_reciprocal_rank=0.0,
            ndcg_at_k={},
            tie_rate=0.0,
            average_processing_time=0.0,
            factor_importance={}
        )
    
    async def get_performance_report(
        self,
        time_window: timedelta = timedelta(days=7)
    ) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        end_time = datetime.utcnow()
        start_time = end_time - time_window
        
        # Get all snapshots in time window
        snapshots = await self.storage.get_metrics_snapshots(start_time, end_time)
        
        if not snapshots:
            return {'error': 'No data available for the specified time window'}
        
        # Aggregate metrics
        report = {
            'time_window': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat()
            },
            'summary': {
                'total_queries': len(await self.storage.get_decisions(start_time, end_time)),
                'average_mrr': statistics.mean(s.mean_reciprocal_rank for s in snapshots),
                'average_tie_rate': statistics.mean(s.tie_rate for s in snapshots),
                'average_processing_time_ms': statistics.mean(s.average_processing_time for s in snapshots)
            },
            'trends': {
                'mrr_trend': self._calculate_trend([s.mean_reciprocal_rank for s in snapshots]),
                'tie_rate_trend': self._calculate_trend([s.tie_rate for s in snapshots]),
                'processing_time_trend': self._calculate_trend([s.average_processing_time for s in snapshots])
            },
            'factor_analysis': self._aggregate_factor_importance(snapshots),
            'recommendations': await self._generate_recommendations(snapshots)
        }
        
        return report
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction from values"""
        if len(values) < 2:
            return 'stable'
        
        # Simple linear regression
        n = len(values)
        x = list(range(n))
        
        x_mean = sum(x) / n
        y_mean = sum(values) / n
        
        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return 'stable'
        
        slope = numerator / denominator
        
        if slope > 0.01:
            return 'increasing'
        elif slope < -0.01:
            return 'decreasing'
        else:
            return 'stable'
    
    def _aggregate_factor_importance(
        self,
        snapshots: List[RankingMetricsSnapshot]
    ) -> Dict[str, float]:
        """Aggregate factor importance across snapshots"""
        factor_totals = {}
        factor_counts = {}
        
        for snapshot in snapshots:
            for factor, importance in snapshot.factor_importance.items():
                if factor not in factor_totals:
                    factor_totals[factor] = 0.0
                    factor_counts[factor] = 0
                
                factor_totals[factor] += importance
                factor_counts[factor] += 1
        
        # Calculate averages
        avg_importance = {}
        for factor, total in factor_totals.items():
            if factor_counts[factor] > 0:
                avg_importance[factor] = total / factor_counts[factor]
        
        # Sort by importance
        return dict(sorted(avg_importance.items(), key=lambda x: x[1], reverse=True))
    
    async def _generate_recommendations(
        self,
        snapshots: List[RankingMetricsSnapshot]
    ) -> List[str]:
        """Generate actionable recommendations based on metrics"""
        recommendations = []
        
        # Check tie rate
        avg_tie_rate = statistics.mean(s.tie_rate for s in snapshots)
        if avg_tie_rate > 0.15:
            recommendations.append(
                f"High tie rate ({avg_tie_rate:.1%}) detected. Consider refining "
                "ranking factors or adjusting weights for better discrimination."
            )
        
        # Check MRR
        avg_mrr = statistics.mean(s.mean_reciprocal_rank for s in snapshots)
        if avg_mrr < 0.5:
            recommendations.append(
                f"Low MRR ({avg_mrr:.3f}) indicates users often don't click top results. "
                "Review ranking factor weights and consider user feedback."
            )
        
        # Check processing time
        avg_time = statistics.mean(s.average_processing_time for s in snapshots)
        if avg_time > 200:
            recommendations.append(
                f"High average processing time ({avg_time:.0f}ms). Consider optimizing "
                "factor calculations or implementing caching."
            )
        
        # Check factor importance
        latest_importance = snapshots[-1].factor_importance if snapshots else {}
        low_impact_factors = [f for f, imp in latest_importance.items() if imp < 0.1]
        if low_impact_factors:
            recommendations.append(
                f"Low-impact factors detected: {', '.join(low_impact_factors)}. "
                "Consider removing or adjusting these factors."
            )
        
        return recommendations


class InMemoryStorage:
    """Simple in-memory storage for testing"""
    
    def __init__(self):
        self.decisions = []
        self.metrics = []
    
    async def store_decisions(self, decisions: List[RankingDecision]):
        self.decisions.extend(decisions)
    
    async def store_metrics(self, metrics: List[RankingMetricsSnapshot]):
        self.metrics.extend(metrics)
    
    async def get_decisions(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[RankingDecision]:
        return [
            d for d in self.decisions
            if start_time <= d.timestamp <= end_time
        ]
    
    async def get_metrics_snapshots(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[RankingMetricsSnapshot]:
        return [
            m for m in self.metrics
            if start_time <= m.timestamp <= end_time
        ]
    
    async def update_decision_feedback(self, query_id: str, feedback: Dict[str, Any]):
        for decision in self.decisions:
            if decision.query_id == query_id:
                decision.user_feedback = feedback
                break


# Import math for NDCG calculation
import math