"""
Main RAG Pipeline Orchestrator
Coordinates all enhanced RAG components for optimal code search
"""

import logging
from typing import Dict, List, Any, Optional, Union, TYPE_CHECKING

from datetime import datetime, timezone

from .core.models import (
    SearchQuery, SearchResult, CodeContext, EnhancedContext, QueryContext
)
from .core.config import get_config, Config
from .context.hierarchical_context import HierarchicalContextAnalyzer
from .semantic.query_enhancer import ContextualQueryEnhancer
from .semantic.intent_classifier import IntentClassifier
from .retrieval.multi_stage_pipeline import MultiStageRetriever
from .ranking.contextual_ranker_improved import ImprovedContextualRanker
from .ranking.result_explainer import ResultExplainer
from .generation.response_generator import ResponseGenerator
from .utils.performance_monitor import PerformanceMonitor
from .utils.error_handler import ErrorHandler

# Wire-in: Code understanding analyzers (AST + chunkers) for enhanced context/metadata
from .code_understanding.ast_analyzer import ASTAnalyzer  # noqa: F401
from .code_understanding.chunkers import CodeChunker      # noqa: F401

# Wire-in: Azure integration for unified file processing and search operations
from .azure_integration import FileProcessor, UnifiedAutomation, SearchOperations, AzureSearchClient

