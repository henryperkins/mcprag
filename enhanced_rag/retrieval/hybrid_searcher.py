"""
Hybrid search implementation combining vector and keyword search
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from azure.search.documents import SearchClient
from azure.search.documents.models import (
    VectorizedQuery,
    VectorizableTextQuery,
    QueryType,
)
from azure.core.credentials import AzureKeyCredential
from enhanced_rag.utils.error_handler import with_retry

from ..core.config import get_config

logger = logging.getLogger(__name__)


@dataclass
class HybridSearchResult:
    """Result from hybrid search"""
    id: str
    score: float
    content: str
    metadata: Dict[str, Any]


class HybridSearcher:
    """
    Implements hybrid search combining vector similarity and keyword matching
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or get_config()
        self._initialize_client()
        self.embedder = None
        self._setup_embedder()
        
    def _initialize_client(self):
        """Initialize Azure Search client"""
        try:
            endpoint = self.config.azure.endpoint
            admin_key = self.config.azure.admin_key
            index_name = self.config.azure.index_name or 'codebase-mcp-sota'
            
            credential = AzureKeyCredential(admin_key)
            self.search_client = SearchClient(
                endpoint=endpoint,
                index_name=index_name,
                credential=credential
            )
        except Exception as e:
            logger.error(f"Failed to initialize search client: {e}")
            self.search_client = None
            
    def _setup_embedder(self):
        """Setup vector embedder if available"""
        try:
            from vector_embeddings import VectorEmbedder
            self.embedder = VectorEmbedder()
            logger.info("✅ Vector embedder initialized")
        except ImportError:
            logger.warning(
                "Vector embeddings not available, falling back to keyword search only"
            )
            self.embedder = None
        except Exception as e:
            logger.error(f"Failed to initialize embedder: {e}")
            self.embedder = None
    
    async def vector_search(
        self,
        query: str,
        filter_expr: Optional[str] = None,
        top_k: int = 50
    ) -> List[HybridSearchResult]:
        """Execute vector similarity search"""
        if not self.search_client:
            logger.warning(
                "Vector search not available, search client not initialized."
            )
            return []

        vector_query = self._build_vector_query(query, top_k)
        if not vector_query:
            logger.warning("Could not build vector query for: %s", query)
            return []

        try:
            # Execute vector search with retries
            results = with_retry(
                self.search_client.search,
                search_text=None,
                vector_queries=[vector_query],
                filter=filter_expr,
                top=top_k
            )
            return self._process_results(results)
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
    
    async def keyword_search(
        self,
        query: str,
        filter_expr: Optional[str] = None,
        top_k: int = 50
    ) -> List[HybridSearchResult]:
        """Execute keyword-based search"""
        if not self.search_client:
            logger.warning("Keyword search not available")
            return []
            
        try:
            # Execute keyword/semantic search with advanced params and retries
            # Select scoring profile with safe defaults
            scoring_profile = "code_quality_boost"
            try:
                if hasattr(self.config, "azure") and getattr(self.config, "azure"):
                    scoring_profile = getattr(
                        self.config.azure,
                        "default_scoring_profile",
                        "code_quality_boost",
                    )
            except Exception:
                scoring_profile = "code_quality_boost"
            enable_semantic = True
            results = with_retry(
                self.search_client.search,
                search_text=query,
                query_type=QueryType.SEMANTIC if enable_semantic else QueryType.SIMPLE,
                semantic_configuration_name="semantic-config" if enable_semantic else None,
                scoring_profile=scoring_profile,
                filter=filter_expr,
                facets=["language,count:20", "repository,count:20", "tags,count:20"],
                query_caption="extractive" if enable_semantic else None,
                query_answer="extractive" if enable_semantic else None,
                highlight_fields="content,docstring",
                include_total_count=True,
                top=top_k,
                search_fields=["content", "function_name", "class_name", "docstring"]
            )
            return self._process_results(results)
        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return []
    
    async def hybrid_search(
        self,
        query: str,
        filter_expr: Optional[str] = None,
        top_k: int = 50,
        vector_weight: float = 0.5
    ) -> List[HybridSearchResult]:
        """Execute hybrid search combining vector and keyword results"""
        
        # Execute both searches in parallel
        vector_results = await self.vector_search(query, filter_expr, top_k * 2)
        keyword_results = await self.keyword_search(query, filter_expr, top_k * 2)
        
        # Combine results with weighted scoring
        combined_results = self._combine_results(
            vector_results,
            keyword_results,
            vector_weight
        )
        
        # Sort by combined score and return top-k
        combined_results.sort(key=lambda x: x.score, reverse=True)
        return combined_results[:top_k]
    
    def _combine_results(
        self,
        vector_results: List[HybridSearchResult],
        keyword_results: List[HybridSearchResult],
        vector_weight: float
    ) -> List[HybridSearchResult]:
        """Combine vector and keyword results with weighted scoring"""
        combined = {}
        keyword_weight = 1 - vector_weight
        
        # Add vector results
        for result in vector_results:
            combined[result.id] = HybridSearchResult(
                id=result.id,
                score=result.score * vector_weight,
                content=result.content,
                metadata=result.metadata
            )
        
        # Add or update with keyword results
        for result in keyword_results:
            if result.id in combined:
                combined[result.id].score += result.score * keyword_weight
            else:
                combined[result.id] = HybridSearchResult(
                    id=result.id,
                    score=result.score * keyword_weight,
                    content=result.content,
                    metadata=result.metadata
                )
        
        return list(combined.values())
    
    def _process_results(self, results) -> List[HybridSearchResult]:
        """Process Azure Search results into HybridSearchResult objects"""
        processed = []
        
        for result in results:
            try:
                processed.append(HybridSearchResult(
                    id=result.get('id', ''),
                    score=result.get('@search.score', 0.0),
                    content=result.get('content', ''),
                    metadata={
                        'file_path': result.get('file_path'),
                        'repository': result.get('repository'),
                        'language': result.get('language'),
                        'function_name': result.get('function_name'),
                        'class_name': result.get('class_name'),
                        'highlights': result.get('@search.highlights', {})
                    }
                ))
            except Exception as e:
                logger.error(f"Error processing result: {e}")
                continue
                
        return processed
    
    def _build_vector_query(self, query: str, k: int) -> Optional[Any]:
        """Build vector query, preferring server-side vectorization."""
        try:
            # Prefer server-side vectorization with VectorizableTextQuery
            return VectorizableTextQuery(
                text=query, k_nearest_neighbors=k, fields="content_vector"
            )
        except Exception:
            # Fallback to client-side vectorization if the above is not supported
            # or if an embedder is explicitly available.
            if self.embedder:
                try:
                    embedding = self.embedder.generate_embedding(query)
                    if embedding:
                        return VectorizedQuery(
                            vector=embedding, k_nearest_neighbors=k, fields="content_vector"
                        )
                except Exception as e:
                    logger.error(f"Client-side embedding failed: {e}")
        return None
