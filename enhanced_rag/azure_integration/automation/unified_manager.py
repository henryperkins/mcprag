"""Unified automation manager for Azure AI Search.

This module provides a single interface that consolidates all automation
capabilities including indexing, reindexing, embeddings, data management,
and health monitoring.
"""

import logging
from typing import Dict, Any, Optional, List, Union, AsyncIterator
from datetime import datetime

from ..rest import AzureSearchClient, SearchOperations
from ..embedding_provider import IEmbeddingProvider, AzureOpenAIEmbeddingProvider
from .index_manager import IndexAutomation
from .data_manager import DataAutomation
from .indexer_manager import IndexerAutomation
from .health_monitor import HealthMonitor
from .reindex_manager import ReindexAutomation
from .embedding_manager import EmbeddingAutomation
from .cli_manager import CLIAutomation

logger = logging.getLogger(__name__)


class UnifiedAutomation:
    """Unified interface for all Azure AI Search automation tasks."""
    
    def __init__(self,
                 endpoint: str,
                 api_key: str,
                 embedding_provider: Optional[IEmbeddingProvider] = None,
                 default_index: Optional[str] = None):
        """Initialize unified automation manager.
        
        Args:
            endpoint: Azure Search endpoint
            api_key: Azure Search admin key
            embedding_provider: Optional embedding provider
            default_index: Default index name
        """
        # Initialize REST client and operations
        self.client = AzureSearchClient(endpoint, api_key)
        self.ops = SearchOperations(self.client)
        
        # Initialize embedding provider
        if embedding_provider is None:
            try:
                embedding_provider = AzureOpenAIEmbeddingProvider()
            except Exception as e:
                logger.warning(f"Failed to create embedding provider: {e}")
                embedding_provider = None
        
        # Initialize all managers
        self.index = IndexAutomation(endpoint=endpoint, api_key=api_key)
        self.data = DataAutomation(self.ops)
        self.indexer = IndexerAutomation(self.ops)
        self.health = HealthMonitor(self.ops)
        self.reindex = ReindexAutomation(self.ops, embedding_provider)
        self.embeddings = EmbeddingAutomation(self.ops, embedding_provider)
        self.cli = CLIAutomation(self.ops, embedding_provider)
        
        self.default_index = default_index or "codebase-mcp-sota"
        self.endpoint = endpoint
    
    # ========== Repository Indexing ==========
    
    async def index_repository(
        self,
        repo_path: str,
        repo_name: str,
        index_name: Optional[str] = None,
        patterns: Optional[List[str]] = None,
        generate_embeddings: bool = True,
        clear_existing: bool = False,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """Index a complete repository with all features.
        
        Args:
            repo_path: Path to repository
            repo_name: Repository name
            index_name: Target index (uses default if None)
            patterns: File patterns to include
            generate_embeddings: Whether to generate embeddings
            clear_existing: Clear existing documents first
            progress_callback: Progress callback function
            
        Returns:
            Indexing results
        """
        index_name = index_name or self.default_index
        
        # Clear existing documents if requested
        if clear_existing:
            logger.info(f"Clearing existing documents for repository {repo_name}")
            clear_result = await self.reindex.reindex_ops.clear_documents(
                f"repository eq '{repo_name}'"
            )
            logger.info(f"Cleared {clear_result} documents")
        
        # Index the repository
        result = await self.cli.index_repository(
            repo_path=repo_path,
            repo_name=repo_name,
            index_name=index_name,
            patterns=patterns,
            generate_embeddings=generate_embeddings,
            progress_callback=progress_callback
        )
        
        return result
    
    async def index_changed_files(
        self,
        file_paths: List[str],
        repo_name: str,
        index_name: Optional[str] = None,
        generate_embeddings: bool = True
    ) -> Dict[str, Any]:
        """Index specific changed files.
        
        Args:
            file_paths: List of file paths
            repo_name: Repository name
            index_name: Target index (uses default if None)
            generate_embeddings: Whether to generate embeddings
            
        Returns:
            Indexing results
        """
        index_name = index_name or self.default_index
        
        return await self.cli.index_changed_files(
            file_paths=file_paths,
            repo_name=repo_name,
            index_name=index_name,
            generate_embeddings=generate_embeddings
        )
    
    # ========== Index Management ==========
    
    async def create_or_update_index(
        self,
        index_name: Optional[str] = None,
        enable_vectors: bool = True,
        enable_semantic: bool = True,
        vector_dimensions: int = 3072
    ) -> Dict[str, Any]:
        """Create or update an index with full configuration.
        
        Args:
            index_name: Index name (uses default if None)
            enable_vectors: Enable vector search
            enable_semantic: Enable semantic search
            vector_dimensions: Vector dimensions
            
        Returns:
            Creation results
        """
        index_name = index_name or self.default_index
        
        # Build index definition from canonical schema and ensure via REST
        from pathlib import Path
        import json
        schema_path = Path("azure_search_index_schema.json")
        if not schema_path.exists():
            raise FileNotFoundError("Index schema file 'azure_search_index_schema.json' not found")
        index_def = json.loads(schema_path.read_text())
        index_def["name"] = index_name

        # Instantiate index automation with underlying client creds
        from .index_manager import IndexAutomation as _IndexAutomation
        automation = _IndexAutomation(endpoint=self.client.endpoint, api_key=self.client.api_key)
        op = await automation.ensure_index_exists(index_def)

        # Fetch the current schema for summary
        current = await self.ops.get_index(index_name)
        fields = current.get("fields", [])
        return {
            "index_name": index_name,
            "fields": len(fields),
            "vector_search_enabled": bool(current.get("vectorSearch")),
            "semantic_search_enabled": bool(current.get("semantic")),
            "created": bool(op.get("created")),
            "updated": bool(op.get("updated"))
        }
    
    async def validate_index(
        self,
        index_name: Optional[str] = None,
        check_embeddings: bool = True
    ) -> Dict[str, Any]:
        """Validate index configuration and health.
        
        Args:
            index_name: Index name (uses default if None)
            check_embeddings: Whether to validate embeddings
            
        Returns:
            Validation results
        """
        index_name = index_name or self.default_index
        
        # Get health information
        health = await self.reindex.get_index_health(index_name)
        
        # Validate embeddings if requested
        embedding_validation = None
        if check_embeddings:
            embedding_validation = await self.embeddings.validate_embeddings(
                index_name=index_name,
                sample_size=100
            )
        
        return {
            "index_health": health,
            "embedding_validation": embedding_validation,
            "overall_valid": health["schema_valid"] and 
                           (not check_embeddings or embedding_validation.get("validation_passed", False))
        }
    
    # ========== Reindexing Operations ==========
    
    async def reindex(
        self,
        method: str,
        index_name: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Perform reindexing with specified method.
        
        Args:
            method: Reindexing method (drop-rebuild, clear, repository)
            index_name: Index name (uses default if None)
            **kwargs: Additional method-specific parameters
            
        Returns:
            Reindexing results
        """
        # Set index name for reindex operations
        if index_name:
            self.reindex.reindex_ops.index_name = index_name
        
        return await self.reindex.perform_reindex(method=method, **kwargs)
    
    async def analyze_and_recommend(
        self,
        index_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze index and provide recommendations.
        
        Args:
            index_name: Index name (uses default if None)
            
        Returns:
            Analysis and recommendations
        """
        index_name = index_name or self.default_index
        
        # Get comprehensive analysis
        health = await self.reindex.get_index_health(index_name)
        recommendations = await self.reindex.analyze_reindex_need()
        report = await self.cli.create_indexing_report(index_name)
        
        return {
            "health_summary": health,
            "recommendations": recommendations,
            "detailed_report": report,
            "suggested_actions": self._generate_action_plan(health, recommendations)
        }
    
    def _generate_action_plan(
        self,
        health: Dict[str, Any],
        recommendations: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate actionable steps based on analysis."""
        actions = []
        
        # Check for critical issues
        if not health["schema_valid"]:
            actions.append({
                "priority": "critical",
                "action": "reindex",
                "method": "drop-rebuild",
                "reason": "Schema validation failed"
            })
        
        # Check recommendations
        for rec in recommendations.get("recommendations", []):
            if rec["priority"] == "high":
                actions.append({
                    "priority": "high",
                    "action": rec["action"],
                    "reason": rec["reason"]
                })
        
        # Check document count
        if health["document_count"] == 0:
            actions.append({
                "priority": "high",
                "action": "index_repository",
                "reason": "Index is empty"
            })
        
        return actions
    
    # ========== Batch Operations ==========
    
    async def bulk_upload_documents(
        self,
        documents: AsyncIterator[Dict[str, Any]],
        index_name: Optional[str] = None,
        enrich_embeddings: bool = True,
        batch_size: int = 100,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """Bulk upload documents with optional embedding enrichment.
        
        Args:
            documents: Async iterator of documents
            index_name: Target index (uses default if None)
            enrich_embeddings: Whether to add embeddings
            batch_size: Upload batch size
            progress_callback: Progress callback
            
        Returns:
            Upload results
        """
        index_name = index_name or self.default_index
        
        if enrich_embeddings:
            # Process documents in batches for embedding
            enriched_docs = []
            async for doc in documents:
                enriched_docs.append(doc)
                
                if len(enriched_docs) >= batch_size:
                    # Enrich batch with embeddings
                    enriched_docs, _ = await self.embeddings.enrich_documents_with_embeddings(
                        documents=enriched_docs,
                        batch_size=batch_size
                    )
                    
                    # Upload enriched batch
                    async def batch_generator():
                        for d in enriched_docs:
                            yield d
                    
                    await self.data.bulk_upload(
                        index_name=index_name,
                        documents=batch_generator(),
                        batch_size=batch_size,
                        progress_callback=progress_callback
                    )
                    
                    enriched_docs = []
            
            # Process remaining documents
            if enriched_docs:
                enriched_docs, _ = await self.embeddings.enrich_documents_with_embeddings(
                    documents=enriched_docs
                )
                
                async def final_generator():
                    for d in enriched_docs:
                        yield d
                
                result = await self.data.bulk_upload(
                    index_name=index_name,
                    documents=final_generator(),
                    batch_size=batch_size,
                    progress_callback=progress_callback
                )
        else:
            # Direct upload without embedding
            result = await self.data.bulk_upload(
                index_name=index_name,
                documents=documents,
                batch_size=batch_size,
                progress_callback=progress_callback
            )
        
        return result
    
    # ========== Monitoring and Health ==========
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health status.
        
        Returns:
            System health information
        """
        # Get service health
        service_health = await self.health.check_service_health()
        
        # Get default index health
        index_health = None
        try:
            index_health = await self.reindex.get_index_health(self.default_index)
        except Exception as e:
            logger.warning(f"Failed to get index health: {e}")
        
        # Get embedding stats
        embedding_stats = await self.embeddings.get_embedding_stats()
        
        return {
            "service": service_health,
            "default_index": index_health,
            "embedding_system": embedding_stats,
            "endpoint": self.endpoint,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def monitor_indexing_operation(
        self,
        operation_id: str,
        poll_interval_seconds: int = 5,
        timeout_seconds: int = 300
    ) -> Dict[str, Any]:
        """Monitor a long-running indexing operation.
        
        Args:
            operation_id: Operation ID to monitor
            poll_interval_seconds: Polling interval
            timeout_seconds: Maximum wait time
            
        Returns:
            Operation results
        """
        return await self.health.monitor_operation(
            operation_type="indexing",
            operation_id=operation_id,
            check_interval_seconds=poll_interval_seconds,
            timeout_seconds=timeout_seconds
        )
    
    # ========== Utility Methods ==========
    
    async def clear_caches(self) -> Dict[str, Any]:
        """Clear all caches.
        
        Returns:
            Cache clearing results
        """
        embedding_cache = await self.embeddings.clear_embedding_cache()
        
        return {
            "embedding_cache": embedding_cache,
            "cleared_at": datetime.utcnow().isoformat()
        }
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics.
        
        Returns:
            System statistics
        """
        # Get index statistics
        index_stats = {}
        try:
            indexes = await self.ops.list_indexes(select=["name"])
            for idx in indexes:
                stats = await self.ops.get_index_stats(idx["name"])
                index_stats[idx["name"]] = stats
        except Exception as e:
            logger.warning(f"Failed to get index stats: {e}")
        
        # Get embedding statistics
        embedding_stats = await self.embeddings.get_embedding_stats()
        
        return {
            "indexes": index_stats,
            "embeddings": embedding_stats,
            "timestamp": datetime.utcnow().isoformat()
        }
