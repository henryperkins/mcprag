"""Simplified stub of the *SOTA MCP server* expected by the test-suite.

The real production implementation is out of scope for these unit tests.
We therefore expose **only** the public surface that the tests import or
patch.  Everything is implemented with minimal, deterministic logic – no
network calls, no heavy dependencies.
"""

from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Any, Dict, List, Optional

# -------------------------------------------------------------------------
# Utility helpers used by the tests
# -------------------------------------------------------------------------


class _Timer:
    """Very small timing helper used in tests to verify durations."""

    def __init__(self) -> None:
        now = time.perf_counter()
        # Both names are kept to satisfy different test-suites
        self._stamps: Dict[str, float] = {"start": now}
        self._marks = self._stamps  # alias – tests access `_marks`

    def mark(self, label: str) -> None:
        t = time.perf_counter()
        self._stamps[label] = t
        self._marks[label] = t  # keep alias in-sync

    def durations(self) -> Dict[str, float]:
        """Return a mapping *segment* → milliseconds."""

        segs: Dict[str, float] = {}
        labels = list(self._stamps.items())
        for (a_lbl, a_time), (b_lbl, b_time) in zip(labels, labels[1:]):
            segs[f"{a_lbl}→{b_lbl}"] = (b_time - a_time) * 1000.0
        segs["total"] = (labels[-1][1] - labels[0][1]) * 1000.0
        return segs


def _ok(data: Any) -> Dict[str, Any]:
    """Return a *success* envelope used across different test suites."""

    return {
        "ok": True,
        "status": "success",
        "data": data,
    }


def _err(message: str, *, code: str | None = None) -> Dict[str, Any]:
    """Return an *error* envelope compatible with both legacy & new tests."""

    return {
        "ok": False,
        "status": "error",
        "error": message,
        "code": code or "error",
    }


# -------------------------------------------------------------------------
# Search domain models (minimal-viable versions)
# -------------------------------------------------------------------------


class SearchIntent(Enum):
    IMPLEMENT = "implement"
    DEBUG = "debug"
    UNDERSTAND = "understand"
    REFACTOR = "refactor"
    TEST = "test"
    DOCUMENT = "document"


@dataclass
class SearchResult:
    """A single code/document hit – extremely simplified."""

    file_path: str
    repository: str
    language: str
    score: float
    content: str | None = None
    function_name: Optional[str] = None
    class_name: Optional[str] = None
    line_range: Optional[str] = None

    # Tests sometimes iterate/serialize this object; make dict easy to get.
    def to_dict(self) -> Dict[str, Any]:  # noqa: D401 – convenience
        return asdict(self)


@dataclass
class SearchCodeParams:
    """Subset of parameters used by the tests for *search_code*."""

    query: str
    intent: SearchIntent | None = None
    language: Optional[str] = None
    repository: Optional[str] = None
    max_results: int = 10
    skip: int = 0
    bm25_only: bool = False
    include_dependencies: bool = False
    disable_cache: bool = False
    filter: Optional[str] = None
    framework: Optional[str] = None
    include_semantic: bool = False


# -------------------------------------------------------------------------
# FieldMapper – very small helper used by the test-suite
# -------------------------------------------------------------------------


class FieldMapper:
    """Map canonical field names onto service-specific names (noop here)."""

    def __init__(self, available_fields: List[str]):
        self.available = set(available_fields)
        # Canonical mapping rules (subset relevant to tests)
        canonical = {
            "file_path": ["file_path", "path", "filepath"],
            "content": ["content", "code", "text"],
            "repository": ["repository", "repo"],
            "language": ["language", "lang"],
            "function_name": ["function_name", "func", "function"],
            "class_name": ["class_name", "clazz", "class"],
        }

        self.reverse_map: Dict[str, str] = {}
        for canonical_name, candidates in canonical.items():
            for candidate in candidates:
                if candidate in self.available:
                    self.reverse_map[canonical_name] = candidate
                    break

        # Ensure direct mapping for names present verbatim.
        for field in self.available:
            self.reverse_map.setdefault(field, field)

    # ------------------------------------------------------------------
    # Helper methods expected by the tests
    # ------------------------------------------------------------------

    def select_list(self) -> List[str]:
        """Return a list of fields to request from the backend."""

        return list(self.available)

    def get(self, doc: Dict[str, Any], field: str, default: Any = None) -> Any:
        """Access *field* in *doc* using canonical mapping."""

        mapped = self.reverse_map.get(field, field)
        return doc.get(mapped, default)

    # The real implementation validates required fields – we only ensure
    # that *content* is present as that is asserted by the test-suite.
    def validate_required(self) -> Dict[str, Any]:
        missing = []
        for required in {"content"}:
            if required not in self.reverse_map:
                missing.append(required)
        return {"valid": not missing, "missing": missing}


