"""
Ranking monitor for tracking and improving ranking decisions
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field, asdict
import json
import statistics
from collections import deque
import re

logger = logging.getLogger(__name__)


@dataclass
class RankingDecision:
    """Record of a ranking decision"""
    query_id: str
    query_text: str
    intent: str
    timestamp: datetime
    result_count: int
    factor_distributions: Dict[str, Dict[str, float]]
    score_variance: float
    tie_count: int
    average_confidence: float
    processing_time_ms: float
    user_feedback: Optional[Dict[str, Any]] = None


@dataclass
class RankingMetricsSnapshot:
    """Snapshot of ranking metrics"""
    timestamp: datetime
    click_through_rate: Dict[str, float]
    mean_reciprocal_rank: float
    ndcg_at_k: Dict[int, float]
    tie_rate: float
    average_processing_time: float
    factor_importance: Dict[str, float]


class InMemoryStorage:
    """Simple in-memory storage for testing"""

    def __init__(self):
        # Bound in-memory storage to avoid unbounded growth
        self.decisions = deque(maxlen=5000)
        self.metrics = deque(maxlen=2000)
        self.feedback_by_query = {}  # Track feedback separately

    async def store_decisions(self, decisions: List[RankingDecision]):
        self.decisions.extend(decisions)
        # Initialize feedback entries
        for decision in decisions:
            if decision.query_id not in self.feedback_by_query:
                self.feedback_by_query[decision.query_id] = None

    async def store_metrics(self, metrics: List[RankingMetricsSnapshot]):
        self.metrics.extend(metrics)

    async def get_decisions(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[RankingDecision]:
        results = []
        for d in self.decisions:
            if start_time <= d.timestamp <= end_time:
                # Include feedback if available
                if d.query_id in self.feedback_by_query and self.feedback_by_query[d.query_id]:
                    d.user_feedback = self.feedback_by_query[d.query_id]
                results.append(d)
        return results

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
        # Store feedback
        self.feedback_by_query[query_id] = feedback

        # Update decision objects
        for decision in self.decisions:
            if decision.query_id == query_id:
                decision.user_feedback = feedback
                break


class RankingMonitor:
    """Monitor and improve ranking decisions"""

    def __init__(self, storage: Optional[InMemoryStorage] = None):
        self.storage = storage or InMemoryStorage()
        # Bounded buffer for decisions before flush
        self.buffer = deque(maxlen=100)
        self.buffer_size = 100
        self.flush_interval = 30  # seconds
        # Add property for backward compatibility
        self.decision_buffer = self.buffer

    async def log_ranking_decision(
        self,
        query,
        results: List,
        factors: List[Dict[str, Any]],
        processing_time_ms: float
    ):
        """Log a ranking decision for analysis"""

        # Calculate metrics
        factor_distributions = {}

        # Handle empty factors list
        if factors and len(factors) > 0:
            for factor_name in factors[0].keys():
                values = [f[factor_name]['value'] for f in factors]
                factor_distributions[factor_name] = {
                    'mean': statistics.mean(values),
                    'std': statistics.stdev(values) if len(values) > 1 else 0,
                    'min': min(values),
                    'max': max(values)
                }

        # Calculate score variance
        scores = [r.score for r in results]
        score_variance = statistics.variance(scores) if len(scores) > 1 else 0

        # Count ties
        unique_scores = len(set(scores))
        tie_count = len(scores) - unique_scores

        # Calculate average confidence
        avg_confidence = 0.3  # Lower default for no factors
        if factors and len(factors) > 0:
            try:
                confidences = []
                for f in factors:
                    if isinstance(f, dict) and f:
                        first_key = list(f.keys())[0]
                        if isinstance(f[first_key], dict) and 'confidence' in f[first_key]:
                            confidences.append(f[first_key]['confidence'])
                if confidences:
                    avg_confidence = statistics.mean(confidences)
            except (KeyError, IndexError, TypeError):
                avg_confidence = 0.3  # Fallback on error

        decision = RankingDecision(
            query_id=f"{query.user_id or 'anon'}_{int(query.timestamp.timestamp())}",
            query_text=query.query,
            intent=query.intent.value if hasattr(query.intent, 'value') else str(query.intent),
            timestamp=datetime.now(timezone.utc),
            result_count=len(results),
            factor_distributions=factor_distributions,
            score_variance=score_variance,
            tie_count=tie_count,
            average_confidence=avg_confidence,
            processing_time_ms=processing_time_ms
        )

        self.buffer.append(decision)

        # Flush buffer if full
        if len(self.buffer) >= self.buffer_size:
            await self.flush_buffers()

    async def flush_buffers(self):
        """Flush buffered decisions to storage"""
        if self.buffer:
            await self.storage.store_decisions(list(self.buffer))
            self.buffer.clear()

    async def record_user_feedback(
        self,
        query_id: str,
        clicked_position: Optional[int] = None,
        dwell_time_seconds: Optional[float] = None,
        rating: Optional[int] = None,
        success: Optional[bool] = None
    ):
        """Record user feedback on search results"""
        # Validate inputs to prevent poisoning/injection
        if query_id and not re.match(r'^[A-Za-z0-9_-:.]+$', query_id):
            raise ValueError("Invalid query_id format")
        if clicked_position is not None:
            if not isinstance(clicked_position, int) or clicked_position < 1 or clicked_position > 100:
                raise ValueError("Invalid clicked_position")
        if rating is not None:
            if not isinstance(rating, int) or rating < 1 or rating > 5:
                raise ValueError("Invalid rating")
        feedback = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'clicked_position': clicked_position,
            'dwell_time_seconds': dwell_time_seconds,
            'rating': rating,
            'success': success
        }

        await self.storage.update_decision_feedback(query_id, feedback)

    def _empty_snapshot(self) -> RankingMetricsSnapshot:
        """Create empty metrics snapshot"""
        return RankingMetricsSnapshot(
            timestamp=datetime.now(timezone.utc),
            click_through_rate={},
            mean_reciprocal_rank=0.0,
            ndcg_at_k={},
            tie_rate=0.0,
            average_processing_time=0.0,
            factor_importance={}
        )

    async def calculate_metrics_snapshot(
        self,
        time_window: timedelta = timedelta(hours=1)
    ) -> RankingMetricsSnapshot:
        """Calculate current metrics snapshot"""
        end_time = datetime.now(timezone.utc)
        start_time = end_time - time_window

        decisions = await self.storage.get_decisions(start_time, end_time)

        if not decisions:
            return self._empty_snapshot()

        # Calculate click-through rate by intent
        ctr_by_intent = {}
        for intent in set(d.intent for d in decisions):
            intent_decisions = [d for d in decisions if d.intent == intent]
            # Simplified CTR calculation
            ctr_by_intent[intent] = 0.1  # Placeholder

        # Calculate mean reciprocal rank
        mrr = 0.0
        for decision in decisions:
            if decision.user_feedback and decision.user_feedback.get('clicked_position') is not None:
                mrr += 1.0 / (decision.user_feedback['clicked_position'] + 1)
        mrr = mrr / len(decisions) if decisions else 0.0

        # Calculate NDCG at k
        ndcg_at_k = {}
        for k in [1, 3, 5, 10]:
            ndcg_at_k[k] = 0.0  # Placeholder

        # Calculate tie rate
        total_results = sum(d.result_count for d in decisions)
        total_ties = sum(d.tie_count for d in decisions)
        tie_rate = total_ties / total_results if total_results > 0 else 0.0

        # Calculate average processing time
        avg_processing_time = statistics.mean([d.processing_time_ms for d in decisions]) if decisions else 0.0

        # Calculate factor importance (placeholder)
        factor_importance = {}

        return RankingMetricsSnapshot(
            timestamp=datetime.now(timezone.utc),
            click_through_rate=ctr_by_intent,
            mean_reciprocal_rank=mrr,
            ndcg_at_k=ndcg_at_k,
            tie_rate=tie_rate,
            average_processing_time=avg_processing_time,
            factor_importance=factor_importance
        )

    async def get_performance_report(
        self,
        time_window: timedelta = timedelta(days=7)
    ) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        end_time = datetime.now(timezone.utc)
        start_time = end_time - time_window

        decisions = await self.storage.get_decisions(start_time, end_time)
        metrics = await self.storage.get_metrics_snapshots(start_time, end_time)

        if not decisions and not metrics:
            return {"message": "No data available for the specified time window"}

        # Generate report
        report = {
            "time_window": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            },
            "total_decisions": len(decisions),
            "total_metrics_snapshots": len(metrics),
            "summary": {}
        }

        if decisions:
            avg_tie_rate = statistics.mean([d.tie_count for d in decisions]) / max([d.result_count for d in decisions]) if decisions else 0
            report["summary"]["average_tie_rate"] = avg_tie_rate
            report["summary"]["average_processing_time_ms"] = statistics.mean([d.processing_time_ms for d in decisions]) if decisions else 0
            report["summary"]["average_confidence"] = statistics.mean([d.average_confidence for d in decisions]) if decisions else 0

        return report
