"""Index management utilities for Azure AI Search.

Provides utilities for managing Azure Search indexes including monitoring,
optimization, and maintenance tasks.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.models import SearchMode

from enhanced_rag.core.config import get_config

logger = logging.getLogger(__name__)


@dataclass
class IndexStats:
    """Statistics about an index."""
    name: str
    document_count: int
    storage_size_bytes: Optional[int]
    field_count: int
    vector_fields: List[str]
    last_modified: Optional[datetime]
    

@dataclass
class DocumentStats:
    """Statistics about documents in an index."""
    total_count: int
    repository_counts: Dict[str, int]
    language_counts: Dict[str, int]
    date_range: Tuple[datetime, datetime]
    avg_content_length: float
    

class IndexManagement:
    """Utilities for managing Azure Search indexes."""
    
    def __init__(self):
        """Initialize index management utilities."""
        config = get_config()
        self.endpoint = config.azure.endpoint
        self.api_key = config.azure.admin_key
        self.index_name = config.azure.index_name or "codebase-mcp-sota"
        
        credential = AzureKeyCredential(self.api_key)
        self.index_client = SearchIndexClient(self.endpoint, credential)
        self.search_client = SearchClient(self.endpoint, self.index_name, credential)
        
    async def get_index_statistics(self) -> IndexStats:
        """Get comprehensive statistics about the index.
        
        Returns:
            IndexStats with index information
        """
        try:
            index = self.index_client.get_index(self.index_name)
            doc_count = self.search_client.get_document_count()
            
            # Get vector fields
            vector_fields = [
                f.name for f in index.fields 
                if hasattr(f, 'vector_search_dimensions') and f.vector_search_dimensions
            ]
            
            # Get service statistics if available
            try:
                service_stats = self.index_client.get_service_statistics()
                storage_size = service_stats.counters.storage_size_counter.usage
            except:
                storage_size = None
                
            return IndexStats(
                name=index.name,
                document_count=doc_count,
                storage_size_bytes=storage_size,
                field_count=len(index.fields),
                vector_fields=vector_fields,
                last_modified=None  # Not directly available
            )
            
        except Exception as e:
            logger.error(f"Failed to get index statistics: {e}")
            raise
            
    async def get_document_statistics(self) -> DocumentStats:
        """Get statistics about documents in the index.
        
        Returns:
            DocumentStats with document information
        """
        try:
            # Get total count
            total_count = self.search_client.get_document_count()
            
            # Get repository counts using facets
            repo_results = self.search_client.search(
                search_text="*",
                facets=["repository"],
                top=0
            )
            
            repository_counts = {}
            for result in repo_results:
                if hasattr(result, 'facets') and 'repository' in result.facets:
                    for facet in result.facets['repository']:
                        repository_counts[facet.value] = facet.count
                break  # Only need first result for facets
                
            # Get language counts
            lang_results = self.search_client.search(
                search_text="*",
                facets=["language"],
                top=0
            )
            
            language_counts = {}
            for result in lang_results:
                if hasattr(result, 'facets') and 'language' in result.facets:
                    for facet in result.facets['language']:
                        language_counts[facet.value] = facet.count
                break
                
            # Get date range and content length (sample)
            sample_results = list(self.search_client.search(
                search_text="*",
                select=["last_modified", "content"],
                top=100
            ))
            
            if sample_results:
                dates = [r.get('last_modified') for r in sample_results if r.get('last_modified')]
                if dates:
                    date_range = (min(dates), max(dates))
                else:
                    date_range = (datetime.now(), datetime.now())
                    
                contents = [len(r.get('content', '')) for r in sample_results if r.get('content')]
                avg_content_length = sum(contents) / len(contents) if contents else 0
            else:
                date_range = (datetime.now(), datetime.now())
                avg_content_length = 0
                
            return DocumentStats(
                total_count=total_count,
                repository_counts=repository_counts,
                language_counts=language_counts,
                date_range=date_range,
                avg_content_length=avg_content_length
            )
            
        except Exception as e:
            logger.error(f"Failed to get document statistics: {e}")
            raise
            
    async def find_duplicates(self, field: str = "content") -> List[Dict[str, Any]]:
        """Find potential duplicate documents based on a field.
        
        Args:
            field: Field to check for duplicates
            
        Returns:
            List of potential duplicate groups
        """
        duplicates = []
        
        try:
            # This is a simplified approach - for production, you'd want
            # to use more sophisticated duplicate detection
            seen_hashes = {}
            
            # Process documents in batches
            batch_size = 100
            skip = 0
            
            while True:
                results = list(self.search_client.search(
                    search_text="*",
                    select=["id", "file_path", field],
                    top=batch_size,
                    skip=skip
                ))
                
                if not results:
                    break
                    
                for doc in results:
                    if field in doc and doc[field]:
                        # Simple hash-based duplicate detection
                        content_hash = hash(doc[field])
                        
                        if content_hash in seen_hashes:
                            # Found potential duplicate
                            seen_hashes[content_hash].append({
                                "id": doc["id"],
                                "file_path": doc.get("file_path", "Unknown")
                            })
                        else:
                            seen_hashes[content_hash] = [{
                                "id": doc["id"],
                                "file_path": doc.get("file_path", "Unknown")
                            }]
                            
                skip += batch_size
                
                # Limit to prevent memory issues
                if skip > 10000:
                    logger.warning("Duplicate detection limited to first 10,000 documents")
                    break
                    
            # Filter to only actual duplicates
            for content_hash, docs in seen_hashes.items():
                if len(docs) > 1:
                    duplicates.append({
                        "count": len(docs),
                        "documents": docs
                    })
                    
            return duplicates
            
        except Exception as e:
            logger.error(f"Failed to find duplicates: {e}")
            return []
            
    async def find_stale_documents(self, days: int = 90) -> List[Dict[str, Any]]:
        """Find documents that haven't been updated recently.
        
        Args:
            days: Number of days to consider as stale
            
        Returns:
            List of stale documents
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            cutoff_str = cutoff_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            
            results = self.search_client.search(
                search_text="*",
                filter=f"last_modified lt {cutoff_str}",
                select=["id", "file_path", "repository", "last_modified"],
                order_by=["last_modified asc"],
                top=100
            )
            
            stale_docs = []
            for doc in results:
                stale_docs.append({
                    "id": doc["id"],
                    "file_path": doc.get("file_path", "Unknown"),
                    "repository": doc.get("repository", "Unknown"),
                    "last_modified": doc.get("last_modified", "Unknown"),
                    "age_days": (datetime.utcnow() - doc.get("last_modified", datetime.utcnow())).days
                })
                
            return stale_docs
            
        except Exception as e:
            logger.error(f"Failed to find stale documents: {e}")
            return []
            
    async def optimize_index(self) -> Dict[str, Any]:
        """Analyze and provide optimization recommendations.
        
        Returns:
            Dict with optimization recommendations
        """
        recommendations = []
        
        try:
            # Get index info
            stats = await self.get_index_statistics()
            doc_stats = await self.get_document_statistics()
            
            # Check document count
            if stats.document_count == 0:
                recommendations.append({
                    "type": "warning",
                    "message": "Index is empty - run indexing to populate"
                })
            elif stats.document_count > 50000:
                recommendations.append({
                    "type": "info",
                    "message": f"Large index with {stats.document_count} documents - consider partitioning"
                })
                
            # Check for duplicates
            duplicates = await self.find_duplicates()
            if duplicates:
                total_dupes = sum(d['count'] - 1 for d in duplicates)
                recommendations.append({
                    "type": "warning",
                    "message": f"Found {total_dupes} potential duplicate documents"
                })
                
            # Check for stale documents
            stale_docs = await self.find_stale_documents()
            if stale_docs:
                recommendations.append({
                    "type": "info",
                    "message": f"Found {len(stale_docs)} documents older than 90 days"
                })
                
            # Check field usage
            if stats.vector_fields and not any(vf == "content_vector" for vf in stats.vector_fields):
                recommendations.append({
                    "type": "warning",
                    "message": "Vector field 'content_vector' not found - vector search may not work"
                })
                
            # Repository balance
            if doc_stats.repository_counts:
                max_repo_count = max(doc_stats.repository_counts.values())
                min_repo_count = min(doc_stats.repository_counts.values())
                if max_repo_count > 10 * min_repo_count:
                    recommendations.append({
                        "type": "info",
                        "message": "Large imbalance in repository document counts"
                    })
                    
            return {
                "index_stats": stats.__dict__,
                "document_stats": {
                    "total": doc_stats.total_count,
                    "repositories": doc_stats.repository_counts,
                    "languages": doc_stats.language_counts
                },
                "recommendations": recommendations
            }
            
        except Exception as e:
            logger.error(f"Failed to optimize index: {e}")
            return {"error": str(e)}
            
    async def export_index_data(self, output_path: str, sample_size: Optional[int] = None) -> bool:
        """Export index data to a JSON file.
        
        Args:
            output_path: Path to save the export
            sample_size: Number of documents to export (None for all)
            
        Returns:
            bool: True if successful
        """
        try:
            documents = []
            batch_size = 100
            skip = 0
            
            while True:
                if sample_size and len(documents) >= sample_size:
                    break
                    
                results = list(self.search_client.search(
                    search_text="*",
                    top=batch_size,
                    skip=skip,
                    search_mode=SearchMode.ALL
                ))
                
                if not results:
                    break
                    
                for doc in results:
                    # Remove internal fields
                    doc.pop('@search.score', None)
                    doc.pop('@search.highlights', None)
                    documents.append(doc)
                    
                    if sample_size and len(documents) >= sample_size:
                        break
                        
                skip += batch_size
                
            # Save to file
            export_data = {
                "export_date": datetime.utcnow().isoformat(),
                "index_name": self.index_name,
                "document_count": len(documents),
                "documents": documents
            }
            
            with open(output_path, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
                
            logger.info(f"Exported {len(documents)} documents to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export index data: {e}")
            return False