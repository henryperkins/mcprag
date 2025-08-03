#!/usr/bin/env python3
"""
Update Azure Search index vectorizer configuration with current API key
"""

import os
import json
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    VectorSearchAlgorithmConfiguration,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    AzureOpenAIParameters,
    AzureOpenAIVectorizer,
    VectorSearch
)
from azure.core.credentials import AzureKeyCredential

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

def update_index_vectorizer():
    """Update the index vectorizer with the current API key"""
    
    # Get credentials
    endpoint = os.getenv("ACS_ENDPOINT")
    admin_key = os.getenv("ACS_ADMIN_KEY")
    openai_key = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("AZURE_OPENAI_KEY")
    
    if not all([endpoint, admin_key, openai_key]):
        print("Missing required environment variables")
        return False
    
    # Create index client
    index_client = SearchIndexClient(
        endpoint=endpoint,
        credential=AzureKeyCredential(admin_key)
    )
    
    index_name = "codebase-mcp-sota"
    
    try:
        # Get current index
        print(f"Fetching index '{index_name}'...")
        current_index = index_client.get_index(index_name)
        
        # Update the vectorizer configuration
        if current_index.vector_search and current_index.vector_search.vectorizers:
            for vectorizer in current_index.vector_search.vectorizers:
                if vectorizer.name == "text-embedding-3-large-vectorizer":
                    print(f"Updating vectorizer '{vectorizer.name}' with new API key...")
                    vectorizer.azure_open_ai_parameters.api_key = openai_key
                    
        # Update the index
        print("Updating index...")
        updated_index = index_client.create_or_update_index(current_index)
        
        print("Index updated successfully!")
        
        # Verify the update
        print("\nVerifying vectorizer configuration...")
        verified_index = index_client.get_index(index_name)
        for vectorizer in verified_index.vector_search.vectorizers:
            if vectorizer.name == "text-embedding-3-large-vectorizer":
                print(f"Vectorizer: {vectorizer.name}")
                print(f"Resource URI: {vectorizer.azure_open_ai_parameters.resource_uri}")
                print(f"Deployment ID: {vectorizer.azure_open_ai_parameters.deployment_id}")
                print(f"API Key: {'<set>' if vectorizer.azure_open_ai_parameters.api_key else '<not set>'}")
                
        return True
        
    except Exception as e:
        print(f"Error updating index: {e}")
        return False

if __name__ == "__main__":
    update_index_vectorizer()