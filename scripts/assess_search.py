#!/usr/bin/env python3
"""
Diagnostics: assess ranker, basic search, relevance, and index integrity.

Runs a few representative queries through both the enhanced ranker and the
basic (BM25) fallback, and fetches Azure Search index health via REST.

Usage:
  source venv/bin/activate
  python scripts/assess_search.py
"""

import asyncio
import json
import os
from typing import Any, Dict, List

from mcprag.server import MCPServer


async def run_query_pair(server: MCPServer, query: str) -> Dict[str, Any]:
    """Run enhanced and basic search for a query and summarize results."""
    from mcprag.mcp.tools._helpers.search_impl import search_code_impl

    # Enhanced search (ranker on)
    enh = await search_code_impl(
        server=server,
        query=query,
        intent=None,
        language=None,
        repository=None,
        max_results=5,
        include_dependencies=False,
        skip=0,
        orderby=None,
        highlight_code=False,
        bm25_only=False,
        exact_terms=None,
        disable_cache=True,
        include_timings=True,
        dependency_mode="auto",
        detail_level="compact",
        snippet_lines=0,
    )

    # Basic search (BM25 only)
    basic = await search_code_impl(
        server=server,
        query=query,
        intent=None,
        language=None,
        repository=None,
        max_results=5,
        include_dependencies=False,
        skip=0,
        orderby=None,
        highlight_code=False,
        bm25_only=True,
        exact_terms=None,
        disable_cache=True,
        include_timings=True,
        dependency_mode="auto",
        detail_level="compact",
        snippet_lines=0,
    )

    def summarize(resp: Dict[str, Any]) -> Dict[str, Any]:
        if not resp.get("ok"):
            return {"ok": False, "error": resp.get("error", "unknown error")}
        data = resp["data"]
        items = data.get("items") or data.get("results") or []
        top = [
            {
                "file": i.get("file"),
                "score": i.get("score") or i.get("relevance"),
                "why": i.get("why"),
            }
            for i in items[:5]
        ]
        return {
            "ok": True,
            "count": data.get("count"),
            "total": data.get("total"),
            "took_ms": data.get("took_ms") or (data.get("timings_ms") or {}).get("total"),
            "top": top,
        }

    return {
        "query": query,
        "enhanced": summarize(enh),
        "basic": summarize(basic),
    }


async def main() -> None:
    server = MCPServer()  # Do not call run(); we use components directly
    await server.ensure_async_components_started()

    # Queries chosen to touch common repo terms
    test_queries = [
        "RAGPipeline ranker",
        "FilterManager language filter",
        "socketpair compatibility patch",
    ]

    results: List[Dict[str, Any]] = []
    for q in test_queries:
        try:
            results.append(await run_query_pair(server, q))
        except Exception as e:
            results.append({"query": q, "error": str(e)})

    # Ranking metrics (may be sparse if little traffic)
    try:
        metrics = await server.get_ranking_metrics(time_window_hours=24)
    except Exception as e:
        metrics = {"error": str(e)}

    # Index health via REST
    health = None
    try:
        if getattr(server, "health_monitor", None):
            health = await server.health_monitor.get_full_health_report()  # type: ignore[func-returns-value]
        else:
            health = {"error": "Health monitor unavailable"}
    except Exception as e:
        health = {"error": str(e)}

    report = {
        "env": {
            "endpoint": os.getenv("ACS_ENDPOINT", ""),
            "index": os.getenv("ACS_INDEX_NAME", ""),
        },
        "queries": results,
        "ranking_metrics": metrics,
        "index_health": health,
    }

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(main())

