"""Health monitoring for Azure AI Search service."""

import logging
from typing import Dict, Any, List
from datetime import datetime

from ..rest import SearchOperations

logger = logging.getLogger(__name__)


class HealthMonitor:
    """Monitor Azure AI Search service health."""
    
    def __init__(self, operations: SearchOperations):
        """Initialize health monitor.
        
        Args:
            operations: SearchOperations instance
        """
        self.ops = operations
    
    async def get_service_health(self) -> Dict[str, Any]:
        """Get overall service health status.
        
        Returns:
            Service health summary
        """
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "issues": []
        }
        
        try:
            # Get service statistics
            service_stats = await self.ops.get_service_statistics()
            
            # Check resource usage
            counters = service_stats.get("counters", {})
            limits = service_stats.get("limits", {})
            
            # Check index count
            index_usage = counters.get("indexesCount", 0)
            index_limit = limits.get("maxIndexesPerService", 0)
            
            if index_limit > 0 and index_usage >= index_limit:
                health_status["status"] = "critical"
                health_status["issues"].append({
                    "type": "index_limit",
                    "message": f"Index limit reached: {index_usage}/{index_limit}"
                })
            elif index_limit > 0 and index_usage >= index_limit * 0.9:
                health_status["status"] = "warning"
                health_status["issues"].append({
                    "type": "index_limit",
                    "message": f"Approaching index limit: {index_usage}/{index_limit}"
                })
            
            health_status["service_stats"] = {
                "indexes": f"{index_usage}/{index_limit}",
                "indexers": f"{counters.get('indexersCount', 0)}/{limits.get('maxIndexersPerService', 0)}",
                "datasources": f"{counters.get('dataSourcesCount', 0)}/{limits.get('maxDataSourcesPerService', 0)}",
                "skillsets": f"{counters.get('skillsetsCount', 0)}/{limits.get('maxSkillsetsPerService', 0)}"
            }
            
        except Exception as e:
            health_status["status"] = "error"
            health_status["issues"].append({
                "type": "service_error",
                "message": f"Failed to get service statistics: {str(e)}"
            })
        
        return health_status
    
    async def check_indexes_health(self) -> List[Dict[str, Any]]:
        """Check health of all indexes.
        
        Returns:
            List of index health statuses
        """
        indexes_health = []
        
        try:
            indexes = await self.ops.list_indexes(select=["name"])
            
            for index in indexes:
                index_name = index["name"]
                try:
                    stats = await self.ops.get_index_stats(index_name)
                    
                    health = {
                        "name": index_name,
                        "status": "healthy",
                        "documentCount": stats.get("documentCount", 0),
                        "storageSizeMB": round(stats.get("storageSize", 0) / (1024 * 1024), 2)
                    }
                    
                    # Check for potential issues
                    if stats.get("documentCount", 0) == 0:
                        health["status"] = "warning"
                        health["message"] = "Index is empty"
                    
                    indexes_health.append(health)
                    
                except Exception as e:
                    indexes_health.append({
                        "name": index_name,
                        "status": "error",
                        "message": str(e)
                    })
                    
        except Exception as e:
            logger.error(f"Failed to check indexes health: {e}")
            
        return indexes_health
    
    async def check_indexers_health(self) -> List[Dict[str, Any]]:
        """Check health of all indexers.
        
        Returns:
            List of indexer health statuses
        """
        indexers_health = []
        
        try:
            indexers = await self.ops.list_indexers(select=["name"])
            
            for indexer in indexers:
                indexer_name = indexer["name"]
                try:
                    status = await self.ops.get_indexer_status(indexer_name)
                    last_result = status.get("lastResult", {})
                    
                    health = {
                        "name": indexer_name,
                        "status": status.get("status", "unknown"),
                        "lastRunStatus": last_result.get("status", "none"),
                        "lastRunTime": last_result.get("endTime")
                    }
                    
                    # Check for errors
                    if last_result.get("status") == "failed":
                        health["status"] = "error"
                        health["message"] = "Last run failed"
                    elif last_result.get("itemsFailed", 0) > 0:
                        health["status"] = "warning"
                        health["message"] = f"{last_result['itemsFailed']} items failed"
                    
                    indexers_health.append(health)
                    
                except Exception as e:
                    indexers_health.append({
                        "name": indexer_name,
                        "status": "error",
                        "message": str(e)
                    })
                    
        except Exception as e:
            logger.error(f"Failed to check indexers health: {e}")
            
        return indexers_health
    
    async def get_full_health_report(self) -> Dict[str, Any]:
        """Get comprehensive health report.
        
        Returns:
            Full health report
        """
        service_health = await self.get_service_health()
        indexes_health = await self.check_indexes_health()
        indexers_health = await self.check_indexers_health()
        
        # Determine overall status
        overall_status = "healthy"
        
        if service_health["status"] == "critical":
            overall_status = "critical"
        elif service_health["status"] == "error" or any(idx["status"] == "error" for idx in indexes_health + indexers_health):
            overall_status = "error"
        elif service_health["status"] == "warning" or any(idx["status"] == "warning" for idx in indexes_health + indexers_health):
            overall_status = "warning"
        
        return {
            "overall_status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "service": service_health,
            "indexes": indexes_health,
            "indexers": indexers_health
        }