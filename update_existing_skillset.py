#!/usr/bin/env python3
"""
Update the existing codebase-skillset with a proper Azure OpenAI embedding skill.
This adds embedding generation to your existing code analysis pipeline.
"""

import os
import asyncio
import logging
from dotenv import load_dotenv
from enhanced_rag.azure_integration.rest import AzureSearchClient

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def update_skillset_with_embeddings():
    """Update the existing skillset to add proper embedding generation."""
    
    # Azure Search configuration
    endpoint = os.getenv("ACS_ENDPOINT")
    admin_key = os.getenv("ACS_ADMIN_KEY")
    
    # Azure OpenAI configuration
    openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    openai_key = os.getenv("AZURE_OPENAI_KEY")
    openai_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "text-embedding-3-large")
    
    if not all([endpoint, admin_key]):
        raise ValueError("Missing ACS_ENDPOINT or ACS_ADMIN_KEY")
    
    if not all([openai_endpoint, openai_key]):
        raise ValueError("Missing AZURE_OPENAI_ENDPOINT or AZURE_OPENAI_KEY")
    
    client = AzureSearchClient(endpoint, admin_key)
    ops = client.operations
    
    # Define the updated skillset
    skillset_name = "codebase-skillset"
    
    updated_skillset = {
        "name": skillset_name,
        "description": "Code enrichment skillset with AST analysis, git metadata extraction, and embeddings",
        "skills": [
            # 1. Code Splitter (existing)
            {
                "@odata.type": "#Microsoft.Skills.Text.SplitSkill",
                "name": "CodeSplitter",
                "description": "Split code files into semantic chunks",
                "context": "/document",
                "defaultLanguageCode": "en",
                "textSplitMode": "pages",
                "maximumPageLength": 2000,
                "pageOverlapLength": 200,
                "maximumPagesToTake": 0,
                "unit": "characters",
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
            # 2. Language Detector (existing)
            {
                "@odata.type": "#Microsoft.Skills.Text.LanguageDetectionSkill",
                "name": "LanguageDetector",
                "description": "Detect programming language from file content",
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
            },
            # 3. Key Phrase Extractor (existing)
            {
                "@odata.type": "#Microsoft.Skills.Text.KeyPhraseExtractionSkill",
                "name": "KeyPhraseExtractor",
                "description": "Extract key phrases from code comments and docstrings",
                "context": "/document/pages/*",
                "defaultLanguageCode": "en",
                "inputs": [
                    {
                        "name": "text",
                        "source": "/document/pages/*"
                    },
                    {
                        "name": "languageCode",
                        "source": "/document/language"
                    }
                ],
                "outputs": [
                    {
                        "name": "keyPhrases",
                        "targetName": "keyPhrases"
                    }
                ]
            },
            # 4. Code Analyzer (existing custom skill)
            {
                "@odata.type": "#Microsoft.Skills.Custom.WebApiSkill",
                "name": "CodeAnalyzer",
                "description": "Custom skill for AST parsing and code structure analysis",
                "context": "/document",
                "uri": "https://your-function-app.azurewebsites.net/api/analyze-code",
                "httpMethod": "POST",
                "timeout": "PT30S",
                "batchSize": 1000,
                "inputs": [
                    {
                        "name": "code",
                        "source": "/document/content"
                    },
                    {
                        "name": "filePath",
                        "source": "/document/metadata_storage_path"
                    },
                    {
                        "name": "language",
                        "source": "/document/language"
                    }
                ],
                "outputs": [
                    {
                        "name": "functions",
                        "targetName": "codeAnalysis/functions"
                    },
                    {
                        "name": "classes",
                        "targetName": "codeAnalysis/classes"
                    },
                    {
                        "name": "imports",
                        "targetName": "codeAnalysis/imports"
                    },
                    {
                        "name": "dependencies",
                        "targetName": "codeAnalysis/dependencies"
                    },
                    {
                        "name": "docstring",
                        "targetName": "codeAnalysis/docstring"
                    },
                    {
                        "name": "signature",
                        "targetName": "codeAnalysis/signature"
                    },
                    {
                        "name": "comments",
                        "targetName": "codeAnalysis/comments"
                    },
                    {
                        "name": "framework",
                        "targetName": "codeAnalysis/framework"
                    },
                    {
                        "name": "complexity",
                        "targetName": "codeAnalysis/complexity"
                    },
                    {
                        "name": "patterns",
                        "targetName": "codeAnalysis/patterns"
                    }
                ]
            },
            # 5. Git Metadata Extractor (existing custom skill)
            {
                "@odata.type": "#Microsoft.Skills.Custom.WebApiSkill",
                "name": "GitMetadataExtractor",
                "description": "Extract git history and metadata for code files",
                "context": "/document",
                "uri": "https://your-function-app.azurewebsites.net/api/git-metadata",
                "httpMethod": "POST",
                "timeout": "PT30S",
                "batchSize": 1000,
                "inputs": [
                    {
                        "name": "filePath",
                        "source": "/document/metadata_storage_path"
                    }
                ],
                "outputs": [
                    {
                        "name": "branch",
                        "targetName": "gitMetadata/branch"
                    },
                    {
                        "name": "commit",
                        "targetName": "gitMetadata/commit"
                    },
                    {
                        "name": "authors",
                        "targetName": "gitMetadata/authors"
                    },
                    {
                        "name": "commitCount",
                        "targetName": "gitMetadata/commitCount"
                    },
                    {
                        "name": "lastModified",
                        "targetName": "gitMetadata/lastModified"
                    }
                ]
            },
            # 6. Azure OpenAI Embedding Skill (NEW - properly configured)
            {
                "@odata.type": "#Microsoft.Skills.Text.AzureOpenAIEmbeddingSkill",
                "name": "AzureOpenAIEmbedding",
                "description": "Generate embeddings for code content using text-embedding-3-large",
                "context": "/document",
                "resourceUri": openai_endpoint,
                "apiKey": openai_key,
                "deploymentId": openai_deployment,
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
                        "name": "embedding",
                        "targetName": "contentVector"
                    }
                ]
            },
            # 7. Embedding Skill for Chunks (NEW - for chunked content)
            {
                "@odata.type": "#Microsoft.Skills.Text.AzureOpenAIEmbeddingSkill",
                "name": "ChunkEmbedding",
                "description": "Generate embeddings for code chunks",
                "context": "/document/pages/*",
                "resourceUri": openai_endpoint,
                "apiKey": openai_key,
                "deploymentId": openai_deployment,
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
                        "targetName": "chunkVector"
                    }
                ]
            }
        ],
        "cognitiveServices": {
            "@odata.type": "#Microsoft.Azure.Search.DefaultCognitiveServices"
        }
    }
    
    # Keep existing cognitive services if provided
    existing_cog_services = os.getenv("COGNITIVE_SERVICES_KEY")
    if existing_cog_services:
        updated_skillset["cognitiveServices"] = {
            "@odata.type": "#Microsoft.Azure.Search.AIServicesByKey",
            "key": existing_cog_services,
            "subdomainUrl": "https://airesourceforsearch.cognitiveservices.azure.com/"
        }
    
    try:
        # Update the skillset
        logger.info(f"Updating skillset: {skillset_name}")
        result = await ops.create_or_update_skillset(updated_skillset)
        logger.info("Skillset updated successfully")
        
        # Verify the skills
        logger.info("\nSkills in updated skillset:")
        for i, skill in enumerate(updated_skillset["skills"]):
            logger.info(f"  {i+1}. {skill.get('name', 'Unnamed')} ({skill['@odata.type']})")
        
        return result
        
    except Exception as e:
        logger.error(f"Error updating skillset: {e}")
        raise


