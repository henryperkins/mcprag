"""Automated index management for Azure AI Search."""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..rest import AzureSearchClient, SearchOperations
from ..lib import (
    ensure_index_exists as lib_ensure_index,
    recreate_index as lib_recreate_index,
    schema_differs,
    validate_index_schema as lib_validate_schema
)

logger = logging.getLogger(__name__)


class IndexAutomation:
    """Automate index management tasks."""
    
    def __init__(self, endpoint: str, api_key: str, api_version: Optional[str] = None):
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
        # Delegate to shared helper
        return await lib_ensure_index(self.ops, index_definition, update_if_different)
    
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
        # Delegate to shared helper
        return await lib_recreate_index(self.ops, index_definition, backup_documents)
    
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
        
        # Use shared validation helper for basic validation
        validation_result = lib_validate_schema(index_def)
        
        # Add additional validation if expected schema provided
        if expected_schema:
            expected_fields = {f["name"]: f for f in expected_schema.get("fields", [])}
            actual_fields = {f["name"]: f for f in index_def.get("fields", [])}
            
            # Check for missing fields
            missing = set(expected_fields.keys()) - set(actual_fields.keys())
            if missing:
                validation_result["issues"].append(
                    f"Missing expected fields: {sorted(missing)}"
                )
                validation_result["valid"] = False
                
            # Check for extra fields
            extra = set(actual_fields.keys()) - set(expected_fields.keys())
            if extra:
                validation_result["warnings"].append(
                    f"Unexpected fields found: {sorted(extra)}"
                )
        
        # Add index name and field count to result
        validation_result["indexName"] = name
        validation_result["fieldCount"] = len(index_def.get("fields", []))
        
        return validation_result
    
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
    
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.close()