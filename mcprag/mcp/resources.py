"""
MCP resource definitions.

Exposes search statistics and metadata as MCP resources.
"""

import json
from datetime import datetime, timezone
from typing import Any
import platform
import sys

from enhanced_rag.core.unified_config import UnifiedConfig as Config


def register_resources(mcp: Any, server: "MCPServer") -> None:
    """Register all MCP resources."""

    @mcp.resource("resource://repositories")
    async def list_repositories() -> str:
        """List all indexed repositories with statistics."""
        try:
            if server.search_client:
                # Use faceted search to get repository counts
                results = server.search_client.search(
                    search_text="*", facets=["repository"], top=0
                )

                facets = results.get_facets() if hasattr(results, "get_facets") else {}
                repos = facets.get("repository", [])

                repo_list = [
                    {"name": r["value"], "documents": r["count"]} for r in repos
                ]

                # Try to detect current repository
                import os
                from pathlib import Path

                current = None
                cwd = Path(os.getcwd())
                for parent in [cwd] + list(cwd.parents):
                    if (parent / ".git").exists():
                        current = parent.name
                        break

                return json.dumps(
                    {
                        "repositories": repo_list,
                        "count": len(repo_list),
                        "current": current,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                    indent=2,
                )
            else:
                return json.dumps({"error": "Search client not available"})

        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.resource("resource://statistics")
    async def get_statistics() -> str:
        """Get comprehensive search statistics."""
        try:
            stats = {
                "index_name": Config.INDEX_NAME,
                "features": {
                    "enhanced_rag": server.enhanced_search is not None,
                    "pipeline": server.pipeline is not None,
                    "code_generation": server.code_gen is not None,
                    "context_analysis": server.context_aware is not None,
                    "semantic_tools": server.intent_classifier is not None,
                    "ranking_tools": server.result_explainer is not None,
                    "cache_manager": server.cache_manager is not None,
                    "learning": server.feedback_collector is not None,
                    # Reflect availability of admin tooling via the unified REST
                    # operations client.  The previous attribute name
                    # `index_ops` was a leftover from an early refactor and is
                    # no longer present on the MCPServer class which now uses
                    # `rest_ops`.  Accessing the non-existent attribute would
                    # raise an AttributeError and break the statistics
                    # endpoint.  Using `rest_ops` correctly reports the admin
                    # functionality without risking a runtime failure.
                    "admin_tools": server.rest_ops is not None,
                    "github_integration": server.github_client is not None,
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            # Add document count if available
            if server.search_client:
                try:
                    stats["total_documents"] = server.search_client.get_document_count()
                except:
                    pass

            return json.dumps(stats, indent=2)

        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.resource("resource://runtime_diagnostics")
    async def runtime_diagnostics() -> str:
        """Get runtime diagnostics information."""
        try:
            diag = {
                "server": {"name": server.name, "version": server.version},
                "config": {
                    "endpoint_prefix": (
                        Config.ENDPOINT.split(".")[0] + "..."
                        if Config.ENDPOINT
                        else None
                    ),
                    "index_name": Config.INDEX_NAME,
                    "cache_ttl": Config.CACHE_TTL_SECONDS,
                    "cache_max_entries": Config.CACHE_MAX_ENTRIES,
                    "admin_mode": Config.ADMIN_MODE,
                    "debug_timings": Config.DEBUG_TIMINGS,
                    "log_level": Config.LOG_LEVEL,
                },
                "features": {
                    "enhanced_rag": server.enhanced_search is not None,
                    "basic_search": server.search_client is not None,
                    "pipeline": server.pipeline is not None,
                    "semantic": server.intent_classifier is not None,
                    "ranking": server.result_explainer is not None,
                    "cache": server.cache_manager is not None,
                    "learning": server.feedback_collector is not None,
                    # Same bug as above – switch to the correct attribute name.
                    "admin": server.rest_ops is not None,
                    "github": server.github_client is not None,
                },
                "python": {
                    "version": platform.python_version(),
                    "platform": platform.platform(),
                },
                "imports": {
                    "mcp_sdk": "mcp.server.fastmcp" in sys.modules,
                    "enhanced_rag": "enhanced_rag" in sys.modules,
                    "azure_sdk": "azure.search.documents" in sys.modules,
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            # Add cache stats if available
            if server.cache_manager:
                try:
                    diag["cache_stats"] = server.cache_manager.get_stats()
                except:
                    pass

            return json.dumps(diag, indent=2)

        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.resource("resource://pipeline_status")
    async def pipeline_status() -> str:
        """Get enhanced RAG pipeline status."""
        if not server.pipeline:
            return json.dumps(
                {"available": False, "reason": "Pipeline not initialized"}, indent=2
            )

        try:
            if hasattr(server.pipeline, "get_pipeline_status"):
                status = server.pipeline.get_pipeline_status()
                return json.dumps(status, indent=2)
            else:
                return json.dumps(
                    {
                        "initialized": True,
                        "status": "Pipeline available but status method not found",
                    },
                    indent=2,
                )
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)
