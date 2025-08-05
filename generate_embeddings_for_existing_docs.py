#!/usr/bin/env python3
"""
Generate embeddings for documents that were indexed without vectors.
This fixes the issue where documents have empty content_vector fields.
"""

import os
import asyncio
import logging
from typing import List, Dict, Any, Optional
from enhanced_rag.azure_integration import AzureSearchClient, AzureOpenAIEmbeddingProvider
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generate embeddings for existing documents in the index."""
    
    def __init__(self):
        self.endpoint = os.getenv("ACS_ENDPOINT")
        self.admin_key = os.getenv("ACS_ADMIN_KEY")
        
        if not all([self.endpoint, self.admin_key]):
            raise ValueError("Missing ACS_ENDPOINT or ACS_ADMIN_KEY")
        
        self.client = AzureSearchClient(self.endpoint, self.admin_key)
        self.ops = self.client.operations
        self.embedding_provider = AzureOpenAIEmbeddingProvider()
        
        if not self.embedding_provider.is_enabled():
            raise ValueError("Azure OpenAI embedding provider is not configured properly")
    
    async def get_documents_without_embeddings(self, index_name: str, max_docs: int = 100) -> List[Dict[str, Any]]:
        """Get documents that don't have embeddings."""
        # Search for all documents
        query = {
            "search": "*",
            "select": "id,content,file_path,repository,language,function_name",
            "filter": None,  # Could add filter for missing vectors if supported
            "top": max_docs,
            "queryType": "simple"
        }
        
        result = await self.ops.search_documents(index_name, query)
        documents = result.get("value", [])
        
        # Filter documents without embeddings (would need to check content_vector field)
        # For now, return all documents
        logger.info(f"Found {len(documents)} documents to process")
        return documents
    
    async def generate_and_update_embeddings(self, index_name: str, batch_size: int = 10):
        """Generate embeddings for documents and update the index."""
        documents = await self.get_documents_without_embeddings(index_name)
        
        if not documents:
            logger.info("No documents found to process")
            return
        
        processed = 0
        failed = 0
        
        # Process in batches
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1} ({len(batch)} documents)")
            
            # Extract content for embedding
            texts = []
            for doc in batch:
                # Combine relevant fields for better semantic representation
                content_parts = []
                
                if doc.get("function_name"):
                    content_parts.append(f"Function: {doc['function_name']}")
                
                if doc.get("file_path"):
                    content_parts.append(f"File: {doc['file_path']}")
                
                if doc.get("content"):
                    content_parts.append(doc["content"])
                
                text = "\n".join(content_parts)
                texts.append(text)
            
            # Generate embeddings
            try:
                embeddings = self.embedding_provider.generate_embeddings_batch(texts)
                
                # Prepare update batch
                update_batch = []
                for doc, embedding in zip(batch, embeddings):
                    if embedding:
                        update_doc = {
                            "@search.action": "mergeOrUpload",
                            "id": doc["id"],
                            "content_vector": embedding
                        }
                        update_batch.append(update_doc)
                    else:
                        logger.warning(f"Failed to generate embedding for document {doc['id']}")
                        failed += 1
                
                # Update documents in index
                if update_batch:
                    await self.ops.upload_documents(index_name, {"value": update_batch})
                    processed += len(update_batch)
                    logger.info(f"Updated {len(update_batch)} documents with embeddings")
                
            except Exception as e:
                logger.error(f"Error processing batch: {e}")
                failed += len(batch)
            
            # Rate limiting
            await asyncio.sleep(1)
        
        logger.info(f"\nEmbedding generation complete:")
        logger.info(f"  - Processed: {processed}")
        logger.info(f"  - Failed: {failed}")
        logger.info(f"  - Total: {len(documents)}")
    
    async def verify_embeddings(self, index_name: str):
        """Verify that embeddings were added successfully."""
        # Try a vector search
        test_query = "search for authentication functions"
        embedding = self.embedding_provider.generate_embedding(test_query)
        
        if not embedding:
            logger.error("Failed to generate test embedding")
            return
        
        vector_query = {
            "search": "*",
            "vectors": [
                {
                    "value": embedding,
                    "fields": "content_vector",
                    "k": 5
                }
            ],
            "select": "id,file_path,function_name",
            "queryType": "simple"
        }
        
        try:
            result = await self.ops.search_documents(index_name, vector_query)
            count = result.get("@odata.count", 0)
            
            if count > 0:
                logger.info(f"\n✓ Vector search is working! Found {count} results")
                logger.info("\nTop results:")
                for i, doc in enumerate(result.get("value", [])[:3]):
                    logger.info(f"  {i+1}. {doc.get('file_path', 'Unknown')} - {doc.get('function_name', 'N/A')}")
            else:
                logger.warning("\n✗ No vector search results found")
                
        except Exception as e:
            logger.error(f"Vector search failed: {e}")


async def main():
    """Main function to generate embeddings for existing documents."""
    generator = EmbeddingGenerator()
    
    # Get index name from environment or use default
    index_name = os.getenv("ACS_INDEX_NAME", "codebase-mcp-sota")
    
    print("\n" + "="*60)
    print("GENERATING EMBEDDINGS FOR EXISTING DOCUMENTS")
    print("="*60)
    print(f"\nIndex: {index_name}")
    print(f"Embedding Model: {os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', 'text-embedding-3-large')}")
    print(f"Dimensions: 3072")
    
    # Check if we have the necessary configuration
    if not generator.embedding_provider.is_enabled():
        print("\nERROR: Azure OpenAI is not configured properly")
        print("Required environment variables:")
        print("  - AZURE_OPENAI_ENDPOINT")
        print("  - AZURE_OPENAI_KEY")
        print("  - AZURE_OPENAI_DEPLOYMENT_NAME (optional, defaults to text-embedding-3-large)")
        return
    
    print("\nStarting embedding generation...")
    
    # Generate embeddings
    await generator.generate_and_update_embeddings(index_name, batch_size=10)
    
    # Verify
    print("\nVerifying vector search...")
    await generator.verify_embeddings(index_name)
    
    print("\n" + "="*60)
    print("COMPLETE")
    print("="*60)
    print("\nYour MCP search tools should now work with vector search!")
    print("Try searching with:")
    print('  mcp__azure-code-search-enhanced__search_code --query "authentication middleware"')


if __name__ == "__main__":
    asyncio.run(main())