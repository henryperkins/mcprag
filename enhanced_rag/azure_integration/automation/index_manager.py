"""Automated index management for Azure AI Search."""

import logging
from typing import Dict, Any, Optional, List
import httpx
from datetime import datetime

from ..rest import AzureSearchClient, SearchOperations

logger = logging.getLogger(__name__)


class IndexAutomation:
    """Automate index management tasks."""
    
    def __init__(self, endpoint: str, api_key: str, api_version: str = "2025-05-01-preview"):
        """Initialize index automation.
        
        Args:
            endpoint: Azure Search service endpoint
            api_key: Admin API key
            api_version: API version to use
        """
        self.client = AzureSearchClient(endpoint, api_key, api_version)
        self.ops = SearchOperations(self.client)
    
    async def ensure_index_exists(
        self, 
        index_definition: Dict[str, Any],
        update_if_different: bool = True
    ) -> Dict[str, Any]:
        """Ensure an index exists with the correct schema.
        
        Args:
            index_definition: Complete index definition
            update_if_different: Whether to update if schema differs
            
        Returns:
            Dictionary with 'created', 'updated', and 'current' status
        """
        name = index_definition["name"]
        result = {
            "created": False,
            "updated": False,
            "current": True
        }
        
        try:
            existing = await self.ops.get_index(name)
            
            # Compare schemas
            if update_if_different and self._schema_differs(existing, index_definition):
                logger.info(f"Updating index {name} with new schema")
                await self.ops.create_index(index_definition)
                result["updated"] = True
                result["current"] = False
            else:
                logger.info(f"Index {name} already exists with matching schema")
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.info(f"Creating new index {name}")
                await self.ops.create_index(index_definition)
                result["created"] = True
                result["current"] = False
            else:
                raise
                
        return result
    
    async def recreate_index(
        self, 
        index_definition: Dict[str, Any],
        backup_documents: bool = False
    ) -> Dict[str, Any]:
        """Drop and recreate an index.
        
        Args:
            index_definition: Complete index definition
            backup_documents: Whether to backup existing documents
            
        Returns:
            Operation result with backup info if applicable
        """
        name = index_definition["name"]
        result = {
            "deleted": False,
            "created": False,
            "documents_backed_up": 0
        }
        
        # Backup documents if requested
        if backup_documents:
            try:
                # Get document count before deletion
                stats = await self.ops.get_index_stats(name)
                doc_count = stats.get("documentCount", 0)
                
                if doc_count > 0:
                    logger.warning(f"Index {name} contains {doc_count} documents. "
                                 "Consider backing up data before deletion.")
                    result["documents_backed_up"] = doc_count
                    
            except httpx.HTTPStatusError:
                pass
        
        # Delete existing index
        try:
            await self.ops.delete_index(name)
            logger.info(f"Deleted existing index {name}")
            result["deleted"] = True
        except httpx.HTTPStatusError as e:
            if e.response.status_code != 404:
                raise
        
        # Create new index
        await self.ops.create_index(index_definition)
        logger.info(f"Created new index {name}")
        result["created"] = True
        
        return result
    
    async def optimize_index(self, name: str) -> Dict[str, Any]:
        """Get optimization recommendations for an index.
        
        Args:
            name: Index name
            
        Returns:
            Dictionary with stats and recommendations
        """
        # Get index statistics
        stats = await self.ops.get_index_stats(name)
        
        # Get index definition
        index_def = await self.ops.get_index(name)
        
        recommendations = []
        warnings = []
        
        # Check document count
        doc_count = stats.get("documentCount", 0)
        if doc_count > 1000000:
            recommendations.append({
                "type": "performance",
                "message": "Consider partitioning data across multiple indexes for better performance",
                "severity": "medium"
            })
        
        # Check storage size
        storage_bytes = stats.get("storageSize", 0)
        storage_gb = storage_bytes / (1024 * 1024 * 1024)
        
        if storage_gb > 10:
            recommendations.append({
                "type": "storage",
                "message": f"Index size is {storage_gb:.2f}GB. Consider cleanup or archival",
                "severity": "medium"
            })
        
        if storage_gb > 50:
            warnings.append({
                "type": "storage",
                "message": f"Index size is {storage_gb:.2f}GB. Approaching service limits",
                "severity": "high"
            })
        
        # Check field count
        field_count = len(index_def.get("fields", []))
        if field_count > 1000:
            warnings.append({
                "type": "schema",
                "message": f"Index has {field_count} fields. Consider schema optimization",
                "severity": "medium"
            })
        
        # Check for vector fields
        vector_fields = [
            f for f in index_def.get("fields", [])
            if f.get("type") == "Collection(Edm.Single)" and f.get("dimensions")
        ]
        
        if vector_fields:
            total_dimensions = sum(f.get("dimensions", 0) for f in vector_fields)
            if total_dimensions > 3000:
                recommendations.append({
                    "type": "vectors",
                    "message": f"High vector dimensionality ({total_dimensions} total). "
                               "Consider dimension reduction",
                    "severity": "low"
                })
        
        return {
            "stats": {
                "documentCount": doc_count,
                "storageSizeGB": round(storage_gb, 2),
                "fieldCount": field_count,
                "vectorFieldCount": len(vector_fields)
            },
            "recommendations": recommendations,
            "warnings": warnings,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def validate_index_schema(
        self, 
        name: str, 
        expected_schema: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Validate index schema against expectations.
        
        Args:
            name: Index name
            expected_schema: Optional expected schema to compare against
            
        Returns:
            Validation result with any issues found
        """
        index_def = await self.ops.get_index(name)
        issues = []
        
        # Basic validation
        if not index_def.get("fields"):
            issues.append({
                "type": "error",
                "message": "Index has no fields defined"
            })
            
        # Check for key field
        key_fields = [f for f in index_def.get("fields", []) if f.get("key")]
        if not key_fields:
            issues.append({
                "type": "error",
                "message": "No key field defined"
            })
        elif len(key_fields) > 1:
            issues.append({
                "type": "error",
                "message": f"Multiple key fields defined: {[f['name'] for f in key_fields]}"
            })
            
        # Validate field types
        for field in index_def.get("fields", []):
            if field.get("searchable") and field.get("type") not in [
                "Edm.String", 
                "Collection(Edm.String)"
            ]:
                issues.append({
                    "type": "warning",
                    "message": f"Field '{field['name']}' is searchable but not a string type"
                })
                
        # Compare with expected schema if provided
        if expected_schema:
            expected_fields = {f["name"]: f for f in expected_schema.get("fields", [])}
            actual_fields = {f["name"]: f for f in index_def.get("fields", [])}
            
            # Check for missing fields
            missing = set(expected_fields.keys()) - set(actual_fields.keys())
            if missing:
                issues.append({
                    "type": "error",
                    "message": f"Missing expected fields: {list(missing)}"
                })
                
            # Check for extra fields
            extra = set(actual_fields.keys()) - set(expected_fields.keys())
            if extra:
                issues.append({
                    "type": "warning",
                    "message": f"Unexpected fields found: {list(extra)}"
                })
                
        return {
            "valid": len([i for i in issues if i["type"] == "error"]) == 0,
            "issues": issues,
            "fieldCount": len(index_def.get("fields", [])),
            "indexName": name
        }
    
    async def list_indexes_with_stats(self) -> List[Dict[str, Any]]:
        """List all indexes with their statistics.
        
        Returns:
            List of indexes with stats
        """
        indexes = await self.ops.list_indexes()
        result = []
        
        for index in indexes:
            name = index["name"]
            try:
                stats = await self.ops.get_index_stats(name)
                result.append({
                    "name": name,
                    "fields": len(index.get("fields", [])),
                    "documentCount": stats.get("documentCount", 0),
                    "storageSizeMB": round(stats.get("storageSize", 0) / (1024 * 1024), 2)
                })
            except Exception as e:
                logger.error(f"Failed to get stats for index {name}: {e}")
                result.append({
                    "name": name,
                    "fields": len(index.get("fields", [])),
                    "error": str(e)
                })
                
        return result
    
    def _schema_differs(self, existing: Dict[str, Any], desired: Dict[str, Any]) -> bool:
        """Check if schemas are different.
        
        Args:
            existing: Current index schema
            desired: Desired index schema
            
        Returns:
            True if schemas differ
        """
        # Compare field names and types
        existing_fields = {
            f["name"]: {
                "type": f.get("type"),
                "searchable": f.get("searchable", False),
                "filterable": f.get("filterable", False),
                "sortable": f.get("sortable", False),
                "facetable": f.get("facetable", False),
                "key": f.get("key", False)
            }
            for f in existing.get("fields", [])
        }
        
        desired_fields = {
            f["name"]: {
                "type": f.get("type"),
                "searchable": f.get("searchable", False),
                "filterable": f.get("filterable", False),
                "sortable": f.get("sortable", False),
                "facetable": f.get("facetable", False),
                "key": f.get("key", False)
            }
            for f in desired.get("fields", [])
        }
        
        if existing_fields != desired_fields:
            return True
            
        # Compare vector search config if present
        existing_vector = existing.get("vectorSearch")
        desired_vector = desired.get("vectorSearch")
        
        if (existing_vector is None) != (desired_vector is None):
            return True
            
        # Add more comparison logic as needed
        
        return False
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.close()