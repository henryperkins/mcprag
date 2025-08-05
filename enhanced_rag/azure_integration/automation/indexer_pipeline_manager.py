"""Comprehensive indexer pipeline management for Azure AI Search."""

import json
import logging
import os
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import asyncio

from ..rest.operations import SearchOperations
from ..config import UnifiedConfig, ClientFactory

logger = logging.getLogger(__name__)


class IndexerPipelineManager:
    """Manages complete indexer pipeline deployment and operations."""
    
    def __init__(self, config: Optional[UnifiedConfig] = None):
        """Initialize indexer pipeline manager."""
        self.config = config or UnifiedConfig.from_env()
        self.operations = ClientFactory.create_operations(self.config.azure_search)
        
    async def deploy_pipeline(
        self,
        datasource_config_path: str = "azure_indexer_datasource.json",
        skillset_config_path: str = "azure_indexer_skillset.json", 
        indexer_config_path: str = "azure_indexer_main.json",
        validate_only: bool = False,
        auto_run: bool = True
    ) -> Dict[str, Any]:
        """Deploy complete indexer pipeline from configuration files."""
        logger.info("Starting indexer pipeline deployment")
        
        deployment_result = {
            "status": "success",
            "components": {
                "datasource": {"name": None, "status": "pending"},
                "skillset": {"name": None, "status": "pending"},
                "indexer": {"name": None, "status": "pending"}
            },
            "validation_errors": [],
            "deployment_errors": [],
            "execution_status": None,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            # Load and validate configurations
            configs = await self._load_and_validate_configs(
                datasource_config_path,
                skillset_config_path,
                indexer_config_path
            )
            
            if configs["validation_errors"]:
                deployment_result["validation_errors"] = configs["validation_errors"]
                deployment_result["status"] = "validation_failed"
                return deployment_result
            
            if validate_only:
                deployment_result["status"] = "validation_success"
                return deployment_result
            
            # Deploy components in order
            await self._deploy_datasource(configs["datasource"], deployment_result)
            await self._deploy_skillset(configs["skillset"], deployment_result)
            await self._deploy_indexer(configs["indexer"], deployment_result)
            
            # Run indexer if requested
            if auto_run and deployment_result["status"] == "success":
                indexer_name = configs["indexer"]["name"]
                await self._run_indexer(indexer_name, deployment_result)
            
            logger.info("Indexer pipeline deployment completed successfully")
            
        except Exception as e:
            logger.error(f"Pipeline deployment failed: {e}")
            deployment_result["status"] = "failed"
            deployment_result["deployment_errors"].append(str(e))
        
        return deployment_result
    
    async def _load_and_validate_configs(
        self,
        datasource_path: str,
        skillset_path: str,
        indexer_path: str
    ) -> Dict[str, Any]:
        """Load and validate all configuration files."""
        result = {
            "datasource": None,
            "skillset": None,
            "indexer": None,
            "validation_errors": []
        }
        
        # Load configurations
        try:
            with open(datasource_path, 'r') as f:
                result["datasource"] = json.load(f)
        except Exception as e:
            result["validation_errors"].append(f"Failed to load datasource config: {e}")
        
        try:
            with open(skillset_path, 'r') as f:
                result["skillset"] = json.load(f)
        except Exception as e:
            result["validation_errors"].append(f"Failed to load skillset config: {e}")
        
        try:
            with open(indexer_path, 'r') as f:
                result["indexer"] = json.load(f)
        except Exception as e:
            result["validation_errors"].append(f"Failed to load indexer config: {e}")
        
        # Validate configurations
        if result["datasource"]:
            await self._validate_datasource_config(result["datasource"], result["validation_errors"])
        
        if result["skillset"]:
            await self._validate_skillset_config(result["skillset"], result["validation_errors"])
        
        if result["indexer"]:
            await self._validate_indexer_config(result["indexer"], result["validation_errors"])
        
        return result
    
    async def _validate_datasource_config(self, config: Dict[str, Any], errors: List[str]):
        """Validate data source configuration."""
        required_fields = ["name", "type", "credentials", "container"]
        for field in required_fields:
            if field not in config:
                errors.append(f"Datasource missing required field: {field}")
    
    async def _validate_skillset_config(self, config: Dict[str, Any], errors: List[str]):
        """Validate skillset configuration."""
        required_fields = ["name", "skills"]
        for field in required_fields:
            if field not in config:
                errors.append(f"Skillset missing required field: {field}")
    
    async def _validate_indexer_config(self, config: Dict[str, Any], errors: List[str]):
        """Validate indexer configuration."""
        required_fields = ["name", "dataSourceName", "targetIndexName"]
        for field in required_fields:
            if field not in config:
                errors.append(f"Indexer missing required field: {field}")
    
    async def _deploy_datasource(self, config: Dict[str, Any], result: Dict[str, Any]):
        """Deploy data source component."""
        try:
            # Replace placeholders with environment variables
            storage_conn = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
            if storage_conn and "credentials" in config:
                config["credentials"]["connectionString"] = storage_conn
            
            await self.operations.create_datasource(config)
            result["components"]["datasource"]["name"] = config["name"]
            result["components"]["datasource"]["status"] = "success"
            logger.info(f"Successfully deployed data source: {config['name']}")
            
        except Exception as e:
            error_msg = f"Failed to deploy data source: {e}"
            result["deployment_errors"].append(error_msg)
            result["components"]["datasource"]["status"] = "failed"
            result["status"] = "partial_failure"
            logger.error(error_msg)
    
    async def _deploy_skillset(self, config: Dict[str, Any], result: Dict[str, Any]):
        """Deploy skillset component."""
        try:
            # Replace cognitive services key placeholder
            cog_key = os.getenv('AZURE_COGNITIVE_SERVICES_KEY')
            if cog_key and "cognitiveServices" in config:
                config["cognitiveServices"]["key"] = cog_key
            
            await self.operations.create_skillset(config)
            result["components"]["skillset"]["name"] = config["name"]
            result["components"]["skillset"]["status"] = "success"
            logger.info(f"Successfully deployed skillset: {config['name']}")
            
        except Exception as e:
            error_msg = f"Failed to deploy skillset: {e}"
            result["deployment_errors"].append(error_msg)
            result["components"]["skillset"]["status"] = "failed"
            result["status"] = "partial_failure"
            logger.error(error_msg)
    
    async def _deploy_indexer(self, config: Dict[str, Any], result: Dict[str, Any]):
        """Deploy indexer component."""
        try:
            await self.operations.create_indexer(config)
            result["components"]["indexer"]["name"] = config["name"]
            result["components"]["indexer"]["status"] = "success"
            logger.info(f"Successfully deployed indexer: {config['name']}")
            
        except Exception as e:
            error_msg = f"Failed to deploy indexer: {e}"
            result["deployment_errors"].append(error_msg)
            result["components"]["indexer"]["status"] = "failed"
            result["status"] = "partial_failure"
            logger.error(error_msg)
    
    async def _run_indexer(self, indexer_name: str, result: Dict[str, Any]):
        """Run the indexer and update execution status."""
        try:
            await self.operations.run_indexer(indexer_name)
            
            # Wait a moment and check status
            await asyncio.sleep(2)
            status = await self.operations.get_indexer_status(indexer_name)
            
            result["execution_status"] = {
                "indexer_name": indexer_name,
                "status": status.get("status", "unknown"),
                "started": True,
                "last_result": status.get("lastResult", {})
            }
            
            logger.info(f"Successfully started indexer: {indexer_name}")
            
        except Exception as e:
            error_msg = f"Failed to run indexer: {e}"
            result["deployment_errors"].append(error_msg)
            result["execution_status"] = {
                "indexer_name": indexer_name,
                "status": "failed_to_start",
                "started": False,
                "error": str(e)
            }
            logger.error(error_msg)
