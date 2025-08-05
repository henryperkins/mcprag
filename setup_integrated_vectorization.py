#!/usr/bin/env python3
"""
Setup integrated vectorization for Azure AI Search with all required components.
Creates data source, skillset, index, and indexer with automatic embedding generation.
"""

import os
import json
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from enhanced_rag.azure_integration.rest import AzureSearchClient
from enhanced_rag.azure_integration.rest.models import (
    create_blob_datasource,
    create_indexer_schedule,
    create_vector_profile,
    create_hnsw_algorithm
)

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
        
        Args:
            name: Data source name
            connection_string: Azure Storage connection string
            container_name: Container name with source documents
            
        Returns:
            Created data source definition
        """
        datasource = {
            "@odata.type": "#Microsoft.Azure.Search.IndexersBlob",
            "name": name,
            "type": "azureblob",
            "credentials": {
                "connectionString": connection_string
            },
            "container": {
                "name": container_name,
                "query": None
            },
            "dataChangeDetectionPolicy": {
                "@odata.type": "#Microsoft.Azure.Search.HighWaterMarkChangeDetectionPolicy",
                "highWaterMarkColumnName": "_ts"
            },
            "dataDeletionDetectionPolicy": {
                "@odata.type": "#Microsoft.Azure.Search.SoftDeleteColumnDeletionDetectionPolicy",
                "softDeleteColumnName": "IsDeleted",
                "softDeleteMarkerValue": "true"
            }
        }
        
        try:
            # Delete existing if present
            await self.ops.delete_datasource(name)
            logger.info(f"Deleted existing data source: {name}")
        except:
            pass
        
        result = await self.ops.create_datasource(datasource)
        logger.info(f"Created data source: {name}")
        return result
    
    async def create_skillset(self, name: str) -> Dict[str, Any]:
        """Create skillset with text splitting and Azure OpenAI embedding skills.
        
        Args:
            name: Skillset name
            
        Returns:
            Created skillset definition
        """
        skillset = {
            "name": name,
            "description": "Integrated vectorization skillset for code search",
            "skills": [
                # Text split skill for chunking
                {
                    "@odata.type": "#Microsoft.Skills.Text.SplitSkill",
                    "name": "text-split",
                    "description": "Split documents into chunks",
                    "context": "/document",
                    "textSplitMode": "pages",
                    "maximumPageLength": 2000,
                    "pageOverlapLength": 500,
                    "maximumPagesToTake": 0,
                    "defaultLanguageCode": "en",
                    "inputs": [
                        {
                            "name": "text",
                            "source": "/document/content"
                        }
                    ],
                    "outputs": [
                        {
                            "name": "textItems",
                            "targetName": "pages"
                        }
                    ]
                },
                # Azure OpenAI embedding skill
                {
                    "@odata.type": "#Microsoft.Skills.Text.AzureOpenAIEmbeddingSkill",
                    "name": "azure-openai-embeddings",
                    "description": "Generate embeddings using text-embedding-3-large",
                    "context": "/document/pages/*",
                    "resourceUri": self.openai_endpoint,
                    "apiKey": self.openai_key,
                    "deploymentId": self.openai_deployment,
                    "modelName": "text-embedding-3-large",
                    "dimensions": 3072,
                    "inputs": [
                        {
                            "name": "text",
                            "source": "/document/pages/*"
                        }
                    ],
                    "outputs": [
                        {
                            "name": "embedding",
                            "targetName": "content_vector"
                        }
                    ]
                },
                # Language detection skill
                {
                    "@odata.type": "#Microsoft.Skills.Text.LanguageDetectionSkill",
                    "name": "language-detection",
                    "description": "Detect document language",
                    "context": "/document",
                    "inputs": [
                        {
                            "name": "text",
                            "source": "/document/content"
                        }
                    ],
                    "outputs": [
                        {
                            "name": "languageCode",
                            "targetName": "language"
                        }
                    ]
                }
            ],
            "cognitiveServices": {
                "@odata.type": "#Microsoft.Azure.Search.DefaultCognitiveServices"
            }
        }
        
        try:
            # Delete existing if present
            await self.ops.delete_skillset(name)
            logger.info(f"Deleted existing skillset: {name}")
        except:
            pass
        
        result = await self.ops.create_skillset(skillset)
        logger.info(f"Created skillset: {name} with {len(skillset['skills'])} skills")
        return result
    
    async def create_index(self, name: str) -> Dict[str, Any]:
        """Create index with vector fields and MCP-required schema.
        
        Args:
            name: Index name
            
        Returns:
            Created index definition
        """
        # Create HNSW algorithm configuration
        hnsw_algo = create_hnsw_algorithm(
            name="hnsw-config",
            m=12,
            ef_construction=300,
            ef_search=120,
            metric="cosine"
        )
        
        # Create vector profile
        vector_profile = create_vector_profile(
            name="vector-profile-hnsw",
            algorithm="hnsw-config"
        )
        
        index = {
            "name": name,
            "fields": [
                # Document key
                {
                    "name": "id",
                    "type": "Edm.String",
                    "key": True,
                    "searchable": False,
                    "filterable": True,
                    "sortable": False,
                    "facetable": False,
                    "retrievable": True
                },
                # MCP required fields
                {
                    "name": "repository",
                    "type": "Edm.String",
                    "searchable": True,
                    "filterable": True,
                    "sortable": True,
                    "facetable": True,
                    "retrievable": True
                },
                {
                    "name": "file_path",
                    "type": "Edm.String",
                    "searchable": True,
                    "filterable": True,
                    "sortable": True,
                    "facetable": False,
                    "retrievable": True
                },
                {
                    "name": "language",
                    "type": "Edm.String",
                    "searchable": False,
                    "filterable": True,
                    "sortable": False,
                    "facetable": True,
                    "retrievable": True
                },
                {
                    "name": "content",
                    "type": "Edm.String",
                    "searchable": True,
                    "filterable": False,
                    "sortable": False,
                    "facetable": False,
                    "retrievable": True,
                    "analyzer": "en.microsoft"
                },
                # Vector field for embeddings
                {
                    "name": "content_vector",
                    "type": "Collection(Edm.Single)",
                    "searchable": True,
                    "filterable": False,
                    "sortable": False,
                    "facetable": False,
                    "retrievable": False,
                    "dimensions": 3072,
                    "vectorSearchProfile": "vector-profile-hnsw"
                },
                # Additional useful fields
                {
                    "name": "function_name",
                    "type": "Edm.String",
                    "searchable": True,
                    "filterable": True,
                    "sortable": False,
                    "facetable": True,
                    "retrievable": True
                },
                {
                    "name": "class_name",
                    "type": "Edm.String",
                    "searchable": True,
                    "filterable": True,
                    "sortable": False,
                    "facetable": True,
                    "retrievable": True
                },
                {
                    "name": "chunk_id",
                    "type": "Edm.String",
                    "searchable": False,
                    "filterable": True,
                    "sortable": False,
                    "facetable": False,
                    "retrievable": True
                },
                {
                    "name": "chunk_type",
                    "type": "Edm.String",
                    "searchable": False,
                    "filterable": True,
                    "sortable": False,
                    "facetable": True,
                    "retrievable": True
                },
                {
                    "name": "last_modified",
                    "type": "Edm.DateTimeOffset",
                    "searchable": False,
                    "filterable": True,
                    "sortable": True,
                    "facetable": False,
                    "retrievable": True
                },
                {
                    "name": "metadata_storage_path",
                    "type": "Edm.String",
                    "searchable": False,
                    "filterable": False,
                    "sortable": False,
                    "facetable": False,
                    "retrievable": True
                },
                {
                    "name": "metadata_storage_name",
                    "type": "Edm.String",
                    "searchable": True,
                    "filterable": False,
                    "sortable": False,
                    "facetable": False,
                    "retrievable": True
                }
            ],
            "vectorSearch": {
                "algorithms": [hnsw_algo],
                "profiles": [vector_profile]
            },
            "semanticConfiguration": {
                "configurations": [
                    {
                        "name": "semantic-config",
                        "prioritizedFields": {
                            "titleField": {
                                "fieldName": "function_name"
                            },
                            "contentFields": [
                                {
                                    "fieldName": "content"
                                }
                            ],
                            "keywordsFields": [
                                {
                                    "fieldName": "language"
                                }
                            ]
                        }
                    }
                ]
            },
            "corsOptions": {
                "allowedOrigins": ["*"],
                "maxAgeInSeconds": 300
            }
        }
        
        try:
            # Delete existing if present
            await self.ops.delete_index(name)
            logger.info(f"Deleted existing index: {name}")
        except:
            pass
        
        result = await self.ops.create_index(index)
        logger.info(f"Created index: {name} with {len(index['fields'])} fields")
        
        # Verify MCP required fields
        logger.info("Verifying MCP-required fields:")
        required_fields = ["repository", "file_path", "language", "content", "content_vector"]
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
        schedule_hours: int = 1
    ) -> Dict[str, Any]:
        """Create indexer to orchestrate the vectorization pipeline.
        
        Args:
            name: Indexer name
            datasource_name: Data source name
            index_name: Target index name
            skillset_name: Skillset name
            schedule_hours: Schedule interval in hours
            
        Returns:
            Created indexer definition
        """
        indexer = {
            "name": name,
            "description": "Integrated vectorization indexer for code search",
            "dataSourceName": datasource_name,
            "targetIndexName": index_name,
            "skillsetName": skillset_name,
            "schedule": create_indexer_schedule(f"PT{schedule_hours}H"),
            "fieldMappings": [
                {
                    "sourceFieldName": "metadata_storage_path",
                    "targetFieldName": "id",
                    "mappingFunction": {
                        "name": "base64Encode"
                    }
                },
                {
                    "sourceFieldName": "metadata_storage_path",
                    "targetFieldName": "file_path"
                },
                {
                    "sourceFieldName": "metadata_storage_last_modified",
                    "targetFieldName": "last_modified"
                }
            ],
            "outputFieldMappings": [
                {
                    "sourceFieldName": "/document/pages/*/content_vector",
                    "targetFieldName": "content_vector"
                },
                {
                    "sourceFieldName": "/document/language",
                    "targetFieldName": "language"
                }
            ],
            "parameters": {
                "configuration": {
                    "dataToExtract": "contentAndMetadata",
                    "parsingMode": "default",
                    "imageAction": "none"
                },
                "batchSize": 10,
                "maxFailedItems": 0,
                "maxFailedItemsPerBatch": 0
            }
        }
        
        try:
            # Delete existing if present
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
        prefix: str = "mcp-integrated",
        storage_connection_string: Optional[str] = None,
        container_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Setup complete integrated vectorization pipeline.
        
        Args:
            prefix: Prefix for all resource names
            storage_connection_string: Azure Storage connection string
            container_name: Container with source documents
            
        Returns:
            Dictionary with all created resource names
        """
        if not storage_connection_string:
            logger.warning("No storage connection string provided - using demo configuration")
            storage_connection_string = "DefaultEndpointsProtocol=https;AccountName=demo;AccountKey=demo;EndpointSuffix=core.windows.net"
            container_name = container_name or "code-samples"
        
        # Resource names
        datasource_name = f"{prefix}-datasource"
        skillset_name = f"{prefix}-skillset"
        index_name = f"{prefix}-index"
        indexer_name = f"{prefix}-indexer"
        
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "prefix": prefix,
            "resources": {}
        }
        
        # Create all components
        try:
            # 1. Create data source
            datasource = await self.create_data_source(
                datasource_name, 
                storage_connection_string, 
                container_name
            )
            results["resources"]["datasource"] = datasource_name
            
            # 2. Create skillset
            skillset = await self.create_skillset(skillset_name)
            results["resources"]["skillset"] = skillset_name
            
            # 3. Create index
            index = await self.create_index(index_name)
            results["resources"]["index"] = index_name
            
            # 4. Create indexer
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
            config_file = f"{prefix}-config.json"
            with open(config_file, 'w') as f:
                json.dump(results, f, indent=2)
            logger.info(f"Saved configuration to {config_file}")
            
        except Exception as e:
            results["status"] = "error"
            results["message"] = str(e)
            logger.error(f"Pipeline creation failed: {e}")
            raise
        
        return results
    
    async def verify_pipeline_status(self, indexer_name: str) -> Dict[str, Any]:
        """Verify the pipeline is working correctly.
        
        Args:
            indexer_name: Indexer to check
            
        Returns:
            Status information
        """
        status = await self.ops.get_indexer_status(indexer_name)
        
        # Get last execution info
        last_result = status.get("lastResult", {})
        execution_history = status.get("executionHistory", [])
        
        return {
            "indexer_name": indexer_name,
            "status": status.get("status"),
            "last_execution": {
                "status": last_result.get("status"),
                "startTime": last_result.get("startTime"),
                "endTime": last_result.get("endTime"),
                "itemsProcessed": last_result.get("itemsProcessed", 0),
                "itemsFailed": last_result.get("itemsFailed", 0),
                "errors": last_result.get("errors", []),
                "warnings": last_result.get("warnings", [])
            },
            "execution_count": len(execution_history)
        }


