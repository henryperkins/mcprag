"""
Performance monitoring utilities for Enhanced RAG system
"""

import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque
import asyncio
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """
    Monitor and track performance metrics for the RAG pipeline
    """

    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history))
        self.counters: Dict[str, int] = defaultdict(int)
        self.timers: Dict[str, float] = {}
        self.start_time = datetime.utcnow()

    def start_timer(self, operation: str) -> str:
        """Start timing an operation"""
        timer_id = f"{operation}_{time.time()}"
        self.timers[timer_id] = time.perf_counter()
        return timer_id

    def end_timer(self, timer_id: str, operation: str):
        """End timing and record the duration"""
        if timer_id in self.timers:
            duration = time.perf_counter() - self.timers[timer_id]
            self.record_metric(f"{operation}_duration_ms", duration * 1000)
            del self.timers[timer_id]

    def record_metric(self, metric_name: str, value: float):
        """Record a metric value"""
        self.metrics[metric_name].append({
            'value': value,
            'timestamp': datetime.utcnow()
        })

    def increment_counter(self, counter_name: str, amount: int = 1):
        """Increment a counter"""
        self.counters[counter_name] += amount

    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        current_metrics = {}

        for metric_name, values in self.metrics.items():
            if values:
                recent_values = [v['value'] for v in values]
                current_metrics[metric_name] = {
                    'count': len(recent_values),
                    'avg': sum(recent_values) / len(recent_values),
                    'min': min(recent_values),
                    'max': max(recent_values),
                    'latest': recent_values[-1]
                }

        return {
            'metrics': current_metrics,
            'counters': dict(self.counters),
            'uptime_seconds': (datetime.utcnow() - self.start_time).total_seconds()
        }

    # ------------ NEW convenience ------------ #
    @contextmanager
    def span(self, name: str):
        """Usage:  with monitor.span('stage'): ..."""
        _id = self.start_timer(name)
        try:
            yield
        finally:
            self.end_timer(_id, name)
