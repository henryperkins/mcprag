"""Minimal stub of the *tenacity* package used only for testing.

This stub exports the symbols that the codebase expects (`retry`,
`stop_after_attempt`, `wait_exponential`).  They behave as *no-op*
wrappers so that the real retry logic is skipped inside the sandbox
environment where outbound network calls are disabled anyway.
"""

from typing import Callable, TypeVar, Any

F = TypeVar("F", bound=Callable[..., Any])


def _identity_decorator(func: F) -> F:  # type: ignore[misc]
    """Return the function unchanged (no-op decorator)."""

    return func


# Public API -----------------------------------------------------------------

def retry(*args, **kwargs):  # noqa: D401 – simple passthrough
    """Decorator stub that returns the wrapped function unchanged."""

    # If used with optional arguments (e.g. `@retry(stop=...)`) we need to
    # return a decorator factory.  We therefore detect whether the first
    # positional argument is a callable.
    if args and callable(args[0]):
        return _identity_decorator(args[0])

    # Otherwise return a factory that will receive the actual function.
    def _wrapper(fn: F) -> F:  # type: ignore[misc]
        return fn

    return _wrapper


def stop_after_attempt(*_args, **_kwargs):  # pragma: no cover – trivial
    """Return a placeholder for *stop* conditions (ignored)."""

    return None


def wait_exponential(*_args, **_kwargs):  # pragma: no cover – trivial
    """Return a placeholder for *wait* strategy (ignored)."""

    return None


# Re-export names so `from tenacity import retry, stop_after_attempt, ...` works
__all__ = ["retry", "stop_after_attempt", "wait_exponential"]
