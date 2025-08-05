"""Reindexing operations for Azure AI Search.

This module provides various strategies for reindexing content in Azure AI Search,
including drop-and-rebuild, incremental updates, and indexer-based approaches.
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from enum import Enum

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient, SearchIndexerClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchIndexer,
    SearchIndexerStatus
)

from .rest import AzureSearchClient, SearchOperations
from .automation import DataAutomation
from .processing import FileProcessor
from .config import AzureSearchConfig

logger = logging.getLogger(__name__)


class ReindexMethod(Enum):
    """Available reindexing methods."""
    DROP_REBUILD = "drop_rebuild"
    INCREMENTAL = "incremental"
    INDEXER_BASED = "indexer_based"
    CLEAR_AND_RELOAD = "clear_and_reload"


class ReindexOperations:
    """Handles various reindexing operations for Azure AI Search."""
    
    def __init__(self, config: Optional[AzureSearchConfig] = None, index_name: Optional[str] = None):
        """Initialize reindex operations with Azure Search clients.
        
        Args:
            config: Azure Search configuration (loads from env if not provided)
            index_name: Target index name (defaults to codebase-mcp-sota)
        """
        if config is None:
            # Fallback to legacy config loading for backward compatibility
            try:
                from enhanced_rag.core.config import get_config
                legacy_config = get_config()
                config = AzureSearchConfig(
                    endpoint=legacy_config.azure.endpoint,
                    api_key=legacy_config.azure.admin_key
                )
                if not index_name:
                    index_name = legacy_config.azure.index_name
            except ImportError:
                # If legacy config is not available, load from env
                config = AzureSearchConfig.from_env()
        
        self.endpoint = config.endpoint
        self.api_key = config.api_key
        self.index_name = index_name or "codebase-mcp-sota"
        
        credential = AzureKeyCredential(self.api_key)
        self.index_client = SearchIndexClient(self.endpoint, credential)
        self.indexer_client = SearchIndexerClient(self.endpoint, credential)
        self.search_client = SearchClient(self.endpoint, self.index_name, credential)
        
    async def get_index_info(self) -> Dict[str, Any]:
        """Get current index information."""
        try:
            index = self.index_client.get_index(self.index_name)
            doc_count = self.search_client.get_document_count()
            
            return {
                "name": index.name,
                "fields": len(index.fields),
                "document_count": doc_count,
                "etag": index.e_tag,
                "vector_search": bool(index.vector_search),
                "semantic_search": bool(index.semantic_search)
            }
        except Exception as e:
            logger.error(f"Failed to get index info: {e}")
            return {}
    
    async def drop_and_rebuild(self, schema_path: Optional[str] = None) -> bool:
        """Drop and rebuild the index with optional schema updates.
        
        Args:
            schema_path: Path to JSON file with new schema (optional)
            
        Returns:
            bool: True if successful
        """
        logger.info(f"Starting drop and rebuild for index '{self.index_name}'")
        
        try:
            # Step 1: Get current schema or load from file
            if schema_path and Path(schema_path).exists():
                with open(schema_path, 'r') as f:
                    schema = json.load(f)
                logger.info(f"Loaded schema from {schema_path}")
            else:
                # Get current schema
                current_index = self.index_client.get_index(self.index_name)
                schema = current_index.as_dict()
                # Remove metadata fields
                for key in ['@odata.context', '@odata.etag', 'etag', 'e_tag']:
                    schema.pop(key, None)
                logger.info("Using current index schema")
            
            # Step 2: Delete existing index
            logger.info(f"Deleting index '{self.index_name}'...")
            self.index_client.delete_index(self.index_name)
            time.sleep(2)  # Brief wait for deletion to propagate
            
            # Step 3: Create new index
            logger.info(f"Creating new index '{self.index_name}'...")
            rest_client = AzureSearchClient(self.endpoint, self.api_key)
            rest_ops = SearchOperations(rest_client)
            await rest_ops.create_index(schema)
            
            logger.info("Drop and rebuild completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Drop and rebuild failed: {e}")
            return False
    
    async def clear_documents(self, filter_query: Optional[str] = None) -> int:
        """Clear documents from the index.
        
        Args:
            filter_query: OData filter to select specific documents (optional)
            
        Returns:
            int: Number of documents deleted
        """
        logger.info(f"Clearing documents from index '{self.index_name}'")
        
        try:
            # Get documents to delete
            search_kwargs = {"select": ["id"], "top": 1000}
            if filter_query:
                search_kwargs["filter"] = filter_query
                
            deleted_count = 0
            
            while True:
                results = list(self.search_client.search("*", **search_kwargs))
                if not results:
                    break
                    
                # Delete in batches
                docs_to_delete = [{"id": doc["id"]} for doc in results]
                self.search_client.delete_documents(docs_to_delete)
                deleted_count += len(docs_to_delete)
                logger.info(f"Deleted {len(docs_to_delete)} documents")
                
            logger.info(f"Total documents deleted: {deleted_count}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to clear documents: {e}")
            return 0
    
    async def create_indexer(
        self,
        indexer_name: str,
        data_source_name: str,
        schedule_minutes: int = 120,
        field_mappings: Optional[List[Dict]] = None
    ) -> bool:
        """Create an indexer for automated reindexing.
        
        Args:
            indexer_name: Name for the indexer
            data_source_name: Name of existing data source
            schedule_minutes: Run interval in minutes
            field_mappings: Optional field mappings
            
        Returns:
            bool: True if successful
        """
        logger.info(f"Creating indexer '{indexer_name}'")
        
        try:
            # Default field mappings if not provided
            if not field_mappings:
                field_mappings = [
                    {
                        "sourceFieldName": "metadata_storage_path",
                        "targetFieldName": "file_path",
                        "mappingFunction": {"name": "base64Decode"}
                    },
                    {
                        "sourceFieldName": "metadata_storage_last_modified",
                        "targetFieldName": "last_modified"
                    }
                ]
            
            indexer = SearchIndexer(
                name=indexer_name,
                data_source_name=data_source_name,
                target_index_name=self.index_name,
                schedule={"interval": f"PT{schedule_minutes}M"},
                field_mappings=field_mappings
            )
            
            self.indexer_client.create_or_update_indexer(indexer)
            logger.info(f"Indexer '{indexer_name}' created successfully")
            
            # Run indexer immediately
            self.indexer_client.run_indexer(indexer_name)
            logger.info(f"Indexer '{indexer_name}' run started")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to create indexer: {e}")
            return False
    
    async def get_indexer_status(self, indexer_name: str) -> Optional[Dict[str, Any]]:
        """Get the status of an indexer.
        
        Args:
            indexer_name: Name of the indexer
            
        Returns:
            Dict with status information or None
        """
        try:
            status = self.indexer_client.get_indexer_status(indexer_name)
            return {
                "status": status.status,
                "last_result": status.last_result.status if status.last_result else None,
                "execution_history": len(status.execution_history),
                "errors": status.last_result.errors if status.last_result else [],
                "warnings": status.last_result.warnings if status.last_result else []
            }
        except Exception as e:
            logger.error(f"Failed to get indexer status: {e}")
            return None
    
    # REMOVED: Duplicated file processing methods
    # These methods have been consolidated into processing.py 
    # Use FileProcessor class instead
    
    async def reindex_repository(
        self,
        repo_path: str,
        repo_name: str,
        method: ReindexMethod = ReindexMethod.INCREMENTAL,
        clear_first: bool = False
    ) -> bool:
        """Reindex a repository using the specified method.
        
        Args:
            repo_path: Path to repository
            repo_name: Repository name
            method: Reindexing method to use
            clear_first: Clear existing documents first
            
        Returns:
            bool: True if successful
        """
        logger.info(f"Reindexing repository '{repo_name}' using method '{method.value}'")
        
        try:
            # Clear documents if requested
            if clear_first:
                deleted = await self.clear_documents(f"repository eq '{repo_name}'")
                logger.info(f"Cleared {deleted} existing documents")
            
            # Initialize REST client and operations
            rest_client = AzureSearchClient(
                endpoint=self.endpoint,
                api_key=self.api_key
            )
            rest_ops = SearchOperations(rest_client)
            data_automation = DataAutomation(rest_ops)
            
            # Use consolidated file processor
            processor = FileProcessor()
            all_documents = processor.process_repository(repo_path, repo_name)
            
            # Upload documents using async generator
            async def document_generator():
                for doc in all_documents:
                    yield doc
            
            # Upload in batches
            result = await data_automation.bulk_upload(
                index_name=self.index_name,
                documents=document_generator(),
                batch_size=100
            )
            
            logger.info(f"Upload complete: {result['succeeded']} succeeded, {result['failed']} failed")
            logger.info("Repository reindexing completed")
            return result['succeeded'] > 0
            
        except Exception as e:
            logger.error(f"Repository reindexing failed: {e}")
            return False
    
    async def validate_index_schema(self) -> Dict[str, Any]:
        """Validate the current index schema.
        
        Returns:
            Dict with validation results
        """
        try:
            index = self.index_client.get_index(self.index_name)
            
            issues = []
            warnings = []
            
            # Check for required fields
            field_names = {f.name for f in index.fields}
            required_fields = {"id", "file_path", "repository", "content"}
            missing = required_fields - field_names
            
            if missing:
                issues.append(f"Missing required fields: {missing}")
            
            # Check vector configuration
            if index.vector_search:
                vector_fields = [f for f in index.fields if f.vector_search_dimensions]
                if not vector_fields:
                    warnings.append("Vector search enabled but no vector fields found")
                else:
                    for vf in vector_fields:
                        if vf.name == "content_vector" and vf.vector_search_dimensions != 3072:
                            warnings.append(f"Vector field '{vf.name}' has {vf.vector_search_dimensions} dimensions, expected 3072")
            
            # Check field configurations
            for field in index.fields:
                if field.name == "file_path" and not field.filterable:
                    warnings.append("Field 'file_path' should be filterable")
                if field.name == "repository" and not field.facetable:
                    warnings.append("Field 'repository' should be facetable")
            
            return {
                "valid": len(issues) == 0,
                "issues": issues,
                "warnings": warnings,
                "field_count": len(index.fields),
                "vector_enabled": bool(index.vector_search),
                "semantic_enabled": bool(index.semantic_search)
            }
            
        except Exception as e:
            logger.error(f"Schema validation failed: {e}")
            return {"valid": False, "error": str(e)}
    
    async def backup_index_schema(self, output_path: str) -> bool:
        """Backup the current index schema to a file.
        
        Args:
            output_path: Path to save the schema JSON
            
        Returns:
            bool: True if successful
        """
        try:
            index = self.index_client.get_index(self.index_name)
            schema = index.serialize()
            
            # Remove metadata
            for key in ['@odata.context', '@odata.etag']:
                schema.pop(key, None)
            
            # Add metadata
            schema['_backup_metadata'] = {
                'timestamp': datetime.utcnow().isoformat(),
                'index_name': self.index_name,
                'document_count': self.search_client.get_document_count()
            }
            
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(schema, f, indent=2)
            
            logger.info(f"Index schema backed up to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to backup schema: {e}")
            return False