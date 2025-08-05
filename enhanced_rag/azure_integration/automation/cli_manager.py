"""CLI automation manager for Azure AI Search.

This module consolidates CLI functionality into the automation framework,
providing a unified interface for repository indexing, file processing,
and index management operations.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import os

from ..rest import SearchOperations
from ..embedding_provider import IEmbeddingProvider
from ..processing import FileProcessor
from .data_manager import DataAutomation
from .embedding_manager import EmbeddingAutomation
from .reindex_manager import ReindexAutomation

logger = logging.getLogger(__name__)


class CLIAutomation:
    """Consolidates CLI operations into the automation framework."""
    
    def __init__(self,
                 operations: SearchOperations,
                 embedding_provider: Optional[IEmbeddingProvider] = None):
        """Initialize CLI automation.
        
        Args:
            operations: SearchOperations instance
            embedding_provider: Optional embedding provider
        """
        self.ops = operations
        self.data_automation = DataAutomation(operations)
        self.embedding_automation = EmbeddingAutomation(operations, embedding_provider)
        self.reindex_automation = ReindexAutomation(operations, embedding_provider)
        
        # Use consolidated file processor
        self.file_processor = FileProcessor()
    
    # REMOVED: Duplicated file processing methods
    # These methods have been consolidated into processing.py FileProcessor class
    
    async def process_file(
        self,
        file_path: str,
        repo_path: str,
        repo_name: str,
        generate_embeddings: bool = True
    ) -> List[Dict[str, Any]]:
        """Process a single file and create document chunks.
        
        Args:
            file_path: Path to file
            repo_path: Repository root path
            repo_name: Repository name
            generate_embeddings: Whether to generate embeddings
            
        Returns:
            List of document chunks
        """
        # Use consolidated file processor
        documents = self.file_processor.process_file(file_path, repo_path, repo_name)
        
        # Generate embeddings if requested
        if generate_embeddings and documents:
            context_fields = ['function_name', 'class_name', 'signature', 'docstring']
            documents, stats = await self.embedding_automation.enrich_documents_with_embeddings(
                documents=documents,
                text_field='content',
                embedding_field='content_vector',
                context_fields=context_fields
            )
            logger.info(f"Embedding stats for {file_path}: {stats}")
        
        return documents
    
    async def index_repository(
        self,
        repo_path: str,
        repo_name: str,
        index_name: str,
        patterns: Optional[List[str]] = None,
        generate_embeddings: bool = True,
        batch_size: int = 100,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """Index an entire repository.
        
        Args:
            repo_path: Repository path
            repo_name: Repository name
            index_name: Target index name
            patterns: Optional file patterns to include
            generate_embeddings: Whether to generate embeddings
            batch_size: Batch size for uploads
            progress_callback: Optional progress callback
            
        Returns:
            Indexing results
        """
        start_time = datetime.utcnow()
        logger.info(f"Starting repository indexing: {repo_name} from {repo_path}")
        
        # Use consolidated file processor for repository processing
        if patterns:
            # Convert patterns to extensions
            extensions = set()
            for pattern in patterns:
                if pattern.startswith('*.'):
                    extensions.add(pattern[1:])
            processor = FileProcessor(extensions)
        else:
            processor = self.file_processor
            
        # Process entire repository
        all_documents = processor.process_repository(repo_path, repo_name)
        
        # Generate embeddings if requested
        if generate_embeddings and all_documents:
            context_fields = ['function_name', 'class_name', 'signature', 'docstring']
            all_documents, stats = await self.embedding_automation.enrich_documents_with_embeddings(
                documents=all_documents,
                text_field='content',
                embedding_field='content_vector',
                context_fields=context_fields,
                batch_size=batch_size
            )
            logger.info(f"Embedding stats for repository: {stats}")
            
        # Progress callback
        if progress_callback:
            await progress_callback({
                "files_processed": "completed",
                "total_files": "all",
                "documents_created": len(all_documents)
            })
        
        # Upload documents
        logger.info(f"Uploading {len(all_documents)} documents to index {index_name}")
        
        async def document_generator():
            for doc in all_documents:
                yield doc
        
        upload_result = await self.data_automation.bulk_upload(
            index_name=index_name,
            documents=document_generator(),
            batch_size=batch_size,
            progress_callback=progress_callback
        )
        
        elapsed = (datetime.utcnow() - start_time).total_seconds()
        
        # Calculate processed files from processor results
        processed_files = len(set(doc.get('file_path', 'unknown') for doc in all_documents))
        
        return {
            "repository": repo_name,
            "files_processed": processed_files,
            "documents_created": len(all_documents),
            "upload_result": upload_result,
            "elapsed_seconds": round(elapsed, 2),
            "files_per_second": round(processed_files / elapsed, 2) if elapsed > 0 else 0
        }
    
    async def index_changed_files(
        self,
        file_paths: List[str],
        repo_name: str,
        index_name: str,
        generate_embeddings: bool = True
    ) -> Dict[str, Any]:
        """Index specific changed files.
        
        Args:
            file_paths: List of file paths to index
            repo_name: Repository name
            index_name: Target index name
            generate_embeddings: Whether to generate embeddings
            
        Returns:
            Indexing results
        """
        start_time = datetime.utcnow()
        logger.info(f"Indexing {len(file_paths)} changed files")
        
        # Find the repo root
        repo_path = None
        for file_path in file_paths:
            current = Path(file_path).parent
            while current != current.parent:
                if (current / '.git').exists():
                    repo_path = str(current)
                    break
                current = current.parent
            if repo_path:
                break
        
        if not repo_path:
            # Fall back to common parent
            repo_path = os.path.commonpath([os.path.dirname(p) for p in file_paths])
        
        # Process files
        all_documents = []
        processed_files = 0
        
        for file_path in file_paths:
            if os.path.exists(file_path) and os.path.isfile(file_path):
                docs = await self.process_file(file_path, repo_path, repo_name, generate_embeddings)
                all_documents.extend(docs)
                processed_files += 1
                
                if docs:
                    logger.info(f"Processed {file_path} ({len(docs)} chunks)")
        
        # Upload documents
        async def document_generator():
            for doc in all_documents:
                yield doc
        
        upload_result = await self.data_automation.bulk_upload(
            index_name=index_name,
            documents=document_generator(),
            batch_size=100
        )
        
        elapsed = (datetime.utcnow() - start_time).total_seconds()
        
        return {
            "files_requested": len(file_paths),
            "files_processed": processed_files,
            "documents_created": len(all_documents),
            "upload_result": upload_result,
            "elapsed_seconds": round(elapsed, 2)
        }
    
    async def create_indexing_report(
        self,
        index_name: str,
        repo_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a comprehensive indexing report.
        
        Args:
            index_name: Index name
            repo_name: Optional repository name filter
            
        Returns:
            Indexing report
        """
        # Get index health
        health = await self.reindex_automation.get_index_health(index_name)
        
        # Get embedding stats
        embedding_stats = await self.embedding_automation.get_embedding_stats()
        
        # Get sample documents
        filter_query = f"repository eq '{repo_name}'" if repo_name else None
        sample_results = await self.ops.search_documents(
            index_name=index_name,
            search_text="*",
            filter=filter_query,
            select=["repository", "language", "chunk_type"],
            top=1000
        )
        
        documents = sample_results.get("value", [])
        
        # Analyze documents
        repo_counts = {}
        language_counts = {}
        chunk_type_counts = {}
        
        for doc in documents:
            # Repository counts
            repo = doc.get("repository", "unknown")
            repo_counts[repo] = repo_counts.get(repo, 0) + 1
            
            # Language counts
            lang = doc.get("language", "unknown")
            language_counts[lang] = language_counts.get(lang, 0) + 1
            
            # Chunk type counts
            chunk_type = doc.get("chunk_type", "unknown")
            chunk_type_counts[chunk_type] = chunk_type_counts.get(chunk_type, 0) + 1
        
        return {
            "index_name": index_name,
            "report_time": datetime.utcnow().isoformat(),
            "health": health,
            "embedding_stats": embedding_stats,
            "document_analysis": {
                "total_sampled": len(documents),
                "repositories": repo_counts,
                "languages": language_counts,
                "chunk_types": chunk_type_counts
            },
            "recommendations": await self.reindex_automation.analyze_reindex_need()
        }