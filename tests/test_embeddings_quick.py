#!/usr/bin/env python3
"""
Quick test of Azure OpenAI embeddings with just a few files
"""

import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from openai import AzureOpenAI

# Load environment
load_dotenv()

# Configuration
endpoint = os.getenv("ACS_ENDPOINT")
admin_key = os.getenv("ACS_ADMIN_KEY")
azure_openai_key = os.getenv("AZURE_OPENAI_KEY")
azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "text-embedding-3-large")
index_name = "codebase-mcp-sota"

# Initialize clients
azure_openai_client = AzureOpenAI(
    api_key=azure_openai_key,
    api_version="2024-02-01",
    azure_endpoint=azure_openai_endpoint
)

search_client = SearchClient(
    endpoint=endpoint,
    index_name=index_name,
    credential=AzureKeyCredential(admin_key)
)

print(f"✅ Azure OpenAI client initialized")
print(f"   Endpoint: {azure_openai_endpoint}")
print(f"   Deployment: {deployment_name}")

# Test with a few key files
test_files = [
    ("mcprag/mcp/tools.py", "MCP tools implementation with register_tools function"),
    ("mcprag/server.py", "Main MCP server implementation"), 
    ("enhanced_rag/azure_integration/automation/index_manager.py", "Index automation for Azure Search")
]

documents = []

for file_path, description in test_files:
    full_path = f"/home/azureuser/mcprag/{file_path}"
    
    # Read file content
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()[:5000]  # First 5000 chars
    except:
        continue
        
    # Create embedding text with context
    embedding_text = f"File: {file_path}\nDescription: {description}\n\n{content}"
    
    print(f"\n📝 Generating embedding for {file_path}")
    
    # Generate embedding
    response = azure_openai_client.embeddings.create(
        input=embedding_text,
        model=deployment_name
    )
    
    embedding = response.data[0].embedding
    print(f"   ✅ Embedding generated ({len(embedding)} dimensions)")
    
    # Create document with valid ID (no dots allowed)
    doc_id = file_path.replace("/", "_").replace(".", "_")
    doc = {
        "id": doc_id,
        "content": content,
        "content_vector": embedding,
        "repository": "mcprag",
        "file_path": file_path,
        "language": "python",
        "semantic_context": description,
        "chunk_type": "file",
        "last_modified": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")[:-4] + "Z"
    }
    
    documents.append(doc)

# Upload documents
print(f"\n📤 Uploading {len(documents)} documents...")
result = search_client.upload_documents(documents=documents)
print("✅ Upload complete")

# Test vector search
print("\n🧪 Testing vector search...")
test_query = "How to register MCP tools?"

# Generate query embedding
query_response = azure_openai_client.embeddings.create(
    input=test_query,
    model=deployment_name
)
query_vector = query_response.data[0].embedding

# Perform vector search
vector_results = search_client.search(
    search_text=None,
    vector_queries=[{
        "vector": query_vector,
        "fields": "content_vector",
        "kind": "vector",
        "k": 3
    }],
    select=["file_path", "semantic_context"]
)

print(f"\nQuery: '{test_query}'")
print("\nVector search results:")
for i, result in enumerate(vector_results):
    print(f"{i+1}. {result.get('file_path', 'Unknown')}")
    print(f"   Context: {result.get('semantic_context', 'N/A')}")
    print(f"   Score: {result.get('@search.score', 0):.4f}")

# Also test hybrid search
print("\n🧪 Testing hybrid search (text + vector)...")
hybrid_results = search_client.search(
    search_text="register tools",
    vector_queries=[{
        "vector": query_vector,
        "fields": "content_vector", 
        "kind": "vector",
        "k": 3
    }],
    select=["file_path", "semantic_context"]
)

print("\nHybrid search results:")
for i, result in enumerate(hybrid_results):
    print(f"{i+1}. {result.get('file_path', 'Unknown')}")
    print(f"   Score: {result.get('@search.score', 0):.4f}")

print("\n✅ Embeddings are working correctly!")