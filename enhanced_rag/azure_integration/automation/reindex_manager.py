"""Reindexing automation for Azure AI Search.

This module integrates reindexing operations into the automation framework,
providing streamlined access to drop-and-rebuild, incremental updates,
and repository-based reindexing strategies.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
import json

from ..rest import SearchOperations
from ..reindex_operations import ReindexOperations, ReindexMethod
from ..embedding_provider import IEmbeddingProvider

logger = logging.getLogger(__name__)


class ReindexAutomation:
    """Automate reindexing tasks for Azure AI Search."""
    
    def __init__(self, 
                 operations: SearchOperations,
                 embedding_provider: Optional[IEmbeddingProvider] = None):
        """Initialize reindex automation.
        
        Args:
            operations: SearchOperations instance
            embedding_provider: Optional embedding provider for vector generation
        """
        self.ops = operations
        self.reindex_ops = ReindexOperations()
        self.embedding_provider = embedding_provider
    
    async def get_index_health(self, index_name: Optional[str] = None) -> Dict[str, Any]:
        """Get comprehensive index health information.
        
        Args:
            index_name: Optional index name (uses default if not provided)
            
        Returns:
            Dict with index health metrics
        """
        info = await self.reindex_ops.get_index_info()
        validation = await self.reindex_ops.validate_index_schema()
        
        # Get additional stats from REST API
        try:
            stats = await self.ops.get_index_stats(index_name or self.reindex_ops.index_name)
        except Exception as e:
            logger.warning(f"Failed to get index stats: {e}")
            stats = {}
        
        return {
            "name": info.get("name"),
            "document_count": info.get("document_count", 0),
            "storage_size_bytes": stats.get("storageSize", 0),
            "field_count": info.get("fields", 0),
            "vector_search_enabled": info.get("vector_search", False),
            "semantic_search_enabled": info.get("semantic_search", False),
            "schema_valid": validation.get("valid", False),
            "schema_issues": validation.get("issues", []),
            "schema_warnings": validation.get("warnings", []),
            "last_check": datetime.utcnow().isoformat()
        }
    
    async def perform_reindex(
        self,
        method: str,
        repo_path: Optional[str] = None,
        repo_name: Optional[str] = None,
        schema_path: Optional[str] = None,
        clear_filter: Optional[str] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Perform reindexing with specified method.
        
        Args:
            method: Reindexing method (drop-rebuild, incremental, clear, repository)
            repo_path: Repository path for repository method
            repo_name: Repository name for repository method
            schema_path: Schema file path for drop-rebuild
            clear_filter: OData filter for clear method
            dry_run: If True, validate but don't execute
            
        Returns:
            Dict with reindexing results
        """
        start_time = datetime.utcnow()
        result = {
            "method": method,
            "start_time": start_time.isoformat(),
            "dry_run": dry_run
        }
        
        try:
            if dry_run:
                # Validate parameters without executing
                if method == "drop-rebuild":
                    if schema_path and not Path(schema_path).exists():
                        raise ValueError(f"Schema file not found: {schema_path}")
                    result["action"] = "Would drop and rebuild index"
                    if schema_path:
                        result["schema_file"] = schema_path
                
                elif method == "clear":
                    doc_count = self.reindex_ops.search_client.get_document_count()
                    result["action"] = f"Would clear {doc_count} documents"
                    if clear_filter:
                        result["filter"] = clear_filter
                
                elif method == "repository":
                    if not repo_path or not repo_name:
                        raise ValueError("Repository path and name required")
                    result["action"] = f"Would reindex repository {repo_name} from {repo_path}"
                
                result["status"] = "validated"
                
            else:
                # Execute reindexing
                if method == "drop-rebuild":
                    success = await self.reindex_ops.drop_and_rebuild(schema_path)
                    result["status"] = "success" if success else "failed"
                    result["rebuild_complete"] = success
                
                elif method == "clear":
                    count = await self.reindex_ops.clear_documents(clear_filter)
                    result["status"] = "success"
                    result["documents_cleared"] = count
                
                elif method == "repository":
                    if not repo_path or not repo_name:
                        raise ValueError("Repository path and name required")
                    
                    success = await self.reindex_ops.reindex_repository(
                        repo_path=repo_path,
                        repo_name=repo_name,
                        method=ReindexMethod.INCREMENTAL
                    )
                    result["status"] = "success" if success else "failed"
                    result["repository"] = repo_name
                
                else:
                    raise ValueError(f"Unknown reindexing method: {method}")
            
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            logger.error(f"Reindexing failed: {e}")
        
        result["end_time"] = datetime.utcnow().isoformat()
        result["duration_seconds"] = (datetime.utcnow() - start_time).total_seconds()
        
        return result
    
    async def create_scheduled_reindex(
        self,
        name: str,
        method: str,
        schedule_hours: int,
        **kwargs
    ) -> Dict[str, Any]:
        """Create a scheduled reindexing task.
        
        Args:
            name: Task name
            method: Reindexing method
            schedule_hours: Schedule interval in hours
            **kwargs: Additional parameters for reindexing
            
        Returns:
            Dict with task creation status
        """
        # This would integrate with Azure Functions or Logic Apps
        # For now, return a placeholder
        return {
            "name": name,
            "method": method,
            "schedule_hours": schedule_hours,
            "parameters": kwargs,
            "status": "not_implemented",
            "message": "Scheduled reindexing requires Azure Functions or Logic Apps setup"
        }
    
    async def backup_and_restore(
        self,
        action: str,
        backup_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Backup or restore index schema.
        
        Args:
            action: "backup" or "restore"
            backup_path: Path for backup file
            
        Returns:
            Dict with operation results
        """
        if action == "backup":
            if not backup_path:
                backup_path = f"index_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            success = await self.reindex_ops.backup_index_schema(backup_path)
            return {
                "action": "backup",
                "path": backup_path,
                "success": success
            }
        
        elif action == "restore":
            if not backup_path or not Path(backup_path).exists():
                raise ValueError("Valid backup file required for restore")
            
            # Load backup and restore
            with open(backup_path, 'r') as f:
                schema = json.load(f)
            
            # Remove backup metadata
            schema.pop('_backup_metadata', None)
            
            success = await self.reindex_ops.drop_and_rebuild(backup_path)
            return {
                "action": "restore",
                "path": backup_path,
                "success": success
            }
        
        else:
            raise ValueError(f"Invalid action: {action}")
    
    async def analyze_reindex_need(self, threshold_days: int = 30) -> Dict[str, Any]:
        """Analyze if reindexing is needed based on various metrics.
        
        Args:
            threshold_days: Age threshold for stale documents
            
        Returns:
            Dict with analysis results and recommendations
        """
        recommendations = []
        health = await self.get_index_health()
        
        # Check schema validity
        if not health["schema_valid"]:
            recommendations.append({
                "priority": "high",
                "action": "drop-rebuild",
                "reason": f"Schema validation failed: {', '.join(health['schema_issues'])}"
            })
        
        # Check for schema warnings
        if health["schema_warnings"]:
            recommendations.append({
                "priority": "medium",
                "action": "schema-update",
                "reason": f"Schema warnings: {', '.join(health['schema_warnings'])}"
            })
        
        # Check document count
        if health["document_count"] == 0:
            recommendations.append({
                "priority": "high",
                "action": "repository",
                "reason": "Index is empty"
            })
        
        # Storage size analysis (example threshold: 10GB)
        if health["storage_size_bytes"] > 10 * 1024 * 1024 * 1024:
            recommendations.append({
                "priority": "low",
                "action": "optimize",
                "reason": "Index size exceeds 10GB, consider optimization"
            })
        
        return {
            "needs_reindex": len([r for r in recommendations if r["priority"] == "high"]) > 0,
            "health_summary": health,
            "recommendations": recommendations,
            "analysis_time": datetime.utcnow().isoformat()
        }