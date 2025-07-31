"""
Main RAG Pipeline Orchestrator
Coordinates all enhanced RAG components for optimal code search
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from .core.models import SearchQuery, SearchResult, CodeContext
from .core.config import get_config
from .context.hierarchical_context import HierarchicalContextAnalyzer
from .semantic.query_enhancer import ContextualQueryEnhancer
from .semantic.intent_classifier import IntentClassifier
from .retrieval.multi_stage_pipeline import MultiStageRetriever
from .ranking.contextual_ranker import ContextualRanker
from .ranking.result_explainer import ResultExplainer
from .generation.response_generator import ResponseGenerator
from .utils.performance_monitor import PerformanceMonitor
from .utils.error_handler import ErrorHandler

logger = logging.getLogger(__name__)


class QueryContext:
    """Context for a search query"""
    def __init__(
        self,
        current_file: Optional[str] = None,
        workspace_root: Optional[str] = None,
        session_id: Optional[str] = None,
        user_preferences: Optional[Dict[str, Any]] = None
    ):
        self.current_file = current_file
        self.workspace_root = workspace_root
        self.session_id = session_id
        self.user_preferences = user_preferences or {}


class RAGPipelineResult:
    """Result from RAG pipeline processing"""
    def __init__(
        self,
        success: bool,
        results: List[SearchResult],
        response: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ):
        self.success = success
        self.results = results
        self.response = response
        self.metadata = metadata or {}
        self.error = error


class RAGPipeline:
    """
    Main RAG Pipeline that orchestrates all enhanced RAG components

    This class coordinates:
    1. Context analysis and extraction
    2. Query enhancement and intent classification
    3. Multi-stage retrieval
    4. Intelligent ranking and filtering
    5. Response generation
    6. Learning and feedback collection
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or get_config()
        self.performance_monitor = PerformanceMonitor()
        self.error_handler = ErrorHandler()

        # Initialize components
        self._initialize_components()

        # Component cache for performance
        self._context_cache: Dict[str, CodeContext] = {}
        self._session_contexts: Dict[str, Dict[str, Any]] = {}

    def _initialize_components(self):
        """Initialize all RAG pipeline components"""
        try:
            # Core components
            self.context_analyzer = HierarchicalContextAnalyzer(self.config.get('context', {}))
            self.query_enhancer = ContextualQueryEnhancer(self.config.get('semantic', {}))
            self.intent_classifier = IntentClassifier(self.config.get('semantic', {}))
            self.retriever = MultiStageRetriever(self.config.get('retrieval', {}))
            self.ranker = ContextualRanker(self.config.get('ranking', {}))
            self.result_explainer = ResultExplainer(self.config.get('ranking', {}))
            self.feedback_collector = LearningCollector(self.config.get('learning', {}))
            self.response_generator = ResponseGenerator(self.config.get('generation', {}))

            logger.info("✅ RAG Pipeline components initialized successfully")

        except Exception as e:
            logger.error(f"❌ Failed to initialize RAG Pipeline: {e}")
            raise

    async def process_query(
        self,
        query: str,
        context: QueryContext,
        generate_response: bool = True,
        max_results: int = 10
    ) -> RAGPipelineResult:
        """
        Process a search query through the complete RAG pipeline

        Args:
            query: The search query
            context: Query context information
            generate_response: Whether to generate a natural language response
            max_results: Maximum number of results to return

        Returns:
            RAGPipelineResult with search results and optional response
        """
        start_time = datetime.utcnow()

        try:
            # 1. Extract and analyze context
            code_context = await self._extract_context(context)

            # 2. Classify intent and enhance query
            intent = await self.intent_classifier.classify_intent(query)

            # Handle case where context is None
            if code_context:
                enhanced_queries = await self.query_enhancer.enhance_query(
                    query, code_context, intent.value
                )
            else:
                enhanced_queries = [query]  # Fallback to original query

            # 3. Build search query object
            search_query = SearchQuery(
                query=query,
                intent=intent,
                current_file=context.current_file,
                language=code_context.language if code_context else None,
                framework=code_context.framework if code_context else None,
                user_id=context.session_id
            )

            # 4. Execute multi-stage retrieval (simplified for now)
            # TODO: Implement proper multi-stage retrieval
            raw_results = []  # Placeholder

            # 5. Rank and filter results (simplified for now)
            # TODO: Implement proper ranking
            ranked_results = raw_results

            # 6. Limit results and add explanations
            final_results = ranked_results[:max_results]
            for result in final_results:
                explanation = await self.result_explainer.explain_ranking(
                    result, search_query, code_context
                )
                result.relevance_explanation = explanation.get('explanation', '')

            # 7. Generate response if requested
            response_text = None
            if generate_response and final_results:
                # Simplified response generation for now
                response_text = f"Found {len(final_results)} relevant results for '{query}'"

            # 8. Skip feedback collection for now (simplified)

            # 9. Build metadata
            metadata = {
                'intent': intent.value,
                'enhanced_queries': enhanced_queries,
                'total_results_found': len(raw_results),
                'processing_time_ms': (datetime.utcnow() - start_time).total_seconds() * 1000,
                'context_used': bool(code_context),
                'session_id': context.session_id
            }

            return RAGPipelineResult(
                success=True,
                results=final_results,
                response=response_text,
                metadata=metadata
            )

        except Exception as e:
            error_msg = await self.error_handler.handle_error(e, {
                'query': query,
                'context': context.__dict__,
                'pipeline_stage': 'process_query'
            })

            logger.error(f"❌ RAG Pipeline error: {error_msg}")

            return RAGPipelineResult(
                success=False,
                results=[],
                error=error_msg,
                metadata={'processing_time_ms': (datetime.utcnow() - start_time).total_seconds() * 1000}
            )

    async def _extract_context(self, query_context: QueryContext) -> Optional[CodeContext]:
        """Extract code context from query context"""
        if not query_context.current_file:
            return None

        # Check cache first
        cache_key = f"{query_context.current_file}:{query_context.workspace_root}"
        if cache_key in self._context_cache:
            return self._context_cache[cache_key]

        try:
            # Extract context using hierarchical analyzer
            context = await self.context_analyzer.get_context(
                query_context.current_file,
                open_files=[],  # Could be enhanced with actual open files
                recent_edits=[]  # Could be enhanced with recent edits
            )

            # Cache the context
            self._context_cache[cache_key] = context
            return context

        except Exception as e:
            logger.warning(f"⚠️ Failed to extract context: {e}")
            return None

    async def _record_interaction(
        self,
        query: SearchQuery,
        results: List[SearchResult],
        context: Optional[CodeContext]
    ):
        """Record interaction for learning purposes"""
        try:
            await self.feedback_collector.record_interaction(
                query, results, context, "search_completed"
            )
        except Exception as e:
            logger.warning(f"⚠️ Failed to record interaction: {e}")

    async def get_session_context(self, session_id: str) -> Dict[str, Any]:
        """Get accumulated context for a session"""
        return self._session_contexts.get(session_id, {})

    async def update_session_context(
        self,
        session_id: str,
        context_update: Dict[str, Any]
    ):
        """Update session context with new information"""
        if session_id not in self._session_contexts:
            self._session_contexts[session_id] = {}

        self._session_contexts[session_id].update(context_update)

    def get_pipeline_status(self) -> Dict[str, Any]:
        """Get current pipeline status and health"""
        return {
            'components_initialized': True,
            'cache_size': len(self._context_cache),
            'active_sessions': len(self._session_contexts),
            'performance_metrics': self.performance_monitor.get_metrics()
        }
