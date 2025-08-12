"""
MCP Server orchestration.

Initializes and coordinates enhanced_rag modules for MCP access.
"""

import logging
import os
from typing import Dict, Any, Literal, cast

from enhanced_rag.core.config import get_config, validate_config
from .compatibility.socketpair_patch import apply_patches

# Import what we need from enhanced_rag - separate try/except for each component
EnhancedSearchTool = None
try:
    from enhanced_rag.mcp_integration.enhanced_search_tool import EnhancedSearchTool
    ENHANCED_SEARCH_AVAILABLE = True
except ImportError:
    ENHANCED_SEARCH_AVAILABLE = False

CodeGenerationTool = None
try:
    from enhanced_rag.mcp_integration.code_gen_tool import CodeGenerationTool
    CODE_GEN_AVAILABLE = True
except ImportError:
    CODE_GEN_AVAILABLE = False

ContextAwareTool = None
try:
    from enhanced_rag.mcp_integration.context_aware_tool import ContextAwareTool
    CONTEXT_AWARE_AVAILABLE = True
except ImportError:
    CONTEXT_AWARE_AVAILABLE = False

# For backward compatibility
ENHANCED_RAG_AVAILABLE = (
    ENHANCED_SEARCH_AVAILABLE or CODE_GEN_AVAILABLE or CONTEXT_AWARE_AVAILABLE
)

try:
    VECTOR_SUPPORT = True
except ImportError:
    VECTOR_SUPPORT = False

RAGPipeline = None
try:
    from enhanced_rag.pipeline import RAGPipeline
    PIPELINE_AVAILABLE = True
except ImportError:
    PIPELINE_AVAILABLE = False

FeedbackCollector = None
UsageAnalyzer = None
ModelUpdater = None
try:
    from enhanced_rag.learning.feedback_collector import FeedbackCollector
    from enhanced_rag.learning.usage_analyzer import UsageAnalyzer
    from enhanced_rag.learning.model_updater import ModelUpdater
    LEARNING_SUPPORT = True
except ImportError:
    LEARNING_SUPPORT = False

# NOTE: The legacy Azure SDK based admin helpers (IndexOperations, IndexerIntegration,
# DocumentOperations) have been fully replaced by their REST-API counterparts as part
# of the Azure integration migration (see docs/azure_integration_migration_plan.md).
# We purposely avoid importing the deprecated modules here to prevent an unnecessary
# runtime dependency on the Azure SDK.  Instead, REST_API_SUPPORT (defined below)
# determines whether admin-level functionality is available.

# Kept for backward-compatibility checks further down in the module.  Code that still
# guards on `AZURE_ADMIN_SUPPORT` should now reference the REST implementation.
AZURE_ADMIN_SUPPORT = False

# GitHub integration pulls in FastAPI app with slowapi limiter that can fail outside web context.
# To avoid import-time side effects for MCP server, guard these imports strictly.
GitHubClient = None
RemoteIndexer = None
try:
    from enhanced_rag.github_integration.api_client import GitHubClient  # type: ignore
    from enhanced_rag.github_integration.remote_indexer import RemoteIndexer  # type: ignore
    GITHUB_SUPPORT = True
except Exception:
    GITHUB_SUPPORT = False

IntentClassifier = None
ContextualQueryEnhancer = None
MultiVariantQueryRewriter = None
try:
    from enhanced_rag.semantic.intent_classifier import IntentClassifier
    from enhanced_rag.semantic.query_enhancer import ContextualQueryEnhancer
    from enhanced_rag.semantic.query_rewriter import MultiVariantQueryRewriter
    SEMANTIC_SUPPORT = True
except ImportError:
    SEMANTIC_SUPPORT = False

ResultExplainer = None
try:
    from enhanced_rag.ranking.result_explainer import ResultExplainer
    RANKING_SUPPORT = True
except ImportError:
    RANKING_SUPPORT = False

CacheManager = None
try:
    from enhanced_rag.utils.cache_manager import CacheManager
    CACHE_SUPPORT = True