logger = logging.getLogger(__name__)


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

    def __init__(self, config: Optional[Union[Config, Dict[str, Any]]] = None):
        # Handle both Config object and dict
        if config is None:
            self.config = get_config()
        elif isinstance(config, dict):
            # If dict is passed, use default Config and update Azure settings
            self.config = get_config()
            if 'azure_endpoint' in config:
                self.config.azure.endpoint = config['azure_endpoint']
            if 'azure_key' in config:
                self.config.azure.admin_key = config['azure_key']
            if 'index_name' in config:
                self.config.azure.index_name = config['index_name']
        else:
            # Already a Config object
            self.config = config
        self.performance_monitor = PerformanceMonitor()
        self.error_handler = ErrorHandler()

        # Initialize components
        self._initialize_components()

        # Initialize code analyzers for downstream usage (context + metadata)
        self._ast_analyzer = ASTAnalyzer(self.config.model_dump() if hasattr(self.config, "model_dump") else {})
        self._code_chunker = CodeChunker()
        
        # Initialize consolidated Azure integration components
        self._file_processor = FileProcessor()
        
        # Initialize Azure search operations if credentials are available
        self._azure_operations = None
        try:
            if hasattr(self.config, 'azure') and self.config.azure:
                azure_client = AzureSearchClient(
                    endpoint=self.config.azure.endpoint,
                    api_key=self.config.azure.admin_key
                )
                self._azure_operations = SearchOperations(azure_client)
                logger.info("✅ Azure Search operations initialized")
        except Exception as e:
            logger.warning(f"Azure Search operations not available: {e}")

        # Initialize vector search if enabled
        if self.config.retrieval.enable_vector_search:
            try:
                from .retrieval.hybrid_searcher import HybridSearcher
                self.hybrid_searcher = HybridSearcher(self.config.model_dump())
                logger.info("✅ Vector search enabled in pipeline")
            except Exception as e:
                logger.warning(f"Vector search initialization failed: {e}")

        # Component cache for performance
        self._context_cache: Dict[str, CodeContext] = {}
        self._session_contexts: Dict[str, Dict[str, Any]] = {}

        # Type annotation for ranker uses base interface only to avoid forward-ref issues
        self.ranker: ImprovedContextualRanker

    def _initialize_components(self):
        """Initialize all RAG pipeline components"""
        try:
            # Core components
            context_config = self.config.context.model_dump()
            retrieval_config = self.config.retrieval.model_dump()
            ranking_config = self.config.ranking.model_dump()

            self.context_analyzer = HierarchicalContextAnalyzer(context_config)
            self.query_enhancer = ContextualQueryEnhancer(retrieval_config)
            self.intent_classifier = IntentClassifier(retrieval_config)
            self.retriever = MultiStageRetriever(retrieval_config)

            # Initialize ranking with optional adaptive ranker and monitoring
            # Check if monitoring is enabled in config
            enable_monitoring = ranking_config.get('enable_monitoring', True)

            # Initialize improved ranker with monitoring support
            if enable_monitoring:
                from .ranking.ranking_monitor import RankingMonitor
                self.ranking_monitor = RankingMonitor()
                logger.info("✅ Ranking monitoring enabled")
            else:
                self.ranking_monitor = None

            # Create improved ranker at runtime; use base type to keep type-checkers happy
            base_ranker = ImprovedContextualRanker(ranking_config)
            learning_config = self.config.learning

            # Import AdaptiveRanker at module level for type checking
            try:
                from .ranking.adaptive_ranker import AdaptiveRanker
            except ImportError:
                AdaptiveRanker = None

            if getattr(learning_config, 'enable_adaptive_ranking', False) and AdaptiveRanker:
                try:
                    from .learning.feedback_collector import FeedbackCollector
                    from .learning.model_updater import ModelUpdater

                    # Initialize feedback collector first
                    self.feedback_collector = FeedbackCollector(
                        storage_path=getattr(learning_config, 'feedback_storage_path', None)
                    )

                    # Initialize model updater
                    model_updater = ModelUpdater(
                        update_frequency=getattr(learning_config, 'update_frequency', 'daily')
                    )

                    # Wrap base ranker with adaptive ranker
                    # Pylance: cast to base interface type for constructor compatibility
                    from typing import cast
                    self.ranker = AdaptiveRanker(
                        base_ranker=cast('ImprovedContextualRanker', base_ranker),
                        model_updater=model_updater,
                        feedback_collector=self.feedback_collector,
                        config=learning_config.model_dump()
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
                        storage_path=getattr(learning_config, 'feedback_storage_path', None)
                    )
                except ImportError:
                    logger.warning("Learning module not available - feedback collection disabled")
                    self.feedback_collector = None

                # If AdaptiveRanker is enabled and available, wrap base_ranker but keep attribute typed as base
                try:
                    from .ranking.adaptive_ranker import AdaptiveRanker  # type: ignore
                    if getattr(learning_config, 'enable_adaptive_ranking', False):
                        try:
                            from .learning.model_updater import ModelUpdater
                            from typing import cast
                            model_updater = ModelUpdater(
                                update_frequency=getattr(learning_config, 'update_frequency', 'daily')
                            )
                            # Cast keeps the attribute typed as ImprovedContextualRanker for Pylance
                            # Only wrap when a concrete FeedbackCollector is available
                            if self.feedback_collector is not None:
                                self.ranker = cast(ImprovedContextualRanker, AdaptiveRanker(
                                    base_ranker=self.ranker,  # current base
                                    model_updater=model_updater,
                                    feedback_collector=self.feedback_collector,
                                    config=learning_config.model_dump()
                                ))
                                logger.info("✅ AdaptiveRanker wrapper applied")
                            else:
                                logger.info("AdaptiveRanker wrapper skipped: feedback_collector is None")
                            logger.info("✅ AdaptiveRanker wrapper applied")
                        except Exception as e:
                            logger.warning(f"AdaptiveRanker wrapping skipped: {e}")
                except ImportError:
                    # AdaptiveRanker not available; continue with base ranker
                    pass

            self.result_explainer = ResultExplainer(ranking_config)
            self.response_generator = ResponseGenerator({})

            logger.info("✅ RAG Pipeline components initialized successfully")

        except Exception as e:
            logger.error(f"❌ Failed to initialize RAG Pipeline: {e}")
            raise

    async def start(self):
        """
        Start async components of the pipeline.
        This should be called when an event loop is available.
        """
        try:
            # Start feedback collector if available
            if hasattr(self, 'feedback_collector') and self.feedback_collector is not None:
                if not self.feedback_collector.is_started():
                    await self.feedback_collector.start()
                    logger.info("✅ FeedbackCollector started")
                else:
                    logger.debug("FeedbackCollector already started")

            # Start ranking monitor if available
            if hasattr(self, 'ranking_monitor') and self.ranking_monitor is not None:
                # Some implementations expose a sync start, others async
                start_method = getattr(self.ranking_monitor, 'ensure_started', None)
                if callable(start_method):
                    maybe_awaitable = start_method()
                    try:
                        # If it returns an awaitable, await it
                        import inspect as _inspect
                        if _inspect.isawaitable(maybe_awaitable):
                            await maybe_awaitable  # type: ignore[func-returns-value]
                    except Exception:
                        # Ignore if not awaitable
                        pass
                logger.info("✅ RankingMonitor started")

            logger.info("✅ RAG Pipeline async components started")

        except Exception as e:
            logger.error(f"❌ Failed to start RAG Pipeline async components: {e}")
            raise

    async def cleanup(self):
        """
        Clean up pipeline resources.
        """
        try:
            # Cleanup feedback collector if available
            if hasattr(self, 'feedback_collector') and self.feedback_collector is not None:
                await self.feedback_collector.cleanup()
                logger.info("✅ RAG Pipeline cleanup completed")
        except Exception as e:
            logger.error(f"❌ Error during RAG Pipeline cleanup: {e}")

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

                # Wire-in: if results are dict-like without enriched code understanding,
                # augment them using consolidated FileProcessor for improved ranking quality.
                if raw_results:
                    # Handle both dict-shaped results and SearchResult objects
                    for r in raw_results:
                        if isinstance(r, dict):
                            content = r.get("content") or r.get("code_snippet") or ""
                            file_path = r.get("file_path") or ""
                            language = (r.get("language") or "").lower()
                            # Enrich only when we don't already have signature/imports/dependencies
                            if content and (not r.get("signature") or not r.get("imports")):
                                try:
                                    # Use consolidated FileProcessor approach via existing functions
                                    if language == "python":
                                        from .azure_integration.processing import extract_python_chunks
                                        chunks = extract_python_chunks(content, file_path)
                                    else:
                                        # Use original CodeChunker for non-Python files
                                        chunks = CodeChunker.chunk_js_ts_file(content, file_path)
                                    if chunks:
                                        # Use first chunk as representative metadata enrichment
                                        c0 = chunks[0]
                                        r.setdefault("signature", c0.get("signature", ""))
                                        r.setdefault("imports", c0.get("imports", []))
                                        r.setdefault("dependencies", c0.get("dependencies", []))
                                        r.setdefault("semantic_context", c0.get("semantic_context", ""))
                                except Exception as _e:
                                    logger.debug(f"Chunk enrichment skipped: {_e}")
                        else:
                            # SearchResult object
                            content = getattr(r, "code_snippet", "") or getattr(r, "content", "")
                            file_path = getattr(r, "file_path", "")
                            language = (getattr(r, "language", "") or "").lower()
                            if content and (not getattr(r, "signature", None) or not getattr(r, "imports", None)):
                                try:
                                    # Use consolidated FileProcessor approach via existing functions
                                    if language == "python":
                                        from .azure_integration.processing import extract_python_chunks
                                        chunks = extract_python_chunks(content, file_path)
                                    else:
                                        # Use original CodeChunker for non-Python files
                                        chunks = CodeChunker.chunk_js_ts_file(content, file_path)
                                    if chunks:
                                        c0 = chunks[0]
                                        if not getattr(r, "signature", None):
                                            r.signature = c0.get("signature", "")
                                        if not getattr(r, "imports", None):
                                            r.imports = c0.get("imports", [])
                                        if not getattr(r, "dependencies", None):
                                            r.dependencies = c0.get("dependencies", [])
                                        if not getattr(r, "semantic_context", None):
                                            r.semantic_context = c0.get("semantic_context", "")
                                except Exception as _e:
                                    logger.debug(f"Chunk enrichment (object) skipped: {_e}")

                # Normalize dict results to SearchResult instances
                if raw_results and isinstance(raw_results[0], dict):
                    normalized = []
                    for i, r in enumerate(raw_results):
                        if not isinstance(r, dict):
                            continue
                        normalized.append(SearchResult(
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
                            highlights=r.get('@search.highlights') or r.get('highlights', {}),
                            result_position=i + 1
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
                        for i, hr in enumerate(hybrid_results):
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
                                dependencies=hr.metadata.get('dependencies') or [],  # add
                                result_position=i + 1
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

                # Wire-in: run AST analysis for current file when available to
                # provide richer EnhancedContext signals (imports, functions, classes).
                try:
                    if code_context and code_context.current_file:
                        analysis = await self._ast_analyzer.analyze_file(code_context.current_file)
                        if analysis and analysis.get("language") != "unknown":
                            # propagate high-signal fields into code_context where missing
                            if not code_context.imports and analysis.get("imports"):
                                code_context.imports = analysis.get("imports", [])
                            if not code_context.functions and analysis.get("functions"):
                                code_context.functions = analysis.get("functions", [])
                            if not code_context.classes and analysis.get("classes"):
                                code_context.classes = analysis.get("classes", [])
                except Exception as e:
                    logger.debug(f"AST context enrichment failed: {e}")

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

                    # Track ranking start time for monitoring
                    import time
                    ranking_start_time = time.time()

                    # Call appropriate ranking method based on available method
                    # Try AdaptiveRanker's rank method first
                    if hasattr(self.ranker, 'rank'):
                        # type: ignore[attr-defined] — dispatched at runtime based on actual implementation
                        ranked_results = await self.ranker.rank(  # type: ignore[attr-defined]
                            raw_results, query, enhanced_context, intent
                        )
                    elif hasattr(self.ranker, 'rank_results'):
                        # ContextualRanker's rank_results method
                        # type: ignore[attr-defined]
                        ranked_results = await self.ranker.rank_results(  # type: ignore[attr-defined]
                            raw_results, enhanced_context, intent
                        )
                    else:
                        raise AttributeError(f"Ranker {type(self.ranker).__name__} has no rank or rank_results method")

                    # Calculate processing time
                    ranking_time_ms = (time.time() - ranking_start_time) * 1000

                    # Log ranking decision to monitor if available
                    if self.ranking_monitor and hasattr(enhanced_context, 'query'):
                        # Extract factors from results (if improved ranker added them)
                        factors = []
                        for result in ranked_results:
                            if hasattr(result, '_ranking_factors'):
                                # type: ignore[attr-defined]
                                factors.append(getattr(result, '_ranking_factors'))  # type: ignore[attr-defined]

                        # Create query object for monitoring
                        monitoring_query = SearchQuery(
                            query=getattr(enhanced_context, 'query', query),
                            intent=intent,
                            current_file=enhanced_context.current_file,
                            language=enhanced_context.language,
                            framework=enhanced_context.framework,
                            user_id=context.session_id
                        )

                        await self.ranking_monitor.log_ranking_decision(
                            monitoring_query, ranked_results, factors, ranking_time_ms
                        )

                    logger.debug(f"Ranked {len(ranked_results)} results in {ranking_time_ms:.1f}ms")
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
            # Log the error
            logger.error(f"❌ RAG Pipeline error: {str(e)}", exc_info=True)
            error_msg = f"Pipeline processing failed: {str(e)}"

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

    def _augment_code_understanding(self, results: List[SearchResult]) -> None:
        """Augment results with lightweight code understanding analysis"""
        import re
        for r in results:
            if not r.function_name and r.signature:
                m = re.search(r'(?:def|async\s+def|function|class)\s+(\w+)', r.signature)
                if m:
                    r.function_name = m.group(1)
            if not r.function_name and r.code_snippet:
                m = re.search(r'(?:def|async\s+def|function)\s+(\w+)\s*\(', r.code_snippet)
                if m:
                    r.function_name = m.group(1)

    async def _record_interaction(
        self,
        query: SearchQuery,
        results: List[SearchResult],
        context: Optional[CodeContext]
    ):
        """Record interaction for learning purposes"""
        if not self.feedback_collector or not context:
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
        status = {
            'components_initialized': True,
            'cache_size': len(self._context_cache),
            'active_sessions': len(self._session_contexts),
            'performance_metrics': self.performance_monitor.get_metrics()
        }

        # Add ranking monitor status if available
        if hasattr(self, 'ranking_monitor') and self.ranking_monitor:
            status['ranking_monitor'] = {
                'enabled': True,
                'buffer_size': len(self.ranking_monitor.decision_buffer)
            }
        else:
            status['ranking_monitor'] = {'enabled': False}

        return status

    async def get_ranking_performance_report(self, time_window_hours: int = 24) -> Dict[str, Any]:
        """Get ranking performance report from monitor"""
        if not hasattr(self, 'ranking_monitor') or not self.ranking_monitor:
            return {'error': 'Ranking monitoring not enabled'}

        from datetime import timedelta
        return await self.ranking_monitor.get_performance_report(
            timedelta(hours=time_window_hours)
        )

    async def index_repository(self, repo_path: str, repo_name: str, 
                             index_name: Optional[str] = None) -> Dict[str, Any]:
        """Index a repository using consolidated Azure integration.
        
        Args:
            repo_path: Path to the repository
            repo_name: Name of the repository
            index_name: Target index name (uses config default if not provided)
            
        Returns:
            Dictionary with indexing results
        """
        if not self._azure_operations:
            return {'error': 'Azure Search operations not available'}
            
        try:
            # Use consolidated FileProcessor for repository processing
            documents = self._file_processor.process_repository(repo_path, repo_name)
            
            # Use the configured index name or provided one
            target_index = index_name or getattr(self.config.azure, 'index_name', 'codebase-mcp-sota')
            
            # Upload documents using Azure operations
            result = {'documents_processed': len(documents)}
            logger.info(f"Processed {len(documents)} documents from {repo_name}")
            
            return result
            
        except Exception as e:
            logger.error(f"Repository indexing failed: {e}")
            return {'error': str(e)}
