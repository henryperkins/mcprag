"""Automated indexer management for Azure AI Search."""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import asyncio

from ..rest import SearchOperations
from ..rest.models import (
    create_indexer_schedule,
    create_blob_datasource,
    create_sql_datasource,
    create_text_split_skill,
    create_language_detection_skill,
    create_entity_recognition_skill
)

logger = logging.getLogger(__name__)


class IndexerAutomation:
    """Automate indexer and data source management tasks."""
    
    def __init__(self, operations: SearchOperations):
        """Initialize indexer automation.
        
        Args:
            operations: SearchOperations instance
        """
        self.ops = operations
    
    async def create_blob_indexer_pipeline(
        self,
        name_prefix: str,
        index_name: str,
        connection_string: str,
        container_name: str,
        schedule_hours: int = 1,
        skillset_definition: Optional[Dict[str, Any]] = None,
        query: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a complete blob indexing pipeline.
        
        Args:
            name_prefix: Prefix for naming resources
            index_name: Target index name
            connection_string: Storage connection string
            container_name: Container name
            schedule_hours: Schedule interval in hours
            skillset_definition: Optional skillset definition
            query: Optional blob query/prefix
            
        Returns:
            Created resource names and status
        """
        datasource_name = f"{name_prefix}-datasource"
        indexer_name = f"{name_prefix}-indexer"
        skillset_name = f"{name_prefix}-skillset" if skillset_definition else None
        
        created_resources = {
            "datasource": None,
            "skillset": None,
            "indexer": None,
            "errors": []
        }
        
        try:
            # Create data source
            datasource = create_blob_datasource(
                name=datasource_name,
                connection_string=connection_string,
                container_name=container_name,
                query=query
            )
            
            await self.ops.create_datasource(datasource)
            created_resources["datasource"] = datasource_name
            logger.info(f"Created data source: {datasource_name}")
            
            # Create skillset if provided
            if skillset_definition:
                skillset_definition["name"] = skillset_name
                await self.ops.create_skillset(skillset_definition)
                created_resources["skillset"] = skillset_name
                logger.info(f"Created skillset: {skillset_name}")
            
            # Create indexer
            indexer_def = {
                "name": indexer_name,
                "dataSourceName": datasource_name,
                "targetIndexName": index_name,
                "schedule": create_indexer_schedule(f"PT{schedule_hours}H"),
                "parameters": {
                    "configuration": {
                        "indexStorageMode": "default",
                        "parsingMode": "default",
                        "maxFailedItems": 0,
                        "maxFailedItemsPerBatch": 0
                    }
                }
            }
            
            if skillset_name:
                indexer_def["skillsetName"] = skillset_name
            
            await self.ops.create_indexer(indexer_def)
            created_resources["indexer"] = indexer_name
            logger.info(f"Created indexer: {indexer_name}")
            
            # Run indexer immediately
            await self.ops.run_indexer(indexer_name)
            logger.info(f"Started initial run of indexer: {indexer_name}")
            
        except Exception as e:
            logger.error(f"Error creating pipeline: {e}")
            created_resources["errors"].append(str(e))
            
            # Cleanup on failure
            await self._cleanup_failed_pipeline(created_resources)
            raise
        
        return created_resources
    
    async def create_sql_indexer_pipeline(
        self,
        name_prefix: str,
        index_name: str,
        connection_string: str,
        table_or_view: str,
        schedule_hours: int = 1,
        change_detection_column: Optional[str] = None,
        delete_detection_column: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a complete SQL indexing pipeline.
        
        Args:
            name_prefix: Prefix for naming resources
            index_name: Target index name
            connection_string: SQL connection string
            table_or_view: Table or view name
            schedule_hours: Schedule interval in hours
            change_detection_column: Column for change tracking
            delete_detection_column: Column for soft delete detection
            
        Returns:
            Created resource names and status
        """
        datasource_name = f"{name_prefix}-datasource"
        indexer_name = f"{name_prefix}-indexer"
        
        # Setup change detection if specified
        change_detection_policy = None
        if change_detection_column:
            change_detection_policy = {
                "@odata.type": "#Microsoft.Azure.Search.HighWaterMarkChangeDetectionPolicy",
                "highWaterMarkColumnName": change_detection_column
            }
        
        # Setup delete detection if specified
        delete_detection_policy = None
        if delete_detection_column:
            delete_detection_policy = {
                "@odata.type": "#Microsoft.Azure.Search.SoftDeleteColumnDeletionDetectionPolicy",
                "softDeleteColumnName": delete_detection_column,
                "softDeleteMarkerValue": "true"
            }
        
        # Create data source
        datasource = create_sql_datasource(
            name=datasource_name,
            connection_string=connection_string,
            table_or_view=table_or_view,
            change_detection_policy=change_detection_policy,
            delete_detection_policy=delete_detection_policy
        )
        
        await self.ops.create_datasource(datasource)
        logger.info(f"Created SQL data source: {datasource_name}")
        
        # Create indexer
        indexer_def = {
            "name": indexer_name,
            "dataSourceName": datasource_name,
            "targetIndexName": index_name,
            "schedule": create_indexer_schedule(f"PT{schedule_hours}H")
        }
        
        await self.ops.create_indexer(indexer_def)
        logger.info(f"Created SQL indexer: {indexer_name}")
        
        # Run indexer
        await self.ops.run_indexer(indexer_name)
        
        return {
            "datasource": datasource_name,
            "indexer": indexer_name
        }
    
    async def monitor_indexer_health(
        self,
        indexer_name: str,
        lookback_hours: int = 24
    ) -> Dict[str, Any]:
        """Monitor indexer health and execution history.
        
        Args:
            indexer_name: Indexer to monitor
            lookback_hours: Hours to look back in history
            
        Returns:
            Health status and metrics
        """
        status = await self.ops.get_indexer_status(indexer_name)
        
        # Analyze execution history
        execution_history = status.get("executionHistory", [])
        cutoff_time = datetime.utcnow() - timedelta(hours=lookback_hours)
        
        recent_executions = []
        errors = []
        warnings = []
        success_count = 0
        failure_count = 0
        total_items_processed = 0
        total_items_failed = 0
        
        for execution in execution_history:
            start_time = execution.get("startTime")
            if start_time:
                # Parse ISO format datetime
                exec_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                if exec_time < cutoff_time:
                    continue
            
            recent_executions.append(execution)
            
            status_value = execution.get("status", "").lower()
            if status_value == "success":
                success_count += 1
            else:
                failure_count += 1
                
            # Collect errors
            if execution.get("errors"):
                for error in execution["errors"]:
                    errors.append({
                        "time": start_time,
                        "message": error.get("errorMessage", "Unknown error")
                    })
            
            # Collect warnings
            if execution.get("warnings"):
                for warning in execution["warnings"]:
                    warnings.append({
                        "time": start_time,
                        "message": warning.get("message", "Unknown warning")
                    })
            
            # Sum items processed
            items_processed = execution.get("itemsProcessed", 0)
            items_failed = execution.get("itemsFailed", 0)
            total_items_processed += items_processed
            total_items_failed += items_failed
        
        # Calculate health score
        total_executions = success_count + failure_count
        health_score = (success_count / total_executions * 100) if total_executions > 0 else 0
        
        # Determine status
        overall_status = "healthy"
        if health_score < 90:
            overall_status = "warning"
        if health_score < 70:
            overall_status = "critical"
        
        # Get current status
        current_status = status.get("status", "unknown")
        last_result = status.get("lastResult", {})
        
        return {
            "indexer_name": indexer_name,
            "current_status": current_status,
            "overall_health": overall_status,
            "health_score": round(health_score, 2),
            "lookback_hours": lookback_hours,
            "execution_summary": {
                "total": total_executions,
                "succeeded": success_count,
                "failed": failure_count,
                "items_processed": total_items_processed,
                "items_failed": total_items_failed
            },
            "last_execution": {
                "status": last_result.get("status"),
                "start_time": last_result.get("startTime"),
                "end_time": last_result.get("endTime"),
                "items_processed": last_result.get("itemsProcessed", 0),
                "items_failed": last_result.get("itemsFailed", 0)
            },
            "errors": errors[-10:],  # Last 10 errors
            "warnings": warnings[-10:],  # Last 10 warnings
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def optimize_indexer_schedule(
        self,
        indexer_name: str,
        target_freshness_minutes: int = 60
    ) -> Dict[str, Any]:
        """Optimize indexer schedule based on data change patterns.
        
        Args:
            indexer_name: Indexer to optimize
            target_freshness_minutes: Target data freshness in minutes
            
        Returns:
            Optimization recommendations
        """
        status = await self.ops.get_indexer_status(indexer_name)
        indexer_def = await self.ops.get_indexer(indexer_name)
        
        # Analyze execution patterns
        execution_history = status.get("executionHistory", [])[:20]  # Last 20 runs
        
        if len(execution_history) < 5:
            return {
                "recommendation": "insufficient_data",
                "message": "Need at least 5 execution runs to analyze patterns"
            }
        
        # Calculate average execution time
        execution_times = []
        items_per_run = []
        
        for execution in execution_history:
            start = execution.get("startTime")
            end = execution.get("endTime")
            
            if start and end:
                start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
                duration = (end_dt - start_dt).total_seconds()
                execution_times.append(duration)
            
            items = execution.get("itemsProcessed", 0)
            items_per_run.append(items)
        
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
        avg_items_per_run = sum(items_per_run) / len(items_per_run) if items_per_run else 0
        
        # Current schedule
        current_schedule = indexer_def.get("schedule", {})
        current_interval = current_schedule.get("interval", "PT1H")
        
        # Parse interval (simple parsing for PT format)
        current_minutes = 60  # Default 1 hour
        if current_interval.startswith("PT"):
            if "H" in current_interval:
                hours = int(current_interval[2:current_interval.index("H")])
                current_minutes = hours * 60
            elif "M" in current_interval:
                current_minutes = int(current_interval[2:current_interval.index("M")])
        
        # Recommendations
        recommendations = []
        
        # If execution time is more than 50% of interval, increase interval
        if avg_execution_time > (current_minutes * 60 * 0.5):
            recommended_minutes = max(current_minutes * 2, int(avg_execution_time / 60 * 2))
            recommendations.append({
                "type": "increase_interval",
                "reason": "Execution time is too long relative to schedule",
                "current_interval_minutes": current_minutes,
                "recommended_interval_minutes": recommended_minutes
            })
        
        # If very few items processed, decrease frequency
        if avg_items_per_run < 10 and current_minutes < 1440:  # Less than daily
            recommendations.append({
                "type": "decrease_frequency",
                "reason": "Very few items processed per run",
                "current_interval_minutes": current_minutes,
                "recommended_interval_minutes": min(current_minutes * 4, 1440)
            })
        
        # If target freshness requires more frequent runs
        if current_minutes > target_freshness_minutes:
            recommendations.append({
                "type": "increase_frequency",
                "reason": f"Current schedule doesn't meet {target_freshness_minutes} minute freshness target",
                "current_interval_minutes": current_minutes,
                "recommended_interval_minutes": target_freshness_minutes
            })
        
        return {
            "indexer_name": indexer_name,
            "analysis": {
                "avg_execution_seconds": round(avg_execution_time, 2),
                "avg_items_per_run": round(avg_items_per_run, 2),
                "current_interval_minutes": current_minutes
            },
            "recommendations": recommendations,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def create_text_processing_skillset(
        self,
        name: str,
        include_language_detection: bool = True,
        include_entity_recognition: bool = True,
        include_text_split: bool = True,
        text_split_page_length: int = 5000
    ) -> Dict[str, Any]:
        """Create a common text processing skillset.
        
        Args:
            name: Skillset name
            include_language_detection: Include language detection
            include_entity_recognition: Include entity recognition
            include_text_split: Include text splitting
            text_split_page_length: Characters per page for splitting
            
        Returns:
            Created skillset definition
        """
        skills = []
        
        if include_text_split:
            skills.append(create_text_split_skill(
                name="text_split",
                maximum_page_length=text_split_page_length
            ))
        
        if include_language_detection:
            skills.append(create_language_detection_skill(
                name="language_detection"
            ))
        
        if include_entity_recognition:
            skills.append(create_entity_recognition_skill(
                name="entity_recognition",
                categories=["Person", "Organization", "Location"]
            ))
        
        skillset_def = {
            "name": name,
            "description": "Text processing skillset for common NLP tasks",
            "skills": skills
        }
        
        await self.ops.create_skillset(skillset_def)
        logger.info(f"Created text processing skillset: {name}")
        
        return skillset_def
    
    async def reset_and_run_indexer(
        self,
        indexer_name: str,
        wait_for_completion: bool = False,
        timeout_minutes: int = 30
    ) -> Dict[str, Any]:
        """Reset and run an indexer, optionally waiting for completion.
        
        Args:
            indexer_name: Indexer to reset and run
            wait_for_completion: Whether to wait for completion
            timeout_minutes: Timeout for waiting
            
        Returns:
            Execution result
        """
        # Reset the indexer
        await self.ops.reset_indexer(indexer_name)
        logger.info(f"Reset indexer: {indexer_name}")
        
        # Run the indexer
        await self.ops.run_indexer(indexer_name)
        logger.info(f"Started indexer: {indexer_name}")
        
        if not wait_for_completion:
            return {
                "status": "started",
                "indexer_name": indexer_name
            }
        
        # Wait for completion
        start_time = datetime.utcnow()
        timeout = timedelta(minutes=timeout_minutes)
        
        while datetime.utcnow() - start_time < timeout:
            status = await self.ops.get_indexer_status(indexer_name)
            current_status = status.get("status", "").lower()
            
            if current_status in ["idle", "error"]:
                last_result = status.get("lastResult", {})
                return {
                    "status": "completed",
                    "indexer_name": indexer_name,
                    "final_status": last_result.get("status"),
                    "items_processed": last_result.get("itemsProcessed", 0),
                    "items_failed": last_result.get("itemsFailed", 0),
                    "execution_time": last_result.get("endTime")
                }
            
            await asyncio.sleep(10)  # Check every 10 seconds
        
        return {
            "status": "timeout",
            "indexer_name": indexer_name,
            "message": f"Execution exceeded {timeout_minutes} minute timeout"
        }
    
    async def _cleanup_failed_pipeline(self, created_resources: Dict[str, Any]):
        """Clean up resources from a failed pipeline creation.
        
        Args:
            created_resources: Dictionary of created resource names
        """
        if created_resources.get("indexer"):
            try:
                await self.ops.delete_indexer(created_resources["indexer"])
                logger.info(f"Cleaned up indexer: {created_resources['indexer']}")
            except:
                pass
        
        if created_resources.get("skillset"):
            try:
                await self.ops.delete_skillset(created_resources["skillset"])
                logger.info(f"Cleaned up skillset: {created_resources['skillset']}")
            except:
                pass
        
        if created_resources.get("datasource"):
            try:
                await self.ops.delete_datasource(created_resources["datasource"])
                logger.info(f"Cleaned up datasource: {created_resources['datasource']}")
            except:
                pass