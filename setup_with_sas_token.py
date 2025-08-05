#!/usr/bin/env python3
"""
Setup integrated vectorization using SAS token for Azure Blob Storage.
This uses your existing storage account with SAS authentication.
"""

import os
import asyncio
import logging
from dotenv import load_dotenv
from setup_integrated_vectorization_v2 import IntegratedVectorizationSetup

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Setup integrated vectorization with SAS token."""
    
    # Your storage details
    storage_account = "codebasestorage2025"
    container_name = "code-repositories"
    sas_token = "st=2025-08-04T15:15:24Z&se=2025-08-09T23:30:24Z&si=aisearch&sv=2024-11-04&sr=c&sig=lthGhNUB9BVCI4MVrcit2KIn36%2FzIOIbwmlzGaCCI8k%3D"
    
    # Construct connection string with SAS token
    # Format: BlobEndpoint=https://{account}.blob.core.windows.net/;SharedAccessSignature={sas}
    connection_string = f"BlobEndpoint=https://{storage_account}.blob.core.windows.net/;SharedAccessSignature={sas_token}"
    
    print("\n" + "="*60)
    print("SETTING UP INTEGRATED VECTORIZATION WITH SAS TOKEN")
    print("="*60)
    print(f"\nStorage Account: {storage_account}")
    print(f"Container: {container_name}")
    print("SAS Token: Valid until 2025-08-09")
    print("\nChecking Azure OpenAI configuration...")
    
    # Check OpenAI configuration
    openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    openai_key = os.getenv("AZURE_OPENAI_KEY")
    openai_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "text-embedding-3-large")
    
    if not openai_endpoint or not openai_key:
        print("\nWARNING: Azure OpenAI not configured!")
        print("Integrated vectorization requires Azure OpenAI for embedding generation.")
        print("\nPlease set these environment variables:")
        print("  export AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com")
        print("  export AZURE_OPENAI_KEY=your-api-key")
        print("  export AZURE_OPENAI_DEPLOYMENT_NAME=text-embedding-3-large")
        
        # Show what we have
        print("\nCurrent configuration:")
        print(f"  AZURE_OPENAI_ENDPOINT: {openai_endpoint or 'NOT SET'}")
        print(f"  AZURE_OPENAI_KEY: {'SET' if openai_key else 'NOT SET'}")
        print(f"  AZURE_OPENAI_DEPLOYMENT_NAME: {openai_deployment}")
        
        response = input("\nDo you want to continue anyway? (y/N): ")
        if response.lower() != 'y':
            return
    else:
        print(f"  ✓ Azure OpenAI Endpoint: {openai_endpoint}")
        print(f"  ✓ Deployment: {openai_deployment}")
    
    # Initialize setup
    setup = IntegratedVectorizationSetup()
    
    try:
        # Create the integrated vectorization pipeline
        result = await setup.setup_complete_pipeline(
            prefix="mcp-codebase",
            storage_connection_string=connection_string,
            container_name=container_name
        )
        
        if result["status"] == "success":
            print("\n" + "="*60)
            print("SUCCESS! INTEGRATED VECTORIZATION IS SET UP")
            print("="*60)
            
            print("\nCreated resources:")
            for resource_type, resource_name in result["resources"].items():
                print(f"  ✓ {resource_type}: {resource_name}")
            
            print("\n" + "="*60)
            print("WHAT HAPPENS NEXT:")
            print("="*60)
            print("\n1. The indexer will automatically scan your blob container")
            print("2. For each document it will:")
            print("   - Extract text content")
            print("   - Split into chunks (2000 chars with 500 char overlap)")
            print("   - Generate embeddings using text-embedding-3-large")
            print("   - Store in the search index with vector fields")
            print("\n3. The indexer runs every 2 hours automatically")
            print("\n4. You can manually trigger it:")
            print(f"   python -m enhanced_rag.azure_integration.cli run-indexer --name {result['resources']['indexer']}")
            
            print("\n" + "="*60)
            print("UPLOADING FILES TO BLOB STORAGE:")
            print("="*60)
            print("\nYou can upload files using:")
            print("1. Azure Storage Explorer")
            print("2. Azure Portal")
            print("3. AzCopy with SAS token:")
            print(f'   azcopy copy "./your-code/*" "https://{storage_account}.blob.core.windows.net/{container_name}?{sas_token}" --recursive')
            
            print("\n" + "="*60)
            print("TESTING VECTOR SEARCH:")
            print("="*60)
            print("\nOnce files are indexed, test with:")
            print(f"""
curl -X POST \\
  "{os.getenv('ACS_ENDPOINT')}/indexes('{result['resources']['index']}')/docs/search?api-version=2024-07-01" \\
  -H "Content-Type: application/json" \\
  -H "api-key: {os.getenv('ACS_ADMIN_KEY', 'YOUR-API-KEY')}" \\
  -d '{
    "count": true,
    "select": "title, content, file_path",
    "vectorQueries": [{
        "kind": "text",
        "text": "authentication middleware",
        "fields": "contentVector",
        "k": 5
    }]
}'
""")
            
        else:
            print(f"\nERROR: {result['message']}")
            
    except Exception as e:
        print(f"\nERROR: {e}")
        logger.exception("Setup failed")


if __name__ == "__main__":
    asyncio.run(main())