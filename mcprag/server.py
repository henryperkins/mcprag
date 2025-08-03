"""
MCP Server orchestration.

Initializes and coordinates enhanced_rag modules for MCP access.
"""

import logging
import sys
from typing import Optional, Dict, Any
from pathlib import Path

from .config import Config
from .compatibility.socketpair_patch import apply_patches

# Import what we need from enhanced_rag
try:
    from enhanced_rag.mcp_integration.enhanced_search_tool import EnhancedSearchTool
    from enhanced_rag.mcp_integration.code_gen_tool import CodeGenerationTool
    from enhanced_rag.mcp_integration.context_aware_tool import ContextAwareTool
    ENHANCED_RAG_AVAILABLE = True
except ImportError:
    ENHANCED_RAG_AVAILABLE = False

try:
    from enhanced_rag.azure_integration import AzureOpenAIEmbeddingProvider
    VECTOR_SUPPORT = True
except ImportError:
    VECTOR_SUPPORT = False

try:
    from enhanced_rag.pipeline import RAGPipeline
    PIPELINE_AVAILABLE = True
except ImportError:
    PIPELINE_AVAILABLE = False

try:
    from enhanced_rag.learning.feedback_collector import FeedbackCollector
    from enhanced_rag.learning.usage_analyzer import UsageAnalyzer
    from enhanced_rag.learning.model_updater import ModelUpdater
    LEARNING_SUPPORT = True
except ImportError:
    LEARNING_SUPPORT = False

try:
    from enhanced_rag.azure_integration.index_operations import IndexOperations
    from enhanced_rag.azure_integration.indexer_integration import IndexerIntegration
    from enhanced_rag.azure_integration.document_operations import DocumentOperations
    AZURE_ADMIN_SUPPORT = True
except ImportError:
    AZURE_ADMIN_SUPPORT = False

# GitHub integration pulls in FastAPI app with slowapi limiter that can fail outside web context.
# To avoid import-time side effects for MCP server, guard these imports strictly.
try:
    from enhanced_rag.github_integration.api_client import GitHubClient  # type: ignore
    from enhanced_rag.github_integration.remote_indexer import RemoteIndexer  # type: ignore
    GITHUB_SUPPORT = True
except Exception:
    GITHUB_SUPPORT = False

try:
    from enhanced_rag.semantic.intent_classifier import IntentClassifier
    from enhanced_rag.semantic.query_enhancer import ContextualQueryEnhancer
    from enhanced_rag.semantic.query_rewriter import MultiVariantQueryRewriter
    SEMANTIC_SUPPORT = True
except ImportError:
    SEMANTIC_SUPPORT = False

try:
    from enhanced_rag.ranking.result_explainer import ResultExplainer
    RANKING_SUPPORT = True
except ImportError:
    RANKING_SUPPORT = False

try:
    from enhanced_rag.utils.cache_manager import CacheManager
    CACHE_SUPPORT = True
except ImportError:
    CACHE_SUPPORT = False

# Direct Azure Search for fallback
try:
    from azure.search.documents import SearchClient
    from azure.core.credentials import AzureKeyCredential
    AZURE_SDK_AVAILABLE = True
except ImportError:
    AZURE_SDK_AVAILABLE = False

# MCP SDK
try:
    from mcp.server.fastmcp import FastMCP
    MCP_SDK_AVAILABLE = True
except ImportError:
    MCP_SDK_AVAILABLE = False
    # Fallback for testing
    class FastMCP:
        def __init__(self, name: str):
            self.name = name
        def tool(self):
            return lambda f: f
        def resource(self):
            return lambda f: f
        def prompt(self):
            return lambda f: f
        def run(self, transport: str = 'stdio'):
            print(f"Mock MCP server {self.name} running")

logger = logging.getLogger(__name__)


