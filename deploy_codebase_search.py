#!/usr/bin/env python3
"""
Deploy complete codebase search infrastructure to Azure Cognitive Search
This script creates all components in the correct order:
1. Data Source
2. Skillset
3. Index (with vector field)
4. Indexer
"""

import asyncio
from pathlib import Path

from enhanced_rag.azure_integration.index_operations import IndexOperations
from enhanced_rag.core.config import get_config
from azure_search_client import AzureSearchClient


async def deploy_codebase_search():
    """Deploy all components for codebase search"""

    # Get configuration
    config = get_config()
    endpoint = config.azure.endpoint
    admin_key = config.azure.admin_key

    print(f"🚀 Deploying to Azure Cognitive Search: {endpoint}")

    # Initialize operations client
    index_ops = IndexOperations(endpoint, admin_key)

    try:
        # Step 1: Create the index with vector field
        print("\n📊 Step 1: Creating index schema...")
        success = await index_ops.create_codebase_index("codebase-mcp-sota")
        if success:
            print("✅ Index 'codebase-mcp-sota' created successfully!")
        else:
            print("❌ Failed to create index")
            return False

        # Step 2: Create data source
        print("\n📁 Step 2: Creating data source...")
        search_client = AzureSearchClient()
        if not search_client.create_data_source():
            print("❌ Data source creation failed")
            return False

        # Step 3: Create skillset
        print("\n🧠 Step 3: Creating skillset...")
        if not search_client.create_skillset():
            print("❌ Skillset creation failed")
            return False

        # Step 4: Create indexer
        print("\n⚙️  Step 4: Creating indexer...")
        if not search_client.create_indexer():
            print("❌ Indexer creation failed")
            return False

        print("\n🎉 Deployment preparation complete!")
        print("\n📋 Next steps:")
        print("1. ✅ Index schema created")
        print("2. 🔄 Create data source using datasource-config.json")
        print("3. 🔄 Create skillset using skillset-config.json")
        print("4. 🔄 Create indexer using indexer-config.json")

        return True

    except Exception as e:
        print(f"❌ Deployment failed: {e}")
        return False
    finally:
        await index_ops.close()


async def verify_index_schema():
    """Verify the index has the correct schema including vector field"""
    index_ops = IndexOperations()

    try:
        # Get index statistics to verify it exists
        stats = await index_ops.get_index_statistics("codebase-mcp-sota")
        if "error" not in stats:
            print("✅ Index exists and is accessible")
            print(f"   Document count: {stats.get('document_count', 'N/A')}")
            print(f"   Storage size: {stats.get('storage_size', 'N/A')}")
        else:
            print(f"❌ Index verification failed: {stats['error']}")

    except Exception as e:
        print(f"❌ Index verification error: {e}")
    finally:
        await index_ops.close()


if __name__ == "__main__":
    print("🔍 Azure Cognitive Search Codebase Deployment")
    print("=" * 50)

    # Check if config files exist
    required_files = ["datasource-config.json", "skillset-config.json", "indexer-config.json"]
    missing_files = [f for f in required_files if not Path(f).exists()]

    if missing_files:
        print(f"❌ Missing required files: {missing_files}")
        exit(1)

    # Run deployment
    asyncio.run(deploy_codebase_search())

    # Verify index
    print("\n🔍 Verifying index schema...")
    asyncio.run(verify_index_schema())