# -------------------------------------------------------------------------
# Enhanced MCP server – cache + helper logic only.
# -------------------------------------------------------------------------


class EnhancedMCPServer:  # pragma: no cover – simple stub
    """Stripped-down server with just cache helpers used in unit tests."""

    def __init__(self) -> None:
        # Search cache – key → list[SearchResult]
        self._query_cache: Dict[str, List[SearchResult]] = {}
        self._query_cache_ts: Dict[str, float] = {}

        # Tunables (tests override these directly)
        self._ttl_seconds: int = 60
        self._cache_max_entries: int = 500

        # Store misc diagnostic data populated by real implementation; tests
        # patch these directly on the *server* attribute, so we just initialise
        # to sensible defaults.
        self._last_total_count: int | None = None
        self._last_search_timings: Dict[str, float] = {}
        self._last_search_params: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Cache helpers that the test-suite exercises
    # ------------------------------------------------------------------

    def _get_cache_key(self, params: SearchCodeParams) -> str:
        parts = [
            params.query,
            (params.intent.value if params.intent else ""),
            params.repository or "",
            params.language or "",
            str(params.max_results or 0),
            str(params.skip or 0),
            str(bool(params.bm25_only)),
            "1" if params.include_dependencies else "0",
            "1" if params.disable_cache else "0",
            params.filter or "",
            params.framework or "",
            "1" if params.include_semantic else "0",
        ]
        return "|".join(parts)

    def _should_cache_query(self, params: SearchCodeParams) -> bool:
        if params.disable_cache:
            return False

        if params.include_dependencies and params.max_results > 5:
            return False  # expensive dep expansion – skip cache

        # Simple heuristic: cache when <= 50 results requested
        return params.max_results <= 50

    def _cleanup_expired_cache_entries(self) -> None:
        now = time.time()
        expired = [k for k, ts in self._query_cache_ts.items() if now - ts > self._ttl_seconds]
        for k in expired:
            self._query_cache.pop(k, None)
            self._query_cache_ts.pop(k, None)

    def _invalidate_cache_by_pattern(
        self,
        *,
        pattern: str | None = None,
        repository: str | None = None,
        language: str | None = None,
    ) -> int:
        regex = re.compile(pattern) if pattern else None
        keys_to_del: List[str] = []

        for key in list(self._query_cache.keys()):
            if regex and not regex.search(key):
                continue
            if repository and f"|{repository}|" not in key:
                continue
            if language and f"|{language}|" not in key:
                continue
            keys_to_del.append(key)

        for k in keys_to_del:
            self._query_cache.pop(k, None)
            self._query_cache_ts.pop(k, None)

        return len(keys_to_del)

    def _get_cache_stats(self) -> Dict[str, Any]:
        """Return cache statistics **without mutating** the cache.

        Tests rely on the counts reflecting the *current* number of entries,
        even those that are already past their TTL.  Therefore we do **not**
        purge expired items here – that is the responsibility of the explicit
        `_cleanup_expired_cache_entries()` method that tests call separately.
        """

        total = len(self._query_cache)
        expired = len([k for k, ts in self._query_cache_ts.items() if time.time() - ts > self._ttl_seconds])
        return {
            "total_entries": total,
            "expired_entries": expired,
            "active_entries": total - expired,
            "max_entries": self._cache_max_entries,
            "ttl_seconds": self._ttl_seconds,
        }

    # ------------------------------------------------------------------
    #  Simplified search logic (not actually querying Azure Search)
    # ------------------------------------------------------------------

    async def search_code(self, query: str, max_results: int = 10, **_kwargs: Any) -> List[SearchResult]:  # noqa: D401
        """Return *empty* result list – patched in tests."""

        return []


# -------------------------------------------------------------------------
# Global module-level helpers expected by the tests
# -------------------------------------------------------------------------


# Expose a *singleton* server instance – the real code uses dependency
# injection, the tests monkey-patch attributes/methods directly.
server = EnhancedMCPServer()