except ImportError:
    CACHE_SUPPORT = False

# Direct Azure Search for fallback
SearchClient = None
AzureKeyCredential = None
try:
    from azure.search.documents import SearchClient
    from azure.core.credentials import AzureKeyCredential
    AZURE_SDK_AVAILABLE = True
except ImportError:
    AZURE_SDK_AVAILABLE = False

# New REST API automation support
AzureSearchClient = None
SearchOperations = None
IndexAutomation = None
DataAutomation = None
IndexerAutomation = None
HealthMonitor = None
try:
    from enhanced_rag.azure_integration.rest import AzureSearchClient, SearchOperations
    from enhanced_rag.azure_integration.automation import (
        IndexAutomation,
        DataAutomation,
        IndexerAutomation,
        HealthMonitor
    )
    REST_API_SUPPORT = True
except ImportError:
    REST_API_SUPPORT = False

# MCP SDK
try:
    # Preferred import path when using the MCP SDK package
    from mcp.server.fastmcp import FastMCP as _FastMCP

    MCP_SDK_AVAILABLE = True
    FastMCP = _FastMCP
except ImportError:
    try:
        # Fallback to standalone fastmcp package if available
        from fastmcp import FastMCP as _FastMCP  # type: ignore

        MCP_SDK_AVAILABLE = True
        FastMCP = _FastMCP
    except ImportError:
        MCP_SDK_AVAILABLE = False

        # Fallback for testing environments without the SDK
        class _MockFastMCP:
            def __init__(self, name: str):
                self.name = name

            def tool(self):
                return lambda f: f

            def resource(self):
                return lambda f: f

            def prompt(self):
                return lambda f: f

            def run(self, transport: Literal["stdio", "sse", "streamable-http"] = "stdio"):
                # Avoid writing to stdout to not break stdio transport clients
                try:
                    import sys
                    sys.stderr.write(f"Mock MCP server {self.name} running\n")
                except Exception:
                    pass

        FastMCP = _MockFastMCP

logger = logging.getLogger(__name__)


