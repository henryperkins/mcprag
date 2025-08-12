"""Reindexing automation for Azure AI Search.

This module provides the unified reindexing interface using REST operations
only. It replaces legacy SDK-based flows and removes the dependency on
ReindexOperations.
"""

import logging
import warnings
from typing import Dict, Any, Optional, List, AsyncIterator, Iterable
from datetime import datetime
from pathlib import Path
import json

from ..rest import SearchOperations
from ..processing import FileProcessor
from .data_manager import DataAutomation
from .index_manager import IndexAutomation
from .indexer_manager import IndexerAutomation
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
        self.embedding_provider = embedding_provider
        self._index_default_name = None
        try:
            # Try to resolve default index name from core config if available
            from enhanced_rag.core.config import get_config  # type: ignore
            self._index_default_name = get_config().azure.index_name
        except Exception:
            import os
            self._index_default_name = os.getenv("ACS_INDEX_NAME", "codebase-mcp-sota")
    
    async def get_index_health(self, index_name: Optional[str] = None) -> Dict[str, Any]:
        """Get comprehensive index health information.
        
        Args:
            index_name: Optional index name (uses default if not provided)
            
        Returns:
            Dict with index health metrics
        """
        index = index_name or self._index_default_name

        # Basic info
        try:
            index_def = await self.ops.get_index(index)
            stats = await self.ops.get_index_stats(index)
        except Exception as e:
            logger.error(f"Failed to get index info: {e}")
            return {
                "name": index,
                "error": str(e)
            }

        # Validation
        validation = await self._validate_index_schema(index)
        
        # Get additional stats from REST API
        try:
            stats = await self.ops.get_index_stats(index)
        except Exception as e:
            logger.warning(f"Failed to get index stats: {e}")
            stats = {}
        
        return {
            "name": index_def.get("name", index),
            "document_count": stats.get("documentCount", 0),
            "storage_size_bytes": stats.get("storageSize", 0),
            "field_count": len(index_def.get("fields", [])),
            "vector_search_enabled": bool(index_def.get("vectorSearch")),
            "semantic_search_enabled": bool(index_def.get("semantic")),
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
            index = self._index_default_name

            if dry_run:
                if method == "drop-rebuild":
                    if schema_path and not Path(schema_path).exists():
                        raise ValueError(f"Schema file not found: {schema_path}")
                    result["action"] = "Would drop and rebuild index"
                    result["index_name"] = index
                    if schema_path:
                        result["schema_file"] = schema_path
                elif method == "clear":
                    stats = await self.ops.get_index_stats(index)
                    result["action"] = f"Would clear {stats.get('documentCount', 0)} documents"
                    result["index_name"] = index
                    if clear_filter:
                        result["filter"] = clear_filter
                elif method == "repository":
                    if not repo_path or not repo_name:
                        raise ValueError("Repository path and name required")
                    result["action"] = f"Would reindex repository {repo_name} from {repo_path}"
                    result["index_name"] = index
                else:
                    raise ValueError(f"Unknown reindexing method: {method}")
                result["status"] = "validated"
            else:
                if method == "drop-rebuild":
                    # Load schema from file or fetch current
                    if schema_path and Path(schema_path).exists():
                        schema = json.loads(Path(schema_path).read_text())
                    else:
                        schema = await self.ops.get_index(index)
                    schema["name"] = index

                    # Recreate via REST
                    try:
                        await self.ops.delete_index(index)
                    except Exception:
                        pass
                    await self.ops.create_index(schema)
                    result["status"] = "success"
                    result["rebuild_complete"] = True
                elif method == "clear":
                    count = await self._clear_documents(index, clear_filter)
                    result["status"] = "success"
                    result["documents_cleared"] = count
                elif method == "repository":
                    if not repo_path or not repo_name:
                        raise ValueError("Repository path and name required")
                    # Optional clear step if caller provided clear_filter through kwargs
                    if clear_filter:
                        await self._clear_documents(index, clear_filter)

                    succeeded = await self._reindex_repository(index, repo_path, repo_name)
                    result["status"] = "success" if succeeded else "failed"
                    result["repository"] = repo_name
                    result["documents_uploaded"] = succeeded
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
            
            success = await self._backup_index_schema(self._index_default_name, backup_path)
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
            
            # Recreate index with backed-up schema
            try:
                await self.ops.delete_index(self._index_default_name)
            except Exception:
                pass
            await self.ops.create_index(schema)
            success = True
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

    # ===== Internal helpers =====

    async def _validate_index_schema(self, index_name: str) -> Dict[str, Any]:
        """Validate the current index schema and surface issues/warnings."""
        try:
            index = await self.ops.get_index(index_name)
        except Exception as e:
            return {"valid": False, "error": str(e), "issues": [str(e)], "warnings": []}

        issues: List[str] = []
        warnings_list: List[str] = []

        fields = index.get("fields", [])
        field_names = {f.get("name") for f in fields}
        required_fields = {"id", "file_path", "repository", "content"}
        missing = required_fields - field_names
        if missing:
            issues.append(f"Missing required fields: {sorted(missing)}")

        # Vector config checks
        if index.get("vectorSearch"):
            vector_fields = [f for f in fields if f.get("dimensions")]
            if not vector_fields:
                warnings_list.append("Vector search enabled but no vector fields found")
            else:
                try:
                    from enhanced_rag.core.config import get_config  # type: ignore
                    expected_dims = getattr(get_config().azure, "embedding_dimensions", 1536)
                except Exception:
                    expected_dims = 1536
                for vf in vector_fields:
                    if vf.get("name") == "content_vector" and vf.get("dimensions") != expected_dims:
                        warnings_list.append(
                            f"content_vector dimensions {vf.get('dimensions')} != expected {expected_dims}"
                        )

        # Field attribute checks
        for f in fields:
            if f.get("name") == "file_path" and not f.get("filterable", False):
                warnings_list.append("Field 'file_path' should be filterable")
            if f.get("name") == "repository" and not f.get("facetable", False):
                warnings_list.append("Field 'repository' should be facetable")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings_list,
        }

    async def _clear_documents(self, index_name: str, filter_query: Optional[str]) -> int:
        """Clear documents by fetching keys and deleting in batches."""
        total_deleted = 0
        top = 1000
        skip = 0
        while True:
            options = {
                "select": ["id"],
                "top": top,
                "skip": skip,
                "count": True,
            }
            if filter_query:
                options["filter"] = filter_query
            results = await self.ops.search(index_name, "*", **options)
            docs = [d.get("id") for d in results.get("value", []) if d.get("id")]
            if not docs:
                break
            await self.ops.delete_documents(index_name, docs)
            total_deleted += len(docs)
            skip += top
        return total_deleted

    async def _reindex_repository(self, index_name: str, repo_path: str, repo_name: str) -> int:
        """Process a repository and upload documents in batches."""
        processor = FileProcessor()
        docs = processor.process_repository(repo_path, repo_name)

        data_automation = DataAutomation(self.ops)

        async def gen() -> AsyncIterator[Dict[str, Any]]:
            for d in docs:
                yield d

        result = await data_automation.bulk_upload(index_name=index_name, documents=gen(), batch_size=100)
        return result.get("succeeded", 0)

    async def _backup_index_schema(self, index_name: str, output_path: str) -> bool:
        try:
            index = await self.ops.get_index(index_name)
            # Remove known metadata keys if present
            for key in ("@odata.context", "@odata.etag", "etag", "e_tag"):
                index.pop(key, None)
            index["_backup_metadata"] = {
                "timestamp": datetime.utcnow().isoformat(),
                "index_name": index_name,
            }
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(index, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to backup schema: {e}")
            return False
