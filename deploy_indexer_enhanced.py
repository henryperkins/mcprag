#\!/usr/bin/env python3
"""Enhanced Azure Search Indexer Pipeline Deployment.

This script uses the IndexerPipelineManager for complete pipeline deployment:
- Data source configuration
- Skillset for text processing  
- Main indexer configuration
- Deployment validation and monitoring
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from enhanced_rag.azure_integration.automation.indexer_pipeline_manager import IndexerPipelineManager
from enhanced_rag.azure_integration import UnifiedConfig

async def deploy_indexer_pipeline():
    """Deploy the complete indexer pipeline."""
    
    print("🚀 Azure Search Indexer Pipeline Deployment")
    print("=" * 50)
    
    try:
        # Initialize pipeline manager
        config = UnifiedConfig.from_env()
        pipeline_manager = IndexerPipelineManager(config)
        
        print("📋 Validating configurations...")
        
        # First, validate all configurations
        validation_result = await pipeline_manager.deploy_pipeline(
            validate_only=True,
            auto_run=False
        )
        
        if validation_result["status"] == "validation_failed":
            print("❌ Configuration validation failed:")
            for error in validation_result["validation_errors"]:
                print(f"  • {error}")
            return False
        
        print("✅ Configuration validation successful")
        
        # Deploy the pipeline
        print("\n🔧 Deploying pipeline components...")
        deployment_result = await pipeline_manager.deploy_pipeline(
            auto_run=True
        )
        
        # Display results
        print(f"\n📊 Deployment Status: {deployment_result['status'].upper()}")
        
        for component, details in deployment_result["components"].items():
            status_icon = "✅" if details["status"] == "success" else "❌"
            print(f"  {status_icon} {component.title()}: {details.get('name', 'N/A')} ({details['status']})")
        
        if deployment_result["deployment_errors"]:
            print("\n⚠️  Deployment Errors:")
            for error in deployment_result["deployment_errors"]:
                print(f"  • {error}")
        
        # Show execution status
        exec_status = deployment_result.get("execution_status")
        if exec_status:
            print(f"\n🏃 Indexer Execution:")
            print(f"  • Name: {exec_status['indexer_name']}")
            print(f"  • Status: {exec_status['status']}")
            print(f"  • Started: {'Yes' if exec_status.get('started') else 'No'}")
            
            if exec_status.get('started'):
                print(f"\n⏱️  Monitoring indexer execution...")
                monitor_result = await pipeline_manager.monitor_indexer_execution(
                    exec_status['indexer_name'],
                    timeout_minutes=10,
                    check_interval_seconds=5
                )
                
                print(f"  • Final Status: {monitor_result.get('final_status', 'unknown')}")
                print(f"  • Duration: {monitor_result.get('monitoring_duration_seconds', 0):.1f}s")
                
                if monitor_result.get('execution_result'):
                    exec_result = monitor_result['execution_result']
                    print(f"  • Items Processed: {exec_result.get('itemsProcessed', 0)}")
                    print(f"  • Items Failed: {exec_result.get('itemsFailed', 0)}")
        
        return deployment_result["status"] == "success"
        
    except Exception as e:
        print(f"💥 Deployment failed with error: {e}")
        return False

async def monitor_existing_indexer(indexer_name: str):
    """Monitor an existing indexer."""
    
    print(f"📊 Monitoring Indexer: {indexer_name}")
    print("=" * 40)
    
    try:
        config = UnifiedConfig.from_env()
        pipeline_manager = IndexerPipelineManager(config)
        
        # Get pipeline health
        health = await pipeline_manager.get_pipeline_health(indexer_name)
        
        print(f"Overall Health: {health['overall_health'].upper()}")
        print("\nComponents:")
        for component, details in health["components"].items():
            health_icon = "✅" if details.get("health") == "healthy" else "❌"
            print(f"  {health_icon} {component.title()}: {details.get('health', 'unknown')}")
            
            if "error" in details:
                print(f"    Error: {details['error']}")
        
        if health["recommendations"]:
            print("\n💡 Recommendations:")
            for rec in health["recommendations"]:
                print(f"  • {rec}")
        
        return health["overall_health"] in ["healthy", "degraded"]
        
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

async def validate_prerequisites():
    """Validate that all prerequisites are met."""
    print("🔍 Validating Prerequisites")
    print("-" * 30)
    
    required_env_vars = [
        'ACS_ENDPOINT',
        'ACS_ADMIN_KEY'
    ]
    
    optional_env_vars = [
        'AZURE_STORAGE_CONNECTION_STRING',
        'AZURE_COGNITIVE_SERVICES_KEY'
    ]
    
    missing_vars = []
    for var in required_env_vars:
        if not os.getenv(var):
            missing_vars.append(var)
        else:
            print(f"✅ {var}: Present")
    
    for var in optional_env_vars:
        if os.getenv(var):
            print(f"✅ {var}: Present")
        else:
            print(f"⚠️  {var}: Missing (may be needed for deployment)")
    
    if missing_vars:
        print(f"\n❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"  • {var}")
        return False
    
    # Check if configuration files exist
    required_files = [
        'azure_indexer_datasource.json',
        'azure_indexer_skillset.json', 
        'azure_indexer_main.json'
    ]
    
    missing_files = []
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file}: Found")
        else:
            missing_files.append(file)
            print(f"❌ {file}: Missing")
    
    if missing_files:
        print(f"\n❌ Missing required configuration files:")
        for file in missing_files:
            print(f"  • {file}")
        return False
    
    print("\n✅ All prerequisites validated")
    return True

async def main():
    """Main function with command line options."""
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python deploy_indexer_enhanced.py deploy    - Deploy indexer pipeline")
        print("  python deploy_indexer_enhanced.py monitor <indexer_name> - Monitor existing indexer")
        print("  python deploy_indexer_enhanced.py validate  - Validate prerequisites only")
        return
    
    command = sys.argv[1].lower()
    
    if command == "validate":
        await validate_prerequisites()
    elif command == "deploy":
        if not await validate_prerequisites():
            print("\n❌ Prerequisites validation failed. Please fix and try again.")
            return
        
        success = await deploy_indexer_pipeline()
        if success:
            print("\n🎉 Deployment completed successfully\!")
        else:
            print("\n❌ Deployment failed. Check the errors above.")
    elif command == "monitor":
        if len(sys.argv) < 3:
            print("❌ Please provide indexer name: python deploy_indexer_enhanced.py monitor <indexer_name>")
            return
        
        indexer_name = sys.argv[2]
        success = await monitor_existing_indexer(indexer_name)
        if success:
            print("\n✅ Indexer is healthy")
        else:
            print("\n⚠️  Indexer has issues")
    else:
        print(f"❌ Unknown command: {command}")

if __name__ == "__main__":
    asyncio.run(main())
