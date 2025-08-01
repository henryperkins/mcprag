"""
Error handling utilities for Enhanced RAG system
"""

import logging
import traceback
import time
import random
import asyncio
from typing import Dict, Any, Optional, Callable
from datetime import datetime

logger = logging.getLogger(__name__)

# Lightweight metric hook; PerformanceMonitor may override this via import
try:
    from enhanced_rag.utils.performance_monitor import PerformanceMonitor
    _pm = PerformanceMonitor()

    def record_metric(name: str, value_or_dims: Any) -> None:
        """Record a metric using PerformanceMonitor with safe fallbacks."""
        if isinstance(value_or_dims, (int, float)):
            _pm.record_metric(name, float(value_or_dims))
            return
        if isinstance(value_or_dims, dict):
            latency = value_or_dims.get("latency_ms")
            if latency is not None:
                _pm.record_metric(f"{name}_latency_ms", float(latency))
            attempts = value_or_dims.get("attempts")
            if attempts is not None:
                _pm.record_metric(f"{name}_attempts", float(attempts))
            status = value_or_dims.get("status")
            if status is not None:
                _pm.record_metric(f"{name}_status_{status}", 1.0)
            return
        _pm.increment_counter(f"{name}_count", 1)
except Exception:
    def record_metric(name: str, value_or_dims: Any) -> None:
        """No-op metric recorder if PerformanceMonitor unavailable."""
        return


class ErrorHandler:
    """
    Centralized error handling for the RAG pipeline
    """

    def __init__(self):
        self.error_counts: Dict[str, int] = {}
        self.last_errors: Dict[str, datetime] = {}

    async def handle_error(
        self,
        error: Exception,
        context: Dict[str, Any],
        reraise: bool = False
    ) -> str:
        """
        Handle an error with context information

        Args:
            error: The exception that occurred
            context: Context information about where the error occurred
            reraise: Whether to reraise the exception after handling

        Returns:
            Error message string
        """
        error_type = type(error).__name__
        error_msg = str(error)

        # Track error frequency
        self.error_counts[error_type] = self.error_counts.get(
            error_type, 0
        ) + 1
        self.last_errors[error_type] = datetime.utcnow()

        # Create detailed error message
        detailed_msg = f"{error_type}: {error_msg}"

        # Add context if available
        if context:
            context_str = ", ".join([f"{k}={v}" for k, v in context.items()])
            detailed_msg += f" (Context: {context_str})"

        # Log the error
        logger.error(f"❌ {detailed_msg}")
        logger.debug(f"Stack trace: {traceback.format_exc()}")

        if reraise:
            raise error

        return detailed_msg

    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        return {
            'error_counts': dict(self.error_counts),
            'last_errors': {
                error_type: timestamp.isoformat()
                for error_type, timestamp in self.last_errors.items()
            },
            'total_errors': sum(self.error_counts.values())
        }


def _extract_status_code(exc: Exception) -> Optional[int]:
    status = getattr(exc, "status_code", None)
    if status is not None:
        return status
    resp = getattr(exc, "response", None)
    if resp is not None:
        sc = getattr(resp, "status_code", None)
        if sc is not None:
            return sc
    return None


def with_retry(func: Callable, *args, **kwargs):
    """
    Synchronous retry wrapper with exponential backoff and jitter.
    Retries on 429/502/503/504 up to max_attempts.
    Emits metrics: attempts, latency_ms, status.
    """
    max_attempts = kwargs.pop("max_attempts", 5)
    base_delay_ms = kwargs.pop("base_delay_ms", 100)
    factor = kwargs.pop("factor", 2)
    jitter_ms = kwargs.pop("jitter_ms", 250)

    attempts = 0
    last_exc: Optional[Exception] = None
    start = time.time()

    while attempts < max_attempts:
        try:
            result = func(*args, **kwargs)
            latency_ms = (time.time() - start) * 1000.0
            record_metric(
                "azure_call_success",
                {"attempts": attempts + 1, "latency_ms": latency_ms},
            )
            return result
        except Exception as e:
            status = _extract_status_code(e)
            if status not in (429, 502, 503, 504):
                # Non-retryable
                raise
            last_exc = e
            delay = (
                (base_delay_ms / 1000.0) * (factor ** attempts)
                + random.uniform(0, jitter_ms / 1000.0)
            )
            record_metric(
                "azure_call_retry",
                {"attempts": attempts + 1, "status": status, "delay_s": delay},
            )
            attempts += 1
            time.sleep(delay)

    latency_ms = (time.time() - start) * 1000.0
    record_metric(
        "azure_call_failure",
        {
            "attempts": attempts,
            "latency_ms": latency_ms,
            "status": _extract_status_code(last_exc) if last_exc else None,
        },
    )
    if last_exc:
        raise last_exc
    raise RuntimeError(
        "with_retry exhausted attempts without exception context"
    )


async def with_retry_async(func: Callable, *args, **kwargs):
    """
    Async retry wrapper mirroring with_retry semantics.
    """
    max_attempts = kwargs.pop("max_attempts", 5)
    base_delay_ms = kwargs.pop("base_delay_ms", 100)
    factor = kwargs.pop("factor", 2)
    jitter_ms = kwargs.pop("jitter_ms", 250)

    attempts = 0
    last_exc: Optional[Exception] = None
    start = time.time()

    while attempts < max_attempts:
        try:
            result = await func(*args, **kwargs)
            latency_ms = (time.time() - start) * 1000.0
            record_metric(
                "azure_call_success",
                {"attempts": attempts + 1, "latency_ms": latency_ms},
            )
            return result
        except Exception as e:
            status = _extract_status_code(e)
            if status not in (429, 502, 503, 504):
                raise
            last_exc = e
            delay = (
                (base_delay_ms / 1000.0) * (factor ** attempts)
                + random.uniform(0, jitter_ms / 1000.0)
            )
            record_metric(
                "azure_call_retry",
                {"attempts": attempts + 1, "status": status, "delay_s": delay},
            )
            attempts += 1
            await asyncio.sleep(delay)

    latency_ms = (time.time() - start) * 1000.0
    record_metric(
        "azure_call_failure",
        {
            "attempts": attempts,
            "latency_ms": latency_ms,
            "status": _extract_status_code(last_exc) if last_exc else None,
        },
    )
    if last_exc:
        raise last_exc
    raise RuntimeError("with_retry_async exhausted attempts without exception context")
