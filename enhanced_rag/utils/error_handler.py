"""
Robust error-handling, retry and circuit-breaker utilities
"""

from __future__ import annotations

import functools
import logging
import random
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

# Status codes retriable by default (Azure Search & generic HTTP)
_RETRIABLE_STATUS = {408, 429, 500, 502, 503, 504}

_log = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
# 1.  Structured error envelope
# ------------------------------------------------------------------ #


class ErrorCode:
    RETRYABLE = "RETRYABLE"
    NON_RETRYABLE = "NON_RETRYABLE"
    TIMEOUT = "TIMEOUT"
    CIRCUIT_OPEN = "CIRCUIT_OPEN"


@dataclass
class StructuredError(Exception):
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.code}: {self.message}"


# ------------------------------------------------------------------ #
# 2.  Circuit breaker
# ------------------------------------------------------------------ #


class _CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, reset_sec: int = 30) -> None:
        self._failures = 0
        self._opened_at: Optional[float] = None
        self._th = failure_threshold
        self._reset = reset_sec
        self._lock = threading.Lock()

    def allow(self) -> bool:
        with self._lock:
            if self._opened_at is None:
                return True
            if (time.time() - self._opened_at) > self._reset:
                # half-open
                return True
            return False

    def success(self) -> None:
        with self._lock:
            self._failures = 0
            self._opened_at = None

    def failure(self) -> None:
        with self._lock:
            self._failures += 1
            if self._failures >= self._th:
                self._opened_at = time.time()


# ------------------------------------------------------------------ #
# 3.  Exponential-back-off retry decorator with jitter
# ------------------------------------------------------------------ #


def with_retry(
    *,
    op_name: str,
    max_attempts: int = 5,
    base_delay_ms: int = 200,
    max_delay_ms: int = 4000,
    circuit: Optional[_CircuitBreaker] = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator for automatic retry with full-jitter back-off.
    The wrapped function **may** accept kwargs: timeout (sec) and/or
    deadline_ms (absolute epoch ms) – they will be honoured when present.
    """

    circuit = circuit or _CircuitBreaker()

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def _wrapper(*args: Any, **kwargs: Any) -> Any:
            if not circuit.allow():
                raise StructuredError(
                    ErrorCode.CIRCUIT_OPEN,
                    f"Circuit open – {op_name} temporarily blocked",
                )

            deadline_ms: Optional[int] = kwargs.pop("deadline_ms", None)

            def remaining_ms() -> Optional[int]:
                if deadline_ms is None:
                    return None
                return max(0, deadline_ms - int(time.time() * 1000))

            attempt = 0
            while True:
                attempt += 1
                try:
                    # Inject per-call timeout if caller didn't provide
                    if "timeout" not in kwargs and remaining_ms() is not None:
                        kwargs["timeout"] = max(0.001, (remaining_ms() - 50) / 1000)
                    return func(*args, **kwargs)
                except StructuredError:
                    raise  # Preserve wrapped errors
                except Exception as exc:  # noqa: BLE001
                    status = getattr(exc, "status_code", None) or getattr(
                        exc, "status", None
                    )
                    retriable = (status in _RETRIABLE_STATUS) or isinstance(
                        exc, TimeoutError
                    )
                    if not retriable or attempt >= max_attempts:
                        circuit.failure()
                        raise StructuredError(
                            ErrorCode.RETRYABLE if retriable else ErrorCode.NON_RETRYABLE,
                            f"{op_name} failed after {attempt} attempts – {exc}",
                            {"status": status},
                        ) from exc

                    delay = min(max_delay_ms, base_delay_ms * (2 ** (attempt - 1)))
                    delay = random.uniform(delay / 2, delay)  # full-jitter
                    if remaining_ms() is not None and delay > remaining_ms():
                        raise StructuredError(
                            ErrorCode.TIMEOUT, f"Deadline exhausted in {op_name}"
                        ) from exc

                    _log.debug(
                        "%s attempt %d/%d failed (%s). Retrying in %.0fms",
                        op_name,
                        attempt,
                        max_attempts,
                        status,
                        delay,
                    )
                    time.sleep(delay / 1000)

        return _wrapper

    return decorator


# ------------------------------------------------------------------ #
# 4.  Degraded fallback helper
# ------------------------------------------------------------------ #


def degraded_fallback(primary_fn: Callable[[], Any], fallback_fn: Callable[[], Any], *, op_name: str) -> Any:
    """
    Execute `primary_fn`; on StructuredError return fallback result and log.
    """
    try:
        return primary_fn()
    except StructuredError as e:
        _log.warning("%s degraded – %s", op_name, e.code)
        return fallback_fn()