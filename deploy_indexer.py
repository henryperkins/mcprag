#!/usr/bin/env python3
"""Deploy Azure Search Indexer Configuration.

This script creates a complete indexing pipeline with:
- Data source configuration
- Skillset for text processing
- Main indexer configuration
- Deployment validation
"""

import json
import asyncio
import os
from typing import Any, Dict, Optional

from enhanced_rag.azure_integration import UnifiedConfig, ClientFactory

async def deploy_indexer_pipeline() -> bool:
    """Deploy the complete indexer pipeline."""
    # Load configuration
    config = UnifiedConfig.from_env()
    operations = ClientFactory.create_operations(config.azure_search)
    
    print("Starting Azure Search Indexer deployment...")
    
    try:
        # 1. Create/update data source
        print("1. Creating data source...")
        with open('azure_indexer_datasource.json', 'r') as f:
            datasource_config = json.load(f)
        
        # Replace placeholder with actual storage connection string
        storage_conn = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
        if storage_conn:
            datasource_config['credentials']['connectionString'] = storage_conn
        
        await operations.create_datasource(datasource_config)
        print(f"✓ Data source '{datasource_config['name']}' created/updated")
        
        # 2. Create/update skillset
        print("2. Creating skillset...")
        with open('azure_indexer_skillset.json', 'r') as f:
            skillset_config = json.load(f)
        
        # Replace cognitive services key
        cog_services_key = os.getenv('AZURE_COGNITIVE_SERVICES_KEY')
        if cog_services_key:
            skillset_config['cognitiveServices']['key'] = cog_services_key
        
        await operations.create_skillset(skillset_config)
        print(f"✓ Skillset '{skillset_config['name']}' created/updated")
        
        # 3. Create/update indexer
        print("3. Creating indexer...")
        with open('azure_indexer_main.json', 'r') as f:
            indexer_config = json.load(f)
        
        await operations.create_indexer(indexer_config)
        print(f"✓ Indexer '{indexer_config['name']}' created/updated")
        
        # 4. Start initial indexing run
        print("4. Starting initial indexer run...")
        await operations.run_indexer(indexer_config['name'])
        print(f"✓ Indexer '{indexer_config['name']}' started")
        
        # 5. Check indexer status
        print("5. Checking indexer status...")
        status = await operations.get_indexer_status(indexer_config['name'])
        print(f"✓ Indexer status: {status.get('status', 'unknown')}")
        
        print("\n🎉 Indexer pipeline deployed successfully!")
        print("\nNext steps:")
        print("- Monitor indexer execution: Check Azure Portal or use status API")
        print("- Upload data: Place files in the configured Azure Storage container")
        print("- Test search: Use the search API to verify indexing results")
        
        return True
        
    except Exception as e:
        print(f"❌ Deployment failed: {e}")
        return False

async def validate_prerequisites() -> bool:
    """Validate that all prerequisites are met."""
    print("Validating prerequisites...")

    # Keep backward compatibility with prior var names
    # Prefer ACS_* but allow Azure SDK style names if present
    required_env_vars = [
        'ACS_ENDPOINT',
        'ACS_ADMIN_KEY',
        'AZURE_STORAGE_CONNECTION_STRING',
        'AZURE_COGNITIVE_SERVICES_KEY'
    ]
    
    missing_vars = []
    for var in required_env_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        return False
    
    # Check if configuration files exist
    required_files = [
        'azure_indexer_datasource.json',
        'azure_indexer_skillset.json', 
        'azure_indexer_main.json',
        'azure_search_index_schema.json'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Missing required configuration files: {', '.join(missing_files)}")
        return False
    
    print("✓ All prerequisites validated")
    return True

async def main():
    """Main deployment function."""
    
    print("Azure Search Indexer Deployment Tool")
    print("=" * 40)
    
    # Validate prerequisites
    if not await validate_prerequisites():
        print("\nPlease fix the issues above and try again.")
        return
    
    # Deploy pipeline
    success = await deploy_indexer_pipeline()
    
    if success:
        print("\n✅ Deployment completed successfully!")
    else:
        print("\n❌ Deployment failed. Check the errors above.")

if __name__ == "__main__":
    asyncio.run(main())
