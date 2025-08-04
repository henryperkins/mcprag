"""Automated document management for Azure AI Search."""

import logging
from typing import List, Dict, Any, AsyncIterator, Optional, Union
from datetime import datetime, timedelta
import asyncio

from ..rest import SearchOperations

logger = logging.getLogger(__name__)


class DataAutomation:
    """Automate document management tasks."""
    
    def __init__(self, operations: SearchOperations):
        """Initialize data automation.
        
        Args:
            operations: SearchOperations instance
        """
        self.ops = operations
    
    async def bulk_upload(
        self, 
        index_name: str, 
        documents: AsyncIterator[Dict[str, Any]], 
        batch_size: int = 1000,
        merge: bool = False,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """Upload documents in batches.
        
        Args:
            index_name: Target index name
            documents: Async iterator of documents
            batch_size: Documents per batch (max 1000)
            merge: Whether to merge with existing documents
            progress_callback: Optional callback for progress updates
            
        Returns:
            Upload summary with success/failure counts
        """
        batch = []
        total_processed = 0
        total_succeeded = 0
        total_failed = 0
        failed_documents = []
        
        start_time = datetime.utcnow()
        
        async for doc in documents:
            batch.append(doc)
            
            if len(batch) >= batch_size:
                result = await self._upload_batch(index_name, batch, merge)
                
                total_processed += len(batch)
                total_succeeded += result["succeeded"]
                total_failed += result["failed"]
                
                if result["failed_items"]:
                    failed_documents.extend(result["failed_items"])
                
                if progress_callback:
                    await progress_callback({
                        "processed": total_processed,
                        "succeeded": total_succeeded,
                        "failed": total_failed
                    })
                
                batch = []
        
        # Upload remaining documents
        if batch:
            result = await self._upload_batch(index_name, batch, merge)
            total_processed += len(batch)
            total_succeeded += result["succeeded"]
            total_failed += result["failed"]
            
            if result["failed_items"]:
                failed_documents.extend(result["failed_items"])
        
        elapsed_time = (datetime.utcnow() - start_time).total_seconds()
        
        return {
            "total_processed": total_processed,
            "succeeded": total_succeeded,
            "failed": total_failed,
            "elapsed_seconds": round(elapsed_time, 2),
            "documents_per_second": round(total_processed / elapsed_time, 2) if elapsed_time > 0 else 0,
            "failed_documents": failed_documents[:100]  # Limit to first 100 failures
        }
    
    async def _upload_batch(
        self, 
        index_name: str, 
        documents: List[Dict[str, Any]],
        merge: bool = False
    ) -> Dict[str, Any]:
        """Upload a single batch with error handling.
        
        Args:
            index_name: Target index name
            documents: Batch of documents
            merge: Whether to merge with existing
            
        Returns:
            Batch result with counts and failed items
        """
        try:
            result = await self.ops.upload_documents(index_name, documents, merge)
            
            succeeded = 0
            failed = 0
            failed_items = []
            
            # Process results
            for item in result.get("value", []):
                if item.get("status", False):
                    succeeded += 1
                else:
                    failed += 1
                    failed_items.append({
                        "key": item.get("key"),
                        "error": item.get("errorMessage", "Unknown error")
                    })
            
            if failed > 0:
                logger.warning(f"Batch upload: {failed} documents failed out of {len(documents)}")
            
            return {
                "succeeded": succeeded,
                "failed": failed,
                "failed_items": failed_items
            }
            
        except Exception as e:
            logger.error(f"Batch upload failed entirely: {e}")
            return {
                "succeeded": 0,
                "failed": len(documents),
                "failed_items": [{"error": str(e)}]
            }
    
    async def cleanup_old_documents(
        self, 
        index_name: str, 
        date_field: str, 
        days_old: int,
        batch_size: int = 100,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Delete documents older than specified days.
        
        Args:
            index_name: Target index name
            date_field: Date field to check
            days_old: Age threshold in days
            batch_size: Deletion batch size
            dry_run: If True, only count without deleting
            
        Returns:
            Cleanup summary
        """
        cutoff_date = (datetime.utcnow() - timedelta(days=days_old)).isoformat()
        
        total_found = 0
        total_deleted = 0
        skip = 0
        
        logger.info(f"{'[DRY RUN] ' if dry_run else ''}Cleaning documents older than {cutoff_date}")
        
        while True:
            # Search for old documents
            results = await self.ops.search(
                index_name,
                query="*",
                filter=f"{date_field} lt {cutoff_date}",
                select=["id"],  # Assuming 'id' is the key field
                top=batch_size,
                skip=skip
            )
            
            documents = results.get("value", [])
            if not documents:
                break
                
            total_found += len(documents)
            
            if not dry_run:
                # Delete in batch
                keys = [doc["id"] for doc in documents]
                delete_result = await self.ops.delete_documents(index_name, keys)
                
                # Count successful deletions
                for item in delete_result.get("value", []):
                    if item.get("status", False):
                        total_deleted += 1
            else:
                total_deleted = total_found
            
            # If we got fewer than batch_size, we're done
            if len(documents) < batch_size:
                break
                
            skip += batch_size
            
            # Add delay to avoid overwhelming the service
            await asyncio.sleep(0.5)
        
        return {
            "found": total_found,
            "deleted": total_deleted,
            "dry_run": dry_run,
            "date_field": date_field,
            "cutoff_date": cutoff_date
        }
    
    async def reindex_documents(
        self,
        source_index: str,
        target_index: str,
        transform_func: Optional[callable] = None,
        filter_query: Optional[str] = None,
        batch_size: int = 100
    ) -> Dict[str, Any]:
        """Reindex documents from one index to another.
        
        Args:
            source_index: Source index name
            target_index: Target index name
            transform_func: Optional function to transform documents
            filter_query: Optional filter for source documents
            batch_size: Batch size for operations
            
        Returns:
            Reindex summary
        """
        total_processed = 0
        total_succeeded = 0
        skip = 0
        
        logger.info(f"Reindexing from {source_index} to {target_index}")
        
        while True:
            # Search source index
            search_params = {
                "query": "*",
                "top": batch_size,
                "skip": skip
            }
            
            if filter_query:
                search_params["filter"] = filter_query
            
            results = await self.ops.search(source_index, **search_params)
            documents = results.get("value", [])
            
            if not documents:
                break
            
            # Transform documents if function provided
            if transform_func:
                transformed_docs = []
                for doc in documents:
                    try:
                        transformed = await transform_func(doc) if asyncio.iscoroutinefunction(transform_func) else transform_func(doc)
                        if transformed:  # Skip None results
                            transformed_docs.append(transformed)
                    except Exception as e:
                        logger.error(f"Transform error for document: {e}")
                documents = transformed_docs
            
            # Upload to target index
            if documents:
                result = await self._upload_batch(target_index, documents)
                total_processed += len(documents)
                total_succeeded += result["succeeded"]
            
            if len(documents) < batch_size:
                break
                
            skip += batch_size
            await asyncio.sleep(0.5)  # Rate limiting
        
        return {
            "total_processed": total_processed,
            "succeeded": total_succeeded,
            "failed": total_processed - total_succeeded,
            "source_index": source_index,
            "target_index": target_index
        }
    
    async def verify_documents(
        self,
        index_name: str,
        sample_size: int = 100,
        check_fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Verify document integrity and completeness.
        
        Args:
            index_name: Index to verify
            sample_size: Number of documents to sample
            check_fields: Specific fields to check for presence
            
        Returns:
            Verification summary
        """
        # Get total count
        total_count = await self.ops.count_documents(index_name)
        
        # Sample documents
        results = await self.ops.search(
            index_name,
            query="*",
            top=min(sample_size, total_count)
        )
        
        documents = results.get("value", [])
        issues = []
        field_stats = {}
        
        for doc in documents:
            # Check for missing fields
            if check_fields:
                for field in check_fields:
                    if field not in doc or doc[field] is None:
                        issues.append({
                            "type": "missing_field",
                            "document_id": doc.get("id", "unknown"),
                            "field": field
                        })
            
            # Collect field statistics
            for field, value in doc.items():
                if field not in field_stats:
                    field_stats[field] = {
                        "present": 0,
                        "null": 0,
                        "empty": 0
                    }
                
                field_stats[field]["present"] += 1
                
                if value is None:
                    field_stats[field]["null"] += 1
                elif isinstance(value, str) and not value.strip():
                    field_stats[field]["empty"] += 1
        
        # Calculate field coverage
        field_coverage = {}
        for field, stats in field_stats.items():
            coverage = (stats["present"] - stats["null"]) / len(documents) * 100
            field_coverage[field] = round(coverage, 2)
        
        return {
            "total_documents": total_count,
            "sampled_documents": len(documents),
            "issues": issues[:50],  # Limit to first 50 issues
            "issue_count": len(issues),
            "field_coverage": field_coverage,
            "verification_timestamp": datetime.utcnow().isoformat()
        }
    
    async def export_documents_iterator(
        self,
        index_name: str,
        filter_query: Optional[str] = None,
        select_fields: Optional[List[str]] = None,
        batch_size: int = 100
    ) -> AsyncIterator[Dict[str, Any]]:
        """Export documents from an index as an async iterator.
        
        Args:
            index_name: Source index name
            filter_query: Optional filter query
            select_fields: Fields to include in export
            batch_size: Batch size for retrieval
            
        Yields:
            Documents from the index
        """
        skip = 0
        
        while True:
            search_params = {
                "query": "*",
                "top": batch_size,
                "skip": skip
            }
            
            if filter_query:
                search_params["filter"] = filter_query
            
            if select_fields:
                search_params["select"] = select_fields
            
            results = await self.ops.search(index_name, **search_params)
            documents = results.get("value", [])
            
            if not documents:
                break
            
            for doc in documents:
                yield doc
            
            if len(documents) < batch_size:
                break
                
            skip += batch_size
            await asyncio.sleep(0.1)  # Rate limiting

    async def export_documents(
        self,
        index_name: str,
        output_async_iterator: bool = True,
        filter_query: Optional[str] = None,
        select_fields: Optional[List[str]] = None,
        batch_size: int = 100
    ) -> Union[AsyncIterator[Dict[str, Any]], List[Dict[str, Any]]]:
        """Export documents from an index.
        
        Args:
            index_name: Source index name
            output_async_iterator: If True, return iterator; if False, return list
            filter_query: Optional filter query
            select_fields: Fields to include in export
            batch_size: Batch size for retrieval
            
        Returns:
            AsyncIterator or List of documents
        """
        if output_async_iterator:
            return self.export_documents_iterator(
                index_name, filter_query, select_fields, batch_size
            )
        else:
            # Collect all documents into a list
            all_documents = []
            async for doc in self.export_documents_iterator(
                index_name, filter_query, select_fields, batch_size
            ):
                all_documents.append(doc)
            return all_documents