async def verify_indexer_mapping(indexer_name: str = "codebase-indexer"):
    """Verify that the indexer has proper output field mappings for embeddings."""
    
    endpoint = os.getenv("ACS_ENDPOINT")
    admin_key = os.getenv("ACS_ADMIN_KEY")
    
    client = AzureSearchClient(endpoint, admin_key)
    ops = client.operations
    
    try:
        # Get existing indexer
        indexer = await ops.get_indexer(indexer_name)
        
        # Check output field mappings
        output_mappings = indexer.get("outputFieldMappings", [])
        
        # Required mappings for embeddings
        required_mappings = [
            {
                "sourceFieldName": "/document/contentVector",
                "targetFieldName": "content_vector"
            },
            {
                "sourceFieldName": "/document/pages/*/chunkVector",
                "targetFieldName": "chunk_vectors"
            }
        ]
        
        # Check which mappings exist
        existing_sources = {m.get("sourceFieldName") for m in output_mappings}
        
        logger.info(f"\nIndexer: {indexer_name}")
        logger.info("Existing output field mappings:")
        for mapping in output_mappings:
            logger.info(f"  {mapping.get('sourceFieldName')} -> {mapping.get('targetFieldName')}")
        
        # Add missing mappings
        missing_mappings = []
        for required in required_mappings:
            if required["sourceFieldName"] not in existing_sources:
                missing_mappings.append(required)
                logger.warning(f"  Missing: {required['sourceFieldName']} -> {required['targetFieldName']}")
        
        if missing_mappings:
            logger.info("\nAdding missing output field mappings...")
            output_mappings.extend(missing_mappings)
            indexer["outputFieldMappings"] = output_mappings
            
            # Update indexer
            await ops.create_or_update_indexer(indexer)
            logger.info("Indexer updated with embedding field mappings")
        else:
            logger.info("\nAll required embedding mappings are present")
            
    except Exception as e:
        logger.error(f"Error checking indexer: {e}")