async def main():
    """Main function to setup integrated vectorization."""
    setup = IntegratedVectorizationSetup()
    
    # Get storage configuration from environment or use defaults
    storage_conn = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    container = os.getenv("AZURE_STORAGE_CONTAINER", "code-repository")
    
    if not storage_conn:
        print("\nWARNING: No AZURE_STORAGE_CONNECTION_STRING found in environment")
        print("To use integrated vectorization, you need:")
        print("1. An Azure Storage account with a container of code files")
        print("2. Set AZURE_STORAGE_CONNECTION_STRING environment variable")
        print("3. Set AZURE_STORAGE_CONTAINER environment variable (optional)")
        print("\nCreating demo configuration for reference...")
    
    # Setup the pipeline
    result = await setup.setup_complete_pipeline(
        prefix="mcp-integrated-vector",
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
    
    if result["status"] == "success" and storage_conn:
        # Wait a bit for indexer to start
        await asyncio.sleep(5)
        
        # Check status
        indexer_name = result["resources"]["indexer"]
        status = await setup.verify_pipeline_status(indexer_name)
        
        print(f"\nIndexer Status: {status['status']}")
        if status['last_execution'].get('status'):
            print(f"Last execution: {status['last_execution']['status']}")
            print(f"Items processed: {status['last_execution']['itemsProcessed']}")
            print(f"Items failed: {status['last_execution']['itemsFailed']}")
    
    print("\n" + "="*60)
    print("NEXT STEPS:")
    print("="*60)
    print("\n1. Upload code files to your Azure Storage container")
    print("2. The indexer will automatically process them every hour")
    print("3. Embeddings will be generated using text-embedding-3-large")
    print("4. Use MCP tools to search with vector similarity")
    print("\nTo manually trigger indexing:")
    print(f"  python -m enhanced_rag.azure_integration.cli run-indexer --name {result['resources'].get('indexer', 'indexer-name')}")


if __name__ == "__main__":
    asyncio.run(main())