class MCPServer:
    """MCP Server orchestrating enhanced_rag modules."""

    def __init__(self):
        """Initialize MCP server."""
        self.name = "azure-code-search-enhanced"
        self.version = "3.0.0"

        # Validate configuration, but don't hard-fail startup.
        # This allows the server to start and advertise limited functionality
        # (e.g. no search backend) rather than failing to connect entirely.
        config = get_config()
        try:
            validate_config(config)
        except ValueError as e:
            logger.warning("Configuration issues detected; continuing with degraded features: %s", str(e))

        # ------------------------------------------------------------------
        # Setup logging
        # ------------------------------------------------------------------
        # The log level is read from the MCP_LOG_LEVEL environment variable via
        # Config.LOG_LEVEL.  Users occasionally provide values that are not
        # valid `logging` symbols (for example "TRACE" or lowercase strings).
        # `getattr(logging, invalid_level)` would raise an AttributeError and
        # abort the server start-up.  To make the server more robust we fall
        # back to INFO when the supplied value is unknown.

        # Get log level from either MCP_LOG_LEVEL env var or config.log_level
        _log_level: str = os.getenv("MCP_LOG_LEVEL", config.log_level).upper()
        _resolved_level = getattr(logging, _log_level, logging.INFO)

        # Defensive logging setup: avoid reconfiguring if already configured elsewhere
        root = logging.getLogger()
        already_configured = len(root.handlers) > 0

        if getattr(logging, _log_level, None) is None:
            if not already_configured:
                logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            logging.getLogger(__name__).warning(
                "Unknown LOG_LEVEL '%s' – falling back to INFO", _log_level
            )
            root.setLevel(logging.INFO)
        else:
            if not already_configured:
                logging.basicConfig(
                    level=_resolved_level,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                )
            else:
                root.setLevel(_resolved_level)

        # Install safe LogRecordFactory here as well (in case enhanced_rag not imported yet)
        try:
            import logging as _pylogging
            current_factory = _pylogging.getLogRecordFactory()
            # If factory doesn't exist or isn't our safe wrapper, install a guard that prevents 'message' overwrite
            def _guard_factory(*args, **kwargs):
                rec = current_factory(*args, **kwargs) if current_factory else logging.LogRecord(*args, **kwargs)  # type: ignore[arg-type]
                # Ensure 'message' is consistent with msg/args
                try:
                    rec.message = rec.getMessage()
                except Exception:
                    rec.message = str(getattr(rec, "msg", ""))
                return rec
            # Only set if not already a guard (simple duck check)
            if getattr(current_factory, "__name__", "") != "_guard_factory":
                _pylogging.setLogRecordFactory(_guard_factory)
        except Exception:
            # Never fail startup due to logging factory issues
            pass

        # Initialize MCP
        self.mcp = FastMCP(self.name)

        # Get RAG configuration
        self.rag_config = config

        # Initialize components
        self._init_components()

        # Track if async components have been started
        self._async_components_started = False

        # Initialize transport wrapper for unified auth
        from .mcp.transport_wrapper import TransportWrapper
        self.transport_wrapper = TransportWrapper(self)
        
        # Register MCP endpoints
        from .mcp import register_tools, register_resources, register_prompts

        # Register tools through transport wrapper for auth enforcement
        register_tools(cast(Any, self.mcp), self)
        register_resources(self.mcp, self)
        register_prompts(self.mcp)

        logger.info(
            f"MCP Server initialized - Features: "
            f"RAG={ENHANCED_RAG_AVAILABLE}, "
            f"Vector={VECTOR_SUPPORT}, "
            f"Pipeline={PIPELINE_AVAILABLE}, "
            f"REST_API={REST_API_SUPPORT}"
        )

    def _init_components(self):
        """Initialize enhanced_rag components."""
        # Initialize search tools if available - each component independently
        self.enhanced_search = None
        if ENHANCED_SEARCH_AVAILABLE:
            try:
                self.enhanced_search = EnhancedSearchTool(self.rag_config)  # type: ignore[call-arg]
            except Exception as e:
                logger.warning("EnhancedSearchTool unavailable; continuing without enhanced search: %s", e)

        self.code_gen = None
        if CODE_GEN_AVAILABLE:
            try:
                self.code_gen = CodeGenerationTool(self.rag_config)  # type: ignore[call-arg]
            except Exception as e:
                logger.warning("CodeGenerationTool unavailable; generation tools disabled: %s", e)

        self.context_aware = None
        if CONTEXT_AWARE_AVAILABLE:
            try:
                self.context_aware = ContextAwareTool(self.rag_config)  # type: ignore[call-arg]
            except Exception as e:
                logger.warning("ContextAwareTool unavailable; context-aware features disabled: %s", e)

        # Initialize basic Azure Search as fallback
        # Guard against partially available Azure SDK imports where AzureKeyCredential could be None
        if (
            AZURE_SDK_AVAILABLE
            and AzureKeyCredential is not None
            and SearchClient is not None
            and bool(config.azure.endpoint and config.azure.endpoint.strip())
        ):
            # Choose key: admin if available
            api_key = config.azure.admin_key.strip()
            if api_key:
                try:
                    # Construct credential only after verifying the symbol is available
                    azure_key_credential = AzureKeyCredential(api_key)  # type: ignore[call-arg]
                    self.search_client = SearchClient(
                        endpoint=str(config.azure.endpoint),
                        index_name=str(config.azure.index_name),
                        credential=azure_key_credential,
                    )  # type: ignore[call-arg]
                except TypeError as e:
                    # Common in type-checkers when symbol resolution fails; hard-disable SDK path
                    logger.warning(f"Azure SDK credential construction failed (TypeError). Disabling SDK fallback. Error: {e}")
                    self.search_client = None
                except Exception as e:
                    logger.warning(f"Azure SearchClient initialization failed, disabling SDK fallback: {e}")
                    self.search_client = None
            else:
                self.search_client = None
        else:
            self.search_client = None

        # Initialize pipeline if available
        # RAGPipeline expects a dict-like config; pass server.rag_config with model_updater
        self.pipeline = None
        if PIPELINE_AVAILABLE:
            try:
                pipeline_config = self.rag_config.copy()
                # Wire up adaptive ranking and ModelUpdater if learning support is available
                if LEARNING_SUPPORT:
                    # Initialize model_updater first since pipeline needs it
                    self.model_updater = ModelUpdater()  # type: ignore[call-arg]
                    pipeline_config["model_updater"] = self.model_updater
                    pipeline_config["adaptive_ranking"] = True

                # Enable ranking monitoring for the improved ranker
                if "ranking" not in pipeline_config:
                    pipeline_config["ranking"] = {}
                pipeline_config["ranking"]["enable_monitoring"] = True

                self.pipeline = RAGPipeline(pipeline_config)  # type: ignore[call-arg]
            except Exception as e:
                logger.warning("RAGPipeline initialization failed; continuing without pipeline: %s", e)

        # Initialize semantic tools
        if SEMANTIC_SUPPORT:
            self.intent_classifier = IntentClassifier()  # type: ignore[call-arg]
            self.query_enhancer = ContextualQueryEnhancer()  # type: ignore[call-arg]
            self.query_rewriter = MultiVariantQueryRewriter()  # type: ignore[call-arg]
        else:
            self.intent_classifier = None
            self.query_enhancer = None
            self.query_rewriter = None

        # Initialize ranking tools
        if RANKING_SUPPORT:
            self.result_explainer = cast(Any, ResultExplainer)()
        else:
            self.result_explainer = None

        # Initialize cache manager
        if CACHE_SUPPORT:
            self.cache_manager = CacheManager(
                ttl=config.cache_ttl_seconds, max_size=config.cache_max_entries
            )  # type: ignore[call-arg]
        else:
            self.cache_manager = None

        # Initialize learning components
        if LEARNING_SUPPORT:
            self.feedback_collector = FeedbackCollector(
                storage_path=str(config.feedback_dir)
            )  # type: ignore[call-arg]
            self.usage_analyzer = UsageAnalyzer(
                feedback_collector=self.feedback_collector
            )  # type: ignore[call-arg]
            # model_updater initialized above for pipeline
        else:
            self.feedback_collector = None
            self.usage_analyzer = None
            self.model_updater = None

        # ------------------------------------------------------------------
        # ADMIN COMPONENTS (REST-BASED)
        # ------------------------------------------------------------------
        # The original SDK based admin helpers have been superseded by the REST
        # automation layer.  We now rely on those helpers when available.

        # Initialize GitHub integration
        if GITHUB_SUPPORT:
            try:
                self.github_client = GitHubClient()  # type: ignore[call-arg]
                self.remote_indexer = RemoteIndexer()  # type: ignore[call-arg]
            except Exception:
                # Disable GitHub integration if imports or setup fail in this environment
                self.github_client = None
                self.remote_indexer = None
        else:
            self.github_client = None
            self.remote_indexer = None

        # Initialize REST API automation components
        if REST_API_SUPPORT:
            try:
                # Create REST client and operations
                self.rest_client = AzureSearchClient(
                    endpoint=config.acs_endpoint,
                    api_key=config.acs_admin_key.get_secret_value() if config.acs_admin_key else ""
                )  # type: ignore[call-arg]
                self.rest_ops = SearchOperations(self.rest_client)  # type: ignore[call-arg]

                # Initialize automation managers
                self.index_automation = IndexAutomation(
                    endpoint=config.acs_endpoint,
                    api_key=config.acs_admin_key.get_secret_value() if config.acs_admin_key else ""
                )  # type: ignore[call-arg]
                self.data_automation = DataAutomation(self.rest_ops)  # type: ignore[call-arg]
                self.indexer_automation = IndexerAutomation(self.rest_ops)  # type: ignore[call-arg]
                self.health_monitor = HealthMonitor(self.rest_ops)  # type: ignore[call-arg]

                logger.info("REST API automation components initialized")
            except Exception as e:
                logger.warning(f"REST API components unavailable: {e}")
                self.rest_client = None
                self.rest_ops = None
                self.index_automation = None
                self.data_automation = None
                self.indexer_automation = None
                self.health_monitor = None
        else:
            self.rest_client = None
            self.rest_ops = None
            self.index_automation = None
            self.data_automation = None
            self.indexer_automation = None
            self.health_monitor = None

    async def ensure_async_components_started(self):
        """
        Ensure async components are started. This is called lazily when needed.
        """
        if not self._async_components_started:
            await self.start_async_components()
            self._async_components_started = True

    async def start_async_components(self):
        """
        Start async components that require an event loop.
        This should be called when an event loop is available.
        """
        try:
            # Start RAGPipeline async components
            if self.pipeline is not None:
                await self.pipeline.start()
                logger.info("✅ RAGPipeline async components started")

            # Start feedback collector if it exists and wasn't started by pipeline
            if (
                self.feedback_collector is not None
                and hasattr(self.feedback_collector, "is_started")
                and not self.feedback_collector.is_started()
            ):
                await self.feedback_collector.start()
                logger.info("✅ FeedbackCollector async components started")

            logger.info("✅ All MCP Server async components started successfully")

        except Exception as e:
            logger.error(f"❌ Failed to start MCP Server async components: {e}")
            raise

    async def cleanup_async_components(self):
        """
        Clean up async components.
        """
        try:
            # Cleanup RAGPipeline
            if self.pipeline is not None and hasattr(self.pipeline, "cleanup"):
                await self.pipeline.cleanup()

            # Cleanup feedback collector if it exists separately
            if self.feedback_collector is not None and hasattr(
                self.feedback_collector, "cleanup"
            ):
                await self.feedback_collector.cleanup()

            # Cleanup REST API client
            if self.rest_client is not None:
                await self.rest_client.close()

            # Cleanup index automation client
            if self.index_automation is not None and hasattr(self.index_automation, "client"):
                await self.index_automation.client.close()

            logger.info("✅ MCP Server async components cleanup completed")

        except Exception as e:
            logger.error(f"❌ Error during MCP Server async cleanup: {e}")

    def run(self, transport: Literal["stdio", "sse", "streamable-http"] = "stdio"):
        """Run the MCP server."""
        if transport == "stdio":
            apply_patches()

        logger.info(f"Starting MCP server in {transport} mode")

        # For stdio mode, start async components synchronously to ensure they're ready
        import asyncio
        
        if transport == "stdio":
            # In stdio mode, ensure components are started before handling requests
            try:
                asyncio.run(self.start_async_components())
                logger.info("Async components started successfully in stdio mode")
            except Exception as e:
                logger.error(f"Failed to start async components: {e}")
                # Continue anyway as some functionality may still work
        else:
            # For other transports, schedule async startup
            async def _startup_task():
                """Start async components after event loop is running"""
                try:
                    await self.start_async_components()
                except Exception as e:
                    logger.error(f"Failed to start async components: {e}")

            # Schedule the startup task to run after the event loop starts
            def schedule_startup():
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(_startup_task())
                except RuntimeError:
                    # No event loop running yet, try to schedule for later
                    logger.warning(
                        "No event loop available yet for async component startup"
                    )

            # Try to schedule startup immediately, or wait for event loop
            try:
                schedule_startup()
            except Exception:
                # If we can't schedule immediately, we'll try during the first tool call
                logger.debug("Will start async components on first tool usage")

        self.mcp.run(transport=transport)

    async def get_ranking_metrics(self, time_window_hours: int = 24) -> Dict[str, Any]:
        """Get ranking performance metrics from the pipeline."""
        if self.pipeline and hasattr(self.pipeline, 'get_ranking_performance_report'):
            return await self.pipeline.get_ranking_performance_report(time_window_hours)
        else:
            return {"error": "Ranking metrics not available"}


def create_server() -> MCPServer:
    """Create and return an MCP server instance."""
    return MCPServer()


def main():
    """Main entry point."""
    server = create_server()
    server.run()


if __name__ == "__main__":
    main()
