"""
Main RAG Pipeline Orchestrator
Coordinates all enhanced RAG components for optimal code search
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

from .core.models import (
    SearchQuery, SearchResult, CodeContext, EnhancedContext
)
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

        # Initialize vector search if enabled
        if self.config.get('retrieval', {}).get('enable_vector_search', True):
            try:
                from .retrieval.hybrid_searcher import HybridSearcher
                self.hybrid_searcher = HybridSearcher(self.config)
                logger.info("✅ Vector search enabled in pipeline")
            except Exception as e:
                logger.warning(f"Vector search initialization failed: {e}")

        # Component cache for performance
        self._context_cache: Dict[str, CodeContext] = {}
        self._session_contexts: Dict[str, Dict[str, Any]] = {}

    def _initialize_components(self):
        """Initialize all RAG pipeline components"""
        try:
            # Core components
            context_config = self.config.get('context', {})
            retrieval_config = self.config.get('retrieval', {})
            ranking_config = self.config.get('ranking', {})

            self.context_analyzer = HierarchicalContextAnalyzer(context_config)
            self.query_enhancer = ContextualQueryEnhancer(retrieval_config)
            self.intent_classifier = IntentClassifier(retrieval_config)
            self.retriever = MultiStageRetriever(retrieval_config)
            
            # Initialize ranking with optional adaptive ranker
            base_ranker = ContextualRanker(ranking_config)
            learning_config = self.config.get('learning', {})
            
            if learning_config.get('enable_adaptive_ranking', False):
                try:
                    from .ranking.adaptive_ranker import AdaptiveRanker
                    from .learning.feedback_collector import FeedbackCollector
                    from .learning.model_updater import ModelUpdater
                    
                    # Initialize feedback collector first
                    self.feedback_collector = FeedbackCollector(
                        storage_path=learning_config.get('feedback_storage_path')
                    )
                    
                    # Initialize model updater
                    model_updater = ModelUpdater(
                        update_frequency=learning_config.get('update_frequency', 'daily')
                    )
                    
                    # Wrap base ranker with adaptive ranker
                    self.ranker = AdaptiveRanker(
                        base_ranker=base_ranker,
                        model_updater=model_updater,
                        feedback_collector=self.feedback_collector,
                        config=learning_config
                    )
                    logger.info("✅ Adaptive ranking enabled")
                except ImportError as e:
                    logger.warning(f"Adaptive ranking not available: {e}")
                    self.ranker = base_ranker
                    self.feedback_collector = None
            else:
                self.ranker = base_ranker
                # Still initialize feedback collector for tracking
                try:
                    from .learning.feedback_collector import FeedbackCollector
                    self.feedback_collector = FeedbackCollector(
                        storage_path=learning_config.get('feedback_storage_path')
                    )
                except ImportError:
                    logger.warning("Learning module not available - feedback collection disabled")
                    self.feedback_collector = None
            
            self.result_explainer = ResultExplainer(ranking_config)
            self.response_generator = ResponseGenerator(
                self.config.get('generation', {})
            )

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
        start_time = datetime.now(timezone.utc)

        try:
            # 1. Extract and analyze context
            code_context = await self._extract_context(context)

            # 2. Classify intent and enhance query
            intent = await self.intent_classifier.classify_intent(query)

            # Handle case where context is None
            if code_context:
                enhancement_result = await self.query_enhancer.enhance_query(
                    query, code_context, intent.value
                )
                enhanced_queries = enhancement_result['queries']
                exclude_terms = enhancement_result['exclude_terms']
            else:
                enhanced_queries = [query]  # Fallback to original query
                exclude_terms = []

            # 3. Build search query object
            search_query = SearchQuery(
                query=query,
                intent=intent,
                current_file=context.current_file,
                language=code_context.language if code_context else None,
                framework=code_context.framework if code_context else None,
                user_id=context.session_id,
                exclude_terms=exclude_terms
            )

            # 4. Execute multi-stage retrieval
            try:
                raw_results = await self.retriever.retrieve(search_query)
                logger.debug(f"Retrieved {len(raw_results)} results from multi-stage retrieval")
                
                # Normalize dict results to SearchResult instances
                if raw_results and isinstance(raw_results[0], dict):
                    from .core.models import SearchResult as CoreSearchResult
                    normalized = []
                    for r in raw_results:
                        normalized.append(CoreSearchResult(
                            id=r.get('id') or r.get('@search.documentId') or '',
                            score=r.get('score') or r.get('@search.score', 0.0),
                            file_path=r.get('file_path', ''),
                            repository=r.get('repository', ''),
                            language=r.get('language', ''),
                            function_name=r.get('function_name'),
                            class_name=r.get('class_name'),
                            code_snippet=r.get('content') or r.get('code_snippet', ''),
                            signature=r.get('signature', ''),
                            semantic_context=r.get('semantic_context', ''),
                            imports=r.get('imports') or [],
                            dependencies=r.get('dependencies') or [],
                            start_line=r.get('start_line'),
                            end_line=r.get('end_line'),
                            highlights=r.get('@search.highlights') or r.get('highlights', {})
                        ))
                    raw_results = normalized
                    
            except Exception as e:
                logger.error(f"Multi-stage retrieval failed: {e}")
                # Fallback to HybridSearcher if available
                if hasattr(self, 'hybrid_searcher') and self.hybrid_searcher:
                    try:
                        logger.info("Falling back to HybridSearcher")
                        hybrid_results = await self.hybrid_searcher.hybrid_search(
                            query=query,
                            top_k=max_results * 2  # Get more results for ranking
                        )
                        # Convert HybridSearchResult to SearchResult
                        raw_results = []
                        for hr in hybrid_results:
                            search_result = SearchResult(
                                id=hr.id,
                                score=hr.score,
                                file_path=hr.metadata.get('file_path', ''),
                                repository=hr.metadata.get('repository', ''),
                                function_name=hr.metadata.get('function_name'),
                                class_name=hr.metadata.get('class_name'),
                                code_snippet=hr.content,
                                language=hr.metadata.get('language', ''),
                                highlights=hr.metadata.get('highlights', {}),
                                signature=hr.metadata.get('signature', ''),  # add
                                semantic_context=hr.metadata.get('semantic_context', ''),  # add
                                imports=hr.metadata.get('imports') or [],  # add
                                dependencies=hr.metadata.get('dependencies') or []  # add
                            )
                            raw_results.append(search_result)
                        logger.info(f"HybridSearcher fallback returned {len(raw_results)} results")
                    except Exception as fallback_error:
                        logger.error(f"HybridSearcher fallback also failed: {fallback_error}")
                        raw_results = []
                else:
                    raw_results = []

            # 5. Rank and filter results
            if raw_results:
                # Optional augmentation to fill missing metadata for better ranking
                self._augment_code_understanding(raw_results)

            if raw_results and code_context:
                try:
                    # Convert CodeContext to EnhancedContext for ranking
                    enhanced_context = EnhancedContext(
                        current_file=code_context.current_file,
                        file_content=code_context.file_content,
                        imports=code_context.imports,
                        functions=code_context.functions,
                        classes=code_context.classes,
                        recent_changes=code_context.recent_changes,
                        git_branch=code_context.git_branch,
                        language=code_context.language,
                        framework=code_context.framework,
                        project_root=code_context.project_root,
                        open_files=code_context.open_files,
                        session_id=code_context.session_id
                    )

                    ranked_results = await self.ranker.rank_results(
                        raw_results, enhanced_context, intent
                    )
                    logger.debug(f"Ranked {len(ranked_results)} results")
                except Exception as e:
                    logger.error(f"Ranking failed: {e}")
                    # Fallback to original results
                    ranked_results = raw_results
            else:
                # No context available or no results, skip ranking
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

            # 8. Record interaction for learning (if available)
            if self.feedback_collector:
                await self._record_interaction(search_query, final_results, code_context)

            # 9. Build metadata
            metadata = {
                'intent': intent.value,
                'enhanced_queries': enhanced_queries,
                'total_results_found': len(raw_results),
                'processing_time_ms': (datetime.now(timezone.utc) - start_time).total_seconds() * 1000,
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
                metadata={'processing_time_ms': (datetime.now(timezone.utc) - start_time).total_seconds() * 1000}
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
        if not self.feedback_collector:
            return

        try:
            # Record the search interaction
            interaction_id = await self.feedback_collector.record_search_interaction(
                query, results, context
            )
            
            # Store interaction ID for potential later feedback
            if hasattr(query, 'user_id') and query.user_id:
                self._session_contexts.setdefault(query.user_id, {})
                self._session_contexts[query.user_id]['last_interaction_id'] = interaction_id
            
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
