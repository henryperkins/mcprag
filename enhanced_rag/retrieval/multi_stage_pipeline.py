"""
Multi-stage retrieval pipeline orchestrating different search strategies
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery, QueryType
from azure.core.credentials import AzureKeyCredential

from ..core.interfaces import Retriever
from ..core.models import SearchQuery, SearchResult, SearchIntent
from ..core.config import get_config
from .hybrid_searcher import HybridSearcher
from .dependency_resolver import DependencyResolver
from .pattern_matcher import PatternMatcher

logger = logging.getLogger(__name__)


class SearchStage(Enum):
    VECTOR = "vector"
    KEYWORD = "keyword"
    SEMANTIC = "semantic"
    PATTERN = "pattern"
    DEPENDENCY = "dependency"


class MultiStageRetriever(Retriever):
    """
    Orchestrates multiple search strategies in parallel and fuses results
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or get_config()
        self.search_clients = self._initialize_clients()
        self.hybrid_searcher = HybridSearcher(config)
        self.dependency_resolver = DependencyResolver(config)
        self.pattern_matcher = PatternMatcher(config)
        self._cache = {}
        
    def _initialize_clients(self) -> Dict[str, SearchClient]:
        """Initialize search clients for different indexes"""
        clients = {}
        
        # Get Azure Search configuration
        endpoint = self.config.azure.endpoint
        admin_key = self.config.azure.admin_key
        credential = AzureKeyCredential(admin_key)
        
        # Initialize clients for different indexes
        index_names = {
            'main': self.config.azure.index_name or 'codebase-mcp-sota',
            'patterns': 'codebase-patterns',
            'dependencies': 'codebase-dependencies'
        }
        
        for key, index_name in index_names.items():
            try:
                clients[key] = SearchClient(
                    endpoint=endpoint,
                    index_name=index_name,
                    credential=credential
                )
            except Exception as e:
                logger.warning(f"Failed to initialize client for {index_name}: {e}")
                
        return clients
        
    async def retrieve(
        self,
        query: SearchQuery,
        stages: Optional[List[SearchStage]] = None
    ) -> List[SearchResult]:
        """
        Execute multi-stage retrieval pipeline
        """
        if stages is None:
            stages = self._select_stages_by_intent(query.intent)
            
        # Execute stages in parallel
        stage_tasks = []
        for stage in stages:
            stage_tasks.append(self._execute_stage(stage, query))
            
        stage_results = await asyncio.gather(*stage_tasks)
        
        # Fuse results using Reciprocal Rank Fusion (RRF)
        fused_results = await self._fuse_results(stage_results, query)
        
        return fused_results
    
    def _select_stages_by_intent(self, intent: SearchIntent) -> List[SearchStage]:
        """Select appropriate search stages based on intent"""
        intent_stages = {
            SearchIntent.IMPLEMENT: [SearchStage.VECTOR, SearchStage.PATTERN, SearchStage.DEPENDENCY],
            SearchIntent.DEBUG: [SearchStage.KEYWORD, SearchStage.SEMANTIC, SearchStage.VECTOR],
            SearchIntent.UNDERSTAND: [SearchStage.SEMANTIC, SearchStage.DEPENDENCY, SearchStage.PATTERN],
            SearchIntent.REFACTOR: [SearchStage.PATTERN, SearchStage.DEPENDENCY, SearchStage.VECTOR],
            SearchIntent.TEST: [SearchStage.PATTERN, SearchStage.KEYWORD],
            SearchIntent.DOCUMENT: [SearchStage.SEMANTIC, SearchStage.KEYWORD]
        }
        return intent_stages.get(intent, [SearchStage.VECTOR, SearchStage.KEYWORD])
    
    async def _execute_stage(
        self,
        stage: SearchStage,
        query: SearchQuery
    ) -> List[Tuple[str, float]]:
        """Execute a single search stage"""
        try:
            if stage == SearchStage.VECTOR:
                return await self._execute_vector_search(query)
            elif stage == SearchStage.KEYWORD:
                return await self._execute_keyword_search(query)
            elif stage == SearchStage.SEMANTIC:
                return await self._execute_semantic_search(query)
            elif stage == SearchStage.PATTERN:
                return await self._execute_pattern_search(query)
            elif stage == SearchStage.DEPENDENCY:
                return await self._execute_dependency_search(query)
            else:
                logger.warning(f"Unknown search stage: {stage}")
                return []
        except Exception as e:
            logger.error(f"Error executing {stage} stage: {e}")
            return []
    
    async def _execute_vector_search(self, query: SearchQuery) -> List[Tuple[str, float]]:
        """Execute vector similarity search"""
        results = await self.hybrid_searcher.vector_search(
            query.query,
            filter_expr=self._build_filter(query),
            top_k=50
        )
        return [(r.id, r.score) for r in results]
    
    async def _execute_keyword_search(self, query: SearchQuery) -> List[Tuple[str, float]]:
        """Execute keyword-based search"""
        results = await self.hybrid_searcher.keyword_search(
            query.query,
            filter_expr=self._build_filter(query),
            top_k=50
        )
        return [(r.id, r.score) for r in results]
    
    async def _execute_semantic_search(self, query: SearchQuery) -> List[Tuple[str, float]]:
        """Execute semantic search with query understanding"""
        if 'main' not in self.search_clients:
            return []
            
        results = self.search_clients['main'].search(
            search_text=query.query,
            query_type=QueryType.SEMANTIC,
            semantic_configuration_name="semantic-config",
            top=50,
            filter=self._build_filter(query)
        )
        
        return [(r['id'], r['@search.score']) for r in results]
    
    async def _execute_pattern_search(self, query: SearchQuery) -> List[Tuple[str, float]]:
        """Execute architectural pattern search"""
        patterns = await self.pattern_matcher.find_patterns(
            query.query,
            context=query.task_context
        )
        return [(p.file_id, p.confidence) for p in patterns]
    
    async def _execute_dependency_search(self, query: SearchQuery) -> List[Tuple[str, float]]:
        """Execute dependency-aware search"""
        deps = await self.dependency_resolver.resolve_dependencies(
            query.query,
            current_file=query.current_file
        )
        return [(d.file_id, d.relevance_score) for d in deps]
    
    def _build_filter(self, query: SearchQuery) -> Optional[str]:
        """Build Azure Search filter expression"""
        filters = []
        
        if query.language:
            filters.append(f"language eq '{query.language}'")
            
        if query.framework:
            filters.append(f"framework eq '{query.framework}'")
            
        return " and ".join(filters) if filters else None
    
    async def _fuse_results(
        self,
        stage_results: List[List[Tuple[str, float]]],
        query: SearchQuery
    ) -> List[SearchResult]:
        """Fuse results from multiple stages using RRF"""
        # RRF implementation
        k = 60  # RRF constant
        doc_scores = {}
        
        for stage_idx, results in enumerate(stage_results):
            for rank, (doc_id, score) in enumerate(results):
                if doc_id not in doc_scores:
                    doc_scores[doc_id] = 0
                # RRF formula: 1/(k+rank)
                doc_scores[doc_id] += 1 / (k + rank + 1)
        
        # Sort by fused score
        sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Convert to SearchResult objects
        final_results = []
        top_k = getattr(query, 'top_k', 20)
        
        for doc_id, fused_score in sorted_docs[:top_k]:
            # Fetch full document details
            result = await self._fetch_document(doc_id)
            if result:
                result.score = fused_score
                final_results.append(result)
            
        return final_results
    
    async def _fetch_document(self, doc_id: str) -> Optional[SearchResult]:
        """Fetch full document details from Azure Search"""
        try:
            if 'main' not in self.search_clients:
                return None
                
            # Try to get from cache first
            if doc_id in self._cache:
                return self._cache[doc_id]
                
            # Fetch from Azure Search
            doc = self.search_clients['main'].get_document(key=doc_id)
            
            # Convert to SearchResult
            result = SearchResult(
                id=doc_id,
                score=0.0,  # Will be updated by caller
                file_path=doc.get('file_path', ''),
                repository=doc.get('repository', ''),
                function_name=doc.get('function_name'),
                class_name=doc.get('class_name'),
                code_snippet=doc.get('content', ''),
                language=doc.get('language', ''),
                start_line=doc.get('start_line'),
                end_line=doc.get('end_line'),
                dependencies=doc.get('imports', []),
                tags=doc.get('tags', []),
                complexity_score=doc.get('complexity_score'),
                test_coverage=doc.get('test_coverage'),
                last_modified=doc.get('last_modified')
            )
            
            # Cache the result
            self._cache[doc_id] = result
            
            return result
            
        except Exception as e:
            logger.error(f"Error fetching document {doc_id}: {e}")
            return None