async def main():
    """Update existing skillset with embedding generation."""
    
    print("\n" + "="*60)
    print("UPDATE EXISTING SKILLSET WITH EMBEDDINGS")
    print("="*60)
    
    # Check configuration
    openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    openai_key = os.getenv("AZURE_OPENAI_KEY")
    openai_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "text-embedding-3-large")
    
    print(f"\nAzure OpenAI Configuration:")
    print(f"  Endpoint: {openai_endpoint}")
    print(f"  Deployment: {openai_deployment}")
    print(f"  Model: text-embedding-3-large (3072 dimensions)")
    
    if not openai_endpoint or not openai_key:
        print("\nERROR: Azure OpenAI not configured!")
        print("Please set these environment variables:")
        print("  export AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com")
        print("  export AZURE_OPENAI_KEY=your-api-key")
        return
    
    try:
        # Update skillset
        print("\nUpdating skillset...")
        await update_skillset_with_embeddings()
        
        # Check indexer mappings
        print("\nChecking indexer configuration...")
        await verify_indexer_mapping()
        
        print("\n" + "="*60)
        print("SUCCESS!")
        print("="*60)
        print("\nYour skillset now includes:")
        print("  ✓ Code splitting (2000 char chunks)")
        print("  ✓ Language detection")
        print("  ✓ Key phrase extraction")
        print("  ✓ Code analysis (custom)")
        print("  ✓ Git metadata extraction (custom)")
        print("  ✓ Azure OpenAI embeddings (NEW)")
        print("  ✓ Chunk embeddings (NEW)")
        
        print("\nNext steps:")
        print("1. Reset and run your indexer to generate embeddings:")
        print("   python -m enhanced_rag.azure_integration.cli reset-indexer --name codebase-indexer")
        print("   python -m enhanced_rag.azure_integration.cli run-indexer --name codebase-indexer")
        print("\n2. Monitor progress:")
        print("   python -m enhanced_rag.azure_integration.cli indexer-status --name codebase-indexer")
        
    except Exception as e:
        print(f"\nERROR: {e}")
        logger.exception("Update failed")


if __name__ == "__main__":
    asyncio.run(main())