class MCPServer:
    """MCP Server orchestrating enhanced_rag modules."""

    def __init__(self):
        """Initialize MCP server."""
        self.name = "azure-code-search-enhanced"
        self.version = "3.0.0"

        # Validate configuration
        errors = Config.validate()
        if errors:
            raise ValueError(f"Configuration errors: {errors}")

        # Setup logging
        logging.basicConfig(
            level=getattr(logging, Config.LOG_LEVEL),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        # Initialize MCP
        self.mcp = FastMCP(self.name)

        # Get RAG configuration
        self.rag_config = Config.get_rag_config()

        # Initialize components
        self._init_components()

        # Track if async components have been started
        self._async_components_started = False

        # Register MCP endpoints
        from .mcp import register_tools, register_resources, register_prompts
        register_tools(self.mcp, self)
        register_resources(self.mcp, self)
        register_prompts(self.mcp)

        logger.info(f"MCP Server initialized - Features: "
                   f"RAG={ENHANCED_RAG_AVAILABLE}, "
                   f"Vector={VECTOR_SUPPORT}, "
                   f"Pipeline={PIPELINE_AVAILABLE}")

    def _init_components(self):
        """Initialize enhanced_rag components."""
        # Initialize search tools if available
        if ENHANCED_RAG_AVAILABLE:
            self.enhanced_search = EnhancedSearchTool(self.rag_config)
            self.code_gen = CodeGenerationTool(self.rag_config)
            self.context_aware = ContextAwareTool(self.rag_config)
        else:
            self.enhanced_search = None
            self.code_gen = None
            self.context_aware = None

        # Initialize basic Azure Search as fallback
        if AZURE_SDK_AVAILABLE:
            self.search_client = SearchClient(
                endpoint=Config.ENDPOINT,
                index_name=Config.INDEX_NAME,
                credential=AzureKeyCredential(Config.ADMIN_KEY)
            )
        else:
            self.search_client = None

        # Initialize pipeline if available
        # RAGPipeline expects a dict-like config; pass server.rag_config
        self.pipeline = RAGPipeline(self.rag_config) if PIPELINE_AVAILABLE else None

        # Initialize semantic tools
        if SEMANTIC_SUPPORT:
            self.intent_classifier = IntentClassifier()
            self.query_enhancer = ContextualQueryEnhancer()
            self.query_rewriter = MultiVariantQueryRewriter()
        else:
            self.intent_classifier = None
            self.query_enhancer = None
            self.query_rewriter = None

        # Initialize ranking tools
        self.result_explainer = ResultExplainer() if RANKING_SUPPORT else None

        # Initialize cache manager
        if CACHE_SUPPORT:
            self.cache_manager = CacheManager(
                ttl=Config.CACHE_TTL_SECONDS,
                max_size=Config.CACHE_MAX_ENTRIES
            )
        else:
            self.cache_manager = None

        # Initialize learning components
        if LEARNING_SUPPORT:
            self.feedback_collector = FeedbackCollector(storage_path=str(Config.FEEDBACK_DIR))
            self.usage_analyzer = UsageAnalyzer(feedback_collector=self.feedback_collector)
            self.model_updater = ModelUpdater()
        else:
            self.feedback_collector = None
            self.usage_analyzer = None
            self.model_updater = None

        # Initialize admin components
        if AZURE_ADMIN_SUPPORT and Config.ADMIN_MODE:
            self.index_ops = IndexOperations(
                endpoint=Config.ENDPOINT,
                admin_key=Config.ADMIN_KEY
            )
            self.indexer_integration = IndexerIntegration()
            self.doc_ops = DocumentOperations(
                endpoint=Config.ENDPOINT,
                admin_key=Config.ADMIN_KEY
            )
        else:
            self.index_ops = None
            self.indexer_integration = None
            self.doc_ops = None

        # Initialize GitHub integration
        if GITHUB_SUPPORT and Config.ADMIN_MODE:
            try:
                self.github_client = GitHubClient()
                self.remote_indexer = RemoteIndexer()
            except Exception:
                # Disable GitHub integration if imports or setup fail in this environment
                self.github_client = None
                self.remote_indexer = None
        else:
            self.github_client = None
            self.remote_indexer = None
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
            if (self.feedback_collector is not None and
                hasattr(self.feedback_collector, 'is_started') and
                not self.feedback_collector.is_started()):
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
            if self.pipeline is not None and hasattr(self.pipeline, 'cleanup'):
                await self.pipeline.cleanup()

            # Cleanup feedback collector if it exists separately
            if (self.feedback_collector is not None and
                hasattr(self.feedback_collector, 'cleanup')):
                await self.feedback_collector.cleanup()

            logger.info("✅ MCP Server async components cleanup completed")

        except Exception as e:
            logger.error(f"❌ Error during MCP Server async cleanup: {e}")


    def run(self, transport: str = 'stdio'):
        """Run the MCP server."""
        if transport == 'stdio':
            apply_patches()

        logger.info(f"Starting MCP server in {transport} mode")

        # Start async components in background when event loop is available
        import asyncio

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
                logger.warning("No event loop available yet for async component startup")

        # Try to schedule startup immediately, or wait for event loop
        try:
            schedule_startup()
        except Exception:
            # If we can't schedule immediately, we'll try during the first tool call
            logger.debug("Will start async components on first tool usage")

        self.mcp.run(transport=transport)


def create_server() -> MCPServer:
    """Create and return an MCP server instance."""
    return MCPServer()


def main():
    """Main entry point."""
    server = create_server()
    server.run()


if __name__ == "__main__":
    main()
