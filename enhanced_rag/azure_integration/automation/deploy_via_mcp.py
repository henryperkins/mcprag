"""Deploy indexer configuration via MCP tools integration."""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from enhanced_rag.azure_integration.automation.indexer_pipeline_manager import IndexerPipelineManager
from enhanced_rag.azure_integration import UnifiedConfig

class MCPIndexerDeployment:
    """MCP-integrated indexer deployment."""
    
    def __init__(self):
        """Initialize MCP indexer deployment."""
        self.config = UnifiedConfig.from_env()
        self.pipeline_manager = IndexerPipelineManager(self.config)
    
    async def deploy_with_mcp_integration(self) -> Dict[str, Any]:
        """Deploy indexer pipeline with MCP tool integration."""
        
        print("🔗 MCP-Integrated Indexer Pipeline Deployment")
        print("=" * 50)
        
        try:
            # Step 1: Validate configuration files exist
            config_files = {
                "datasource": "azure_indexer_datasource.json",
                "skillset": "azure_indexer_skillset.json",
                "indexer": "azure_indexer_main.json"
            }
            
            for component, filepath in config_files.items():
                if not os.path.exists(filepath):
                    return {
                        "status": "failed",
                        "error": f"Configuration file missing: {filepath}",
                        "step": "validation"
                    }
            
            print("✅ Configuration files validated")
            
            # Step 2: Deploy pipeline using automation manager
            print("\n🚀 Deploying pipeline...")
            deployment_result = await self.pipeline_manager.deploy_pipeline(
                datasource_config_path=config_files["datasource"],
                skillset_config_path=config_files["skillset"],
                indexer_config_path=config_files["indexer"],
                validate_only=False,
                auto_run=True
            )
            
            # Step 3: Enhanced monitoring and reporting
            if deployment_result["status"] == "success":
                print("✅ Pipeline deployed successfully")
                
                # Get indexer name for monitoring
                with open(config_files["indexer"], 'r') as f:
                    indexer_config = json.load(f)
                    indexer_name = indexer_config["name"]
                
                # Monitor initial execution
                print(f"\n⏱️  Monitoring indexer: {indexer_name}")
                monitor_result = await self.pipeline_manager.monitor_indexer_execution(
                    indexer_name=indexer_name,
                    timeout_minutes=15,
                    check_interval_seconds=10
                )
                
                deployment_result["monitoring"] = monitor_result
                
                # Get health status
                health_status = await self.pipeline_manager.get_pipeline_health(indexer_name)
                deployment_result["health"] = health_status
                
                print(f"📊 Final Status: {monitor_result.get('final_status', 'unknown')}")
                print(f"⏱️  Duration: {monitor_result.get('monitoring_duration_seconds', 0):.1f}s")
                
            else:
                print(f"❌ Pipeline deployment failed: {deployment_result['status']}")
                
            return deployment_result
            
        except Exception as e:
            error_result = {
                "status": "error",
                "error": str(e),
                "step": "deployment"
            }
            print(f"💥 Deployment error: {e}")
            return error_result
    
    async def get_deployment_status(self, indexer_name: str) -> Dict[str, Any]:
        """Get comprehensive deployment status."""
        
        try:
            # Get pipeline health
            health = await self.pipeline_manager.get_pipeline_health(indexer_name)
            
            # Get current indexer status
            from enhanced_rag.azure_integration.rest.operations import SearchOperations
            operations = self.pipeline_manager.operations
            
            indexer_status = await operations.get_indexer_status(indexer_name)
            
            return {
                "status": "success",
                "indexer_name": indexer_name,
                "health": health,
                "indexer_status": indexer_status,
                "timestamp": health.get("timestamp")
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "indexer_name": indexer_name
            }

async def main():
    """Main deployment function."""
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python deploy_via_mcp.py deploy           - Deploy pipeline")
        print("  python deploy_via_mcp.py status <name>    - Get status")
        return
    
    command = sys.argv[1].lower()
    deployment = MCPIndexerDeployment()
    
    if command == "deploy":
        result = await deployment.deploy_with_mcp_integration()
        
        # Pretty print result
        print(f"\n📋 Deployment Summary:")
        print(f"Status: {result['status']}")
        
        if "components" in result:
            print("Components:")
            for comp, details in result["components"].items():
                print(f"  • {comp}: {details['status']}")
        
        if "monitoring" in result:
            monitor = result["monitoring"]
            print(f"Monitoring: {monitor.get('final_status', 'unknown')}")
            
        if result["status"] == "success":
            print("\n🎉 Indexer pipeline deployed and running successfully\!")
        else:
            print(f"\n❌ Deployment failed: {result.get('error', 'Unknown error')}")
    
    elif command == "status":
        if len(sys.argv) < 3:
            print("❌ Please provide indexer name")
            return
        
        indexer_name = sys.argv[2]
        result = await deployment.get_deployment_status(indexer_name)
        
        print(f"📊 Status for {indexer_name}:")
        print(f"Overall: {result.get('status', 'unknown')}")
        
        if "health" in result:
            health = result["health"]
            print(f"Health: {health.get('overall_health', 'unknown')}")
            
        if "indexer_status" in result:
            idx_status = result["indexer_status"]
            print(f"Indexer Status: {idx_status.get('status', 'unknown')}")

if __name__ == "__main__":
    asyncio.run(main())
EOF < /dev/null
