"""Light-weight stub module for the *openai* Python SDK.

Only the handful of attributes referenced by the codebase/tests are
implemented.  The goal is to avoid `ModuleNotFoundError` in the sandbox –
**no real network calls are performed.**
"""

from __future__ import annotations

import types
from typing import Any, List


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _EmbeddingData:
    """Simple structure mimicking the object returned by OpenAI."""

    def __init__(self, embedding: List[float]):
        self.embedding = embedding


class _EmbeddingResponse:
    """Mimic the *openai* embeddings response object."""

    def __init__(self, vector: List[float]):
        # The real SDK exposes `.data` – we replicate this minimal API.
        self.data = [_EmbeddingData(vector)]


def _fake_create(*_args: Any, **_kwargs: Any) -> _EmbeddingResponse:  # noqa: D401
    """Return a deterministic zero-vector embedding."""

    # 1536-dimensional zero vector keeps size reasonable while matching
    # common OpenAI defaults.
    return _EmbeddingResponse([0.0] * 1536)


# The *embeddings* attribute on client instances is a namespace with a
# `.create()` method.  Using `types.SimpleNamespace` keeps it trivial.
_embeddings_namespace = types.SimpleNamespace(create=_fake_create)


class _BaseClient:
    """Tiny base client exposing `.embeddings.create()` like the real one."""

    def __init__(self, **_kwargs: Any):
        # The stub ignores all kwargs (api_key, endpoint, …).
        self.embeddings = _embeddings_namespace


class AzureOpenAI(_BaseClient):  # type: ignore[override]
    """Stub for *openai.AzureOpenAI* client."""


class OpenAI(_BaseClient):  # type: ignore[override]
    """Stub for *openai.OpenAI* client."""


# Re-export the public names expected by `from openai import AzureOpenAI`.
__all__ = ["AzureOpenAI", "OpenAI"]