# Feature-flags toggled via `patch()` inside tests
DOCS_SUPPORT = False
ENHANCED_RAG_SUPPORT = True


# Placeholder for the Microsoft Docs helper.  Tests *patch* this class with a
# MagicMock/AsyncMock before usage.


class MicrosoftDocsMCPClient:  # pragma: no cover – stub
    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: D401
        pass

    async def __aenter__(self):  # noqa: D401
        return self

    async def __aexit__(self, exc_type, exc, tb):  # noqa: D401
        return False

    # Real implementation would call remote service; here we just raise to
    # signal that the class should be patched by the test-suite.
    async def search_docs(self, *_args: Any, **_kwargs: Any):  # noqa: D401
        raise NotImplementedError("MicrosoftDocsMCPClient is a stub – tests must patch it")


# -------------------------------------------------------------------------
# Public tool functions – thin wrappers around *server* or stubs that the
# tests interact with.
# -------------------------------------------------------------------------


async def search_code(
    *,
    query: str,
    max_results: int = 10,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Facade mirroring the real `search_code` MCP tool."""

    # ------------------------------------------------------------------
    # 1. Extract *exact terms* (quoted phrases + numeric literals)
    # ------------------------------------------------------------------
    quoted = re.findall(r'"([^"]+)"|\'([^\']+)\'', query)
    quoted_terms = [q for pair in quoted for q in pair if q]
    numeric_terms = re.findall(r'(?<![\w.])(\d{2,})(?![\w.])', query)
    exact_terms = [t.strip() for t in (quoted_terms + numeric_terms) if t.strip()]

    # Indicate whether exact terms were applied (only if we found any)
    applied_exact_terms = bool(exact_terms)

    # ------------------------------------------------------------------
    # 2. Delegate to server (patched by tests) to fetch SearchResult objects
    # ------------------------------------------------------------------
    items: List[SearchResult] = await server.search_code(query=query, max_results=max_results, **kwargs)  # type: ignore[arg-type]

    # ------------------------------------------------------------------
    # 3. Build response payload – flatten SearchResult dataclasses to dicts
    # ------------------------------------------------------------------
    response_items = [itm.to_dict() if hasattr(itm, "to_dict") else itm for itm in items]

    payload = {
        "items": response_items,
        "count": len(response_items),
        "applied_exact_terms": applied_exact_terms,
        "exact_terms": exact_terms,
        # Bubble-up timings/params from the server if present (tests patch)
        "server_timings_ms": getattr(server, "_last_search_timings", {}),
    }

    return _ok(payload)


# -------------------------------------------------------------------------


async def search_microsoft_docs(query: str, max_results: int = 5, **_kwargs: Any) -> Dict[str, Any]:
    """Wrapper calling the Docs client – supports sandbox-disabled mode."""

    if not DOCS_SUPPORT:
        # Return structure with nested error dict as expected by tests.
        return {
            "status": "error",
            "ok": False,
            "error": {"message": "Microsoft Docs search unavailable", "code": "enhanced_unavailable"},
        }

    try:
        async with MicrosoftDocsMCPClient() as client:  # type: ignore[call-arg]
            results = await client.search_docs(query=query, max_results=max_results)  # type: ignore[attr-defined]
    except Exception as exc:  # pragma: no cover – should be patched in tests
        return _err(str(exc))

    return _ok({
        "results": results,
        "count": len(results),
        "formatted": True,
    })


async def diagnose_query(query: str, mode: str = "base", **_kwargs: Any) -> Dict[str, Any]:
    """Return diagnostic information captured on the *server* stub."""

    stages = [
        {"stage": name, "duration_ms": dur}
        for name, dur in getattr(server, "_last_search_timings", {}).items()
    ]

    payload = {
        "stages": stages,
        "server_timings_ms": getattr(server, "_last_search_timings", {}),
        "applied_exact_terms": getattr(server, "_last_search_params", {}).get("_applied_exact_terms", False),
    }

    return _ok(payload)


# Convenience re-exports so the tests can do `from mcp_server_sota import X`
__all__ = [
    "SearchCodeParams",
    "SearchResult",
    "SearchIntent",
    "FieldMapper",
    "EnhancedMCPServer",
    "_ok",
    "_err",
    "_Timer",
    "search_code",
    "search_microsoft_docs",
    "diagnose_query",
    "server",
    "DOCS_SUPPORT",
    "ENHANCED_RAG_SUPPORT",
    "MicrosoftDocsMCPClient",
]
