#!/usr/bin/env python3
"""
Setup integrated vectorization for Azure AI Search following the latest 2025-05-01-preview API.
Creates data source, skillset, index, and indexer with automatic embedding generation.
Based on: https://learn.microsoft.com/en-us/azure/search/search-how-to-integrated-vectorization
"""

import os
import json
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

from enhanced_rag.azure_integration.rest import AzureSearchClient

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IntegratedVectorizationSetup:
    """Setup integrated vectorization pipeline for Azure AI Search."""
    
    def __init__(self):
        """Initialize with Azure credentials from environment."""
        self.endpoint = os.getenv("ACS_ENDPOINT")
        self.admin_key = os.getenv("ACS_ADMIN_KEY")
        self.openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.openai_key = os.getenv("AZURE_OPENAI_KEY")
        self.openai_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "text-embedding-3-large")
        
        if not all([self.endpoint, self.admin_key]):
            raise ValueError("Missing ACS_ENDPOINT or ACS_ADMIN_KEY environment variables")
        
        if not all([self.openai_endpoint, self.openai_key]):
            logger.warning("Azure OpenAI credentials not found - vectorization will not work")
        
        self.client = AzureSearchClient(self.endpoint, self.admin_key)
        self.ops = self.client.operations
    
    async def create_data_source(self, name: str, connection_string: str, container_name: str) -> Dict[str, Any]:
        """Create blob storage data source for integrated vectorization.
        
        Based on: https://learn.microsoft.com/en-us/azure/search/search-how-to-integrated-vectorization
        """
        datasource = {
            "name": name,
            "type": "azureblob",
            "subtype": None,
            "credentials": {
                "connectionString": connection_string
            },
            "container": {
                "name": container_name,
                "query": None
            },
            "dataChangeDetectionPolicy": None,
            "dataDeletionDetectionPolicy": None
        }
        
        try:
            await self.ops.delete_datasource(name)
            logger.info(f"Deleted existing data source: {name}")
        except:
            pass
        
        result = await self.ops.create_datasource(datasource)
        logger.info(f"Created data source: {name}")
        return result
    
    async def create_skillset(self, name: str) -> Dict[str, Any]:
        """Create skillset with text splitting and Azure OpenAI embedding skills.
        
        Following the pattern from:
        https://learn.microsoft.com/en-us/azure/search/search-how-to-integrated-vectorization
        """
        skillset = {
            "name": name,
            "skills": [
                # Text split skill for chunking
                {
                    "@odata.type": "#Microsoft.Skills.Text.SplitSkill",
                    "name": "my-text-split-skill",
                    "textSplitMode": "pages",
                    "maximumPageLength": 2000,
                    "pageOverlapLength": 500,
                    "maximumPagesToTake": 0,
                    "unit": "characters",
                    "defaultLanguageCode": "en",
                    "inputs": [
                        {
                            "name": "text",
                            "source": "/document/text"
                        }
                    ],
                    "outputs": [
                        {
                            "name": "textItems"
                        }
                    ]
                },
                # Azure OpenAI embedding skill for content
                {
                    "@odata.type": "#Microsoft.Skills.Text.AzureOpenAIEmbeddingSkill",
                    "resourceUri": self.openai_endpoint,
                    "deploymentId": self.openai_deployment,
                    "modelName": "text-embedding-3-large",
                    "dimensions": 3072,
                    "inputs": [
                        {
                            "name": "text",
                            "source": "/document/content"
                        }
                    ],
                    "outputs": [
                        {
                            "name": "embedding"
                        }
                    ]
                }
            ]
        }
        
        # Add API key if not using managed identity
        if self.openai_key:
            for skill in skillset["skills"]:
                if skill["@odata.type"] == "#Microsoft.Skills.Text.AzureOpenAIEmbeddingSkill":
                    skill["apiKey"] = self.openai_key
        
        try:
            await self.ops.delete_skillset(name)
            logger.info(f"Deleted existing skillset: {name}")
        except:
            pass
        
        result = await self.ops.create_skillset(skillset)
        logger.info(f"Created skillset: {name} with {len(skillset['skills'])} skills")
        return result
    
    async def create_index(self, name: str) -> Dict[str, Any]:
        """Create index with vector fields and MCP-required schema.
        
        Following schema from:
        https://learn.microsoft.com/en-us/azure/search/search-how-to-integrated-vectorization
        """
        index = {
            "name": name,
            "fields": [
                # Document key
                {
                    "name": "id",
                    "type": "Edm.String",
                    "key": True,
                    "filterable": True
                },
                # Title field
                {
                    "name": "title",
                    "type": "Edm.String",
                    "searchable": True,
                    "filterable": True,
                    "sortable": True,
                    "retrievable": True
                },
                # Title vector field
                {
                    "name": "titleVector",
                    "type": "Collection(Edm.Single)",
                    "searchable": True,
                    "retrievable": False,
                    "stored": True,
                    "dimensions": 3072,
                    "vectorSearchProfile": "vector-profile-hnsw"
                },
                # Content field (human-readable)
                {
                    "name": "content",
                    "type": "Edm.String",
                    "searchable": True,
                    "retrievable": True
                },
                # Content vector field (embeddings)
                {
                    "name": "contentVector",
                    "type": "Collection(Edm.Single)",
                    "searchable": True,
                    "retrievable": False,
                    "stored": False,
                    "dimensions": 3072,
                    "vectorSearchProfile": "vector-profile-hnsw"
                },
                # MCP required fields
                {
                    "name": "repository",
                    "type": "Edm.String",
                    "searchable": True,
                    "filterable": True,
                    "facetable": True,
                    "retrievable": True
                },
                {
                    "name": "file_path",
                    "type": "Edm.String",
                    "searchable": True,
                    "filterable": True,
                    "retrievable": True
                },
                {
                    "name": "language",
                    "type": "Edm.String",
                    "searchable": False,
                    "filterable": True,
                    "facetable": True,
                    "retrievable": True
                },
                {
                    "name": "function_name",
                    "type": "Edm.String",
                    "searchable": True,
                    "filterable": True,
                    "facetable": True,
                    "retrievable": True
                },
                {
                    "name": "class_name",
                    "type": "Edm.String",
                    "searchable": True,
                    "filterable": True,
                    "facetable": True,
                    "retrievable": True
                }
            ],
            "vectorSearch": {
                "algorithms": [
                    {
                        "name": "hnsw-algorithm",
                        "kind": "hnsw",
                        "hnswParameters": {
                            "m": 4,
                            "efConstruction": 400,
                            "efSearch": 100,
                            "metric": "cosine"
                        }
                    }
                ],
                "profiles": [
                    {
                        "name": "vector-profile-hnsw",
                        "algorithm": "hnsw-algorithm",
                        "vectorizer": "my-openai-vectorizer"
                    }
                ],
                "vectorizers": [
                    {
                        "name": "my-openai-vectorizer",
                        "kind": "azureOpenAI",
                        "azureOpenAIParameters": {
                            "resourceUri": self.openai_endpoint,
                            "deploymentId": self.openai_deployment,
                            "modelName": "text-embedding-3-large"
                        }
                    }
                ]
            }
        }
        
        # Add API key to vectorizer if not using managed identity
        if self.openai_key:
            index["vectorSearch"]["vectorizers"][0]["azureOpenAIParameters"]["apiKey"] = self.openai_key
        
        try:
            await self.ops.delete_index(name)
            logger.info(f"Deleted existing index: {name}")
        except:
            pass
        
        result = await self.ops.create_index(index)
        logger.info(f"Created index: {name} with {len(index['fields'])} fields")
        
        # Verify MCP required fields
        logger.info("Verifying MCP-required fields:")
        required_fields = ["repository", "file_path", "language", "content", "contentVector"]
        for field_name in required_fields:
            field = next((f for f in index['fields'] if f['name'] == field_name), None)
            if field:
                logger.info(f"  ✓ {field_name}: {field['type']}")
            else:
                logger.error(f"  ✗ {field_name}: MISSING!")
        
        return result
    
    async def create_indexer(
        self, 
        name: str, 
        datasource_name: str,
        index_name: str,
        skillset_name: str,
        schedule_hours: int = 2
    ) -> Dict[str, Any]:
        """Create indexer to orchestrate the vectorization pipeline.
        
        Following pattern from:
        https://learn.microsoft.com/en-us/azure/search/search-how-to-integrated-vectorization
        """
        indexer = {
            "name": name,
            "dataSourceName": datasource_name,
            "targetIndexName": index_name,
            "skillsetName": skillset_name,
            "schedule": {
                "interval": f"PT{schedule_hours}H"
            },
            "parameters": {
                "batchSize": None,
                "maxFailedItems": None,
                "maxFailedItemsPerBatch": None
            }
        }
        
        try:
            await self.ops.delete_indexer(name)
            logger.info(f"Deleted existing indexer: {name}")
        except:
            pass
        
        result = await self.ops.create_indexer(indexer)
        logger.info(f"Created indexer: {name}")
        
        # Run indexer immediately
        await self.ops.run_indexer(name)
        logger.info(f"Started initial run of indexer: {name}")
        
        return result
    
    async def setup_complete_pipeline(
        self,
        prefix: str = "my",
        storage_connection_string: Optional[str] = None,
        container_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Setup complete integrated vectorization pipeline following Microsoft docs.
        
        Based on: https://learn.microsoft.com/en-us/azure/search/search-how-to-integrated-vectorization
        """
        if not storage_connection_string:
            logger.error("Storage connection string is required for integrated vectorization")
            raise ValueError("AZURE_STORAGE_CONNECTION_STRING environment variable must be set")
        
        if not container_name:
            container_name = "code-repository"
            logger.info(f"Using default container name: {container_name}")
        
        # Resource names following docs pattern
        datasource_name = f"{prefix}-data-source"
        skillset_name = f"{prefix}-skillset"
        index_name = f"{prefix}-vector-index"
        indexer_name = f"{prefix}-indexer"
        
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "prefix": prefix,
            "resources": {}
        }
        
        try:
            # 1. Create data source
            logger.info("\n=== Creating Data Source ===")
            datasource = await self.create_data_source(
                datasource_name, 
                storage_connection_string, 
                container_name
            )
            results["resources"]["datasource"] = datasource_name
            
            # 2. Create skillset
            logger.info("\n=== Creating Skillset ===")
            skillset = await self.create_skillset(skillset_name)
            results["resources"]["skillset"] = skillset_name
            
            # 3. Create index
            logger.info("\n=== Creating Index ===")
            index = await self.create_index(index_name)
            results["resources"]["index"] = index_name
            
            # 4. Create indexer
            logger.info("\n=== Creating Indexer ===")
            indexer = await self.create_indexer(
                indexer_name,
                datasource_name,
                index_name,
                skillset_name
            )
            results["resources"]["indexer"] = indexer_name
            
            results["status"] = "success"
            results["message"] = "Integrated vectorization pipeline created successfully"
            
            # Save configuration
            config_file = f"{prefix}-integrated-vector-config.json"
            with open(config_file, 'w') as f:
                json.dump(results, f, indent=2)
            logger.info(f"\nSaved configuration to {config_file}")
            
        except Exception as e:
            results["status"] = "error"
            results["message"] = str(e)
            logger.error(f"Pipeline creation failed: {e}")
            raise
        
        return results
    
    async def run_vector_query(self, index_name: str, query_text: str) -> Dict[str, Any]:
        """Run a vector query to test integrated vectorization.
        
        Based on query example from:
        https://learn.microsoft.com/en-us/azure/search/search-how-to-integrated-vectorization
        """
        query = {
            "count": True,
            "select": "title, content",
            "vectorQueries": [
                {
                    "kind": "text",
                    "text": query_text,
                    "fields": "titleVector, contentVector",
                    "k": 3
                }
            ]
        }
        
        # Execute query
        result = await self.ops.search_documents(index_name, query)
        
        return {
            "query": query_text,
            "count": result.get("@odata.count", 0),
            "results": result.get("value", [])
        }


async def main():
    """Main function to setup integrated vectorization."""
    setup = IntegratedVectorizationSetup()
    
    # Get storage configuration from environment
    storage_conn = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    container = os.getenv("AZURE_STORAGE_CONTAINER", "code-repository")
    
    if not storage_conn:
        print("\n" + "="*60)
        print("ERROR: Missing Required Configuration")
        print("="*60)
        print("\nIntegrated vectorization requires:")
        print("1. AZURE_STORAGE_CONNECTION_STRING - Connection to blob storage")
        print("2. AZURE_STORAGE_CONTAINER - Container with documents (optional)")
        print("3. AZURE_OPENAI_ENDPOINT - Azure OpenAI endpoint")
        print("4. AZURE_OPENAI_KEY - Azure OpenAI API key")
        print("5. AZURE_OPENAI_DEPLOYMENT_NAME - Deployment name (e.g., text-embedding-3-large)")
        print("\nExample:")
        print('export AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=..."')
        print('export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com"')
        print('export AZURE_OPENAI_KEY="your-api-key"')
        return
    
    # Setup the pipeline
    print("\n" + "="*60)
    print("SETTING UP INTEGRATED VECTORIZATION")
    print("="*60)
    print(f"\nStorage Account: {storage_conn.split(';')[1].split('=')[1] if ';' in storage_conn else 'Unknown'}")
    print(f"Container: {container}")
    print(f"OpenAI Endpoint: {setup.openai_endpoint}")
    print(f"Embedding Model: {setup.openai_deployment}")
    
    result = await setup.setup_complete_pipeline(
        prefix="mcp",
        storage_connection_string=storage_conn,
        container_name=container
    )
    
    print("\n" + "="*60)
    print("INTEGRATED VECTORIZATION SETUP COMPLETE")
    print("="*60)
    print(f"\nCreated resources:")
    for resource_type, resource_name in result["resources"].items():
        print(f"  - {resource_type}: {resource_name}")
    
    print(f"\nStatus: {result['status']}")
    print(f"Message: {result['message']}")
    
    if result["status"] == "success":
        print("\n" + "="*60)
        print("NEXT STEPS:")
        print("="*60)
        print("\n1. Upload code files to your Azure Storage container:")
        print(f"   Container: {container}")
        print("\n2. The indexer will automatically:")
        print("   - Extract text from documents")
        print("   - Split text into chunks")
        print("   - Generate embeddings using text-embedding-3-large (3072 dimensions)")
        print("   - Store vectors in the search index")
        print("\n3. Query with integrated vectorization:")
        print("   - Text queries are automatically converted to vectors")
        print("   - No need to generate embeddings client-side")
        print("\n4. Monitor indexer status:")
        print(f"   python -m enhanced_rag.azure_integration.cli indexer-status --name {result['resources'].get('indexer', 'indexer-name')}")
        
        # Example query
        print("\n" + "="*60)
        print("EXAMPLE VECTOR QUERY:")
        print("="*60)
        print("""
POST {{baseUrl}}/indexes('""" + result["resources"]["index"] + """')/docs/search.post.search?api-version=2024-07-01
{
    "count": true,
    "select": "title, content",
    "vectorQueries": [
        {
            "kind": "text",
            "text": "authentication middleware functions",
            "fields": "titleVector, contentVector",
            "k": 3
        }
    ]
}
""")


if __name__ == "__main__":
    asyncio.run(main())