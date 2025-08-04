#!/usr/bin/env python3
"""
Reindex documents with Azure OpenAI embeddings using text-embedding-3-large
"""

import os
import sys
import json
import hashlib
import ast
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any
from dotenv import load_dotenv
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

# Azure OpenAI imports
try:
    from openai import AzureOpenAI
    HAS_AZURE_OPENAI = True
except ImportError:
    HAS_AZURE_OPENAI = False
    print("⚠️  Azure OpenAI package not installed. Install with: pip install openai")

# Load environment
load_dotenv()

# Configuration
endpoint = os.getenv("ACS_ENDPOINT")
admin_key = os.getenv("ACS_ADMIN_KEY")
azure_openai_key = os.getenv("AZURE_OPENAI_KEY")
azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "text-embedding-3-large")
index_name = "codebase-mcp-sota"

# Initialize Azure OpenAI client
azure_openai_client = None
embedding_dimensions = 3072  # Default for text-embedding-3-large

if HAS_AZURE_OPENAI and azure_openai_key and azure_openai_endpoint:
    azure_openai_client = AzureOpenAI(
        api_key=azure_openai_key,
        api_version="2024-02-01",
        azure_endpoint=azure_openai_endpoint
    )
    print(f"✅ Azure OpenAI client initialized")
    print(f"   Endpoint: {azure_openai_endpoint}")
    print(f"   Deployment: {deployment_name}")
    print(f"   Dimensions: {embedding_dimensions}")
else:
    print("❌ Azure OpenAI not available - cannot generate embeddings")
    sys.exit(1)

def get_embedding(text: str) -> List[float]:
    """Generate embedding for text using Azure OpenAI"""
    if not azure_openai_client:
        # Return empty embedding if Azure OpenAI not available
        return [0.0] * embedding_dimensions
    
    try:
        # Truncate text if too long (max ~8000 tokens for text-embedding-3-large)
        if len(text) > 30000:
            text = text[:30000]
        
        response = azure_openai_client.embeddings.create(
            input=text,
            model=deployment_name
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"❌ Error generating embedding: {e}")
        return [0.0] * embedding_dimensions

def get_language_from_extension(file_path):
    """Determine language from file extension"""
    ext_map = {
        '.py': 'python',
        '.js': 'javascript',
        '.mjs': 'javascript',
        '.ts': 'typescript',
        '.jsx': 'javascript',
        '.tsx': 'typescript',
        '.java': 'java',
        '.cpp': 'cpp',
        '.c': 'c',
        '.cs': 'csharp',
        '.go': 'go',
        '.rs': 'rust',
        '.php': 'php',
        '.rb': 'ruby',
        '.swift': 'swift',
        '.kt': 'kotlin',
        '.scala': 'scala',
        '.r': 'r',
        '.md': 'markdown',
        '.json': 'json',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.xml': 'xml',
        '.html': 'html',
        '.css': 'css'
    }
    
    ext = Path(file_path).suffix.lower()
    return ext_map.get(ext, 'text')

def extract_python_chunks(content, file_path):
    """Extract semantic chunks from Python code"""
    chunks = []
    
    try:
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                chunk = {
                    "chunk_type": "function" if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else "class",
                    "function_name": node.name if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else None,
                    "class_name": node.name if isinstance(node, ast.ClassDef) else None,
                    "start_line": node.lineno,
                    "end_line": node.end_lineno or node.lineno,
                    "docstring": ast.get_docstring(node) or "",
                    "signature": f"def {node.name}" if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else f"class {node.name}"
                }
                
                # Extract code content
                lines = content.split('\n')
                chunk_content = '\n'.join(lines[chunk['start_line']-1:chunk['end_line']])
                chunk['content'] = chunk_content
                
                # Extract imports
                imports = []
                for n in ast.walk(node):
                    if isinstance(n, ast.Import):
                        for alias in n.names:
                            imports.append(alias.name)
                    elif isinstance(n, ast.ImportFrom):
                        module = n.module or ''
                        for alias in n.names:
                            imports.append(f"{module}.{alias.name}")
                chunk['imports'] = list(set(imports))
                
                chunks.append(chunk)
    except:
        # If AST parsing fails, return whole file as single chunk
        chunks.append({
            "chunk_type": "file",
            "content": content,
            "start_line": 1,
            "end_line": len(content.split('\n')),
            "imports": []
        })
    
    return chunks

def process_file(file_path, repo_path, repo_name="mcprag"):
    """Process a single file and create document chunks with embeddings"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except:
        return []
    
    language = get_language_from_extension(file_path)
    relative_path = os.path.relpath(file_path, repo_path)
    
    # Extract chunks based on language
    if language == 'python':
        chunks = extract_python_chunks(content, file_path)
    else:
        # For non-Python files, treat whole file as one chunk
        chunks = [{
            "chunk_type": "file",
            "content": content,
            "start_line": 1,
            "end_line": len(content.split('\n')),
            "imports": []
        }]
    
    # Create documents for each chunk
    documents = []
    for i, chunk in enumerate(chunks):
        # Create valid document ID (alphanumeric, underscore, dash only)
        doc_id = hashlib.sha256(f"{relative_path}:{i}".encode()).hexdigest()[:16]
        
        # Create semantic context for better embeddings
        semantic_context_parts = []
        semantic_context_parts.append(f"File: {relative_path}")
        semantic_context_parts.append(f"Language: {language}")
        
        if chunk.get('docstring'):
            semantic_context_parts.append(f"Documentation: {chunk['docstring']}")
        if chunk.get('function_name'):
            semantic_context_parts.append(f"Function: {chunk['function_name']}")
        if chunk.get('class_name'):
            semantic_context_parts.append(f"Class: {chunk['class_name']}")
        if chunk.get('signature'):
            semantic_context_parts.append(f"Signature: {chunk['signature']}")
            
        semantic_context = " | ".join(semantic_context_parts)
        
        # Generate embedding for the content with context
        embedding_text = f"{semantic_context}\n\n{chunk.get('content', '')}"
        
        print(f"  📝 Generating embedding for {relative_path}:{i} ({chunk['chunk_type']})")
        content_vector = get_embedding(embedding_text)
        
        doc = {
            "id": doc_id,
            "content": chunk.get('content', ''),
            "content_vector": content_vector,
            "repository": repo_name,
            "file_path": relative_path,
            "language": language,
            "chunk_type": chunk.get('chunk_type', 'file'),
            "chunk_id": f"{relative_path}:{i}",
            "semantic_context": semantic_context,
            "last_modified": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")[:-4] + "Z",
            "file_extension": Path(file_path).suffix,
            "imports": chunk.get('imports', []),
            "dependencies": []  # Could be populated with function calls
        }
        
        # Add optional fields if they exist
        if chunk.get('function_name'):
            doc['function_name'] = chunk['function_name']
        if chunk.get('class_name'):
            doc['class_name'] = chunk['class_name']
        if chunk.get('docstring'):
            doc['docstring'] = chunk['docstring']
        if chunk.get('signature'):
            doc['signature'] = chunk['signature']
        if chunk.get('start_line'):
            doc['start_line'] = chunk['start_line']
        if chunk.get('end_line'):
            doc['end_line'] = chunk['end_line']
        
        documents.append(doc)
    
    return documents

def index_repository(repo_path, repo_name="mcprag"):
    """Index an entire repository with embeddings"""
    search_client = SearchClient(
        endpoint=endpoint,
        index_name=index_name,
        credential=AzureKeyCredential(admin_key)
    )
    
    # Collect all documents
    all_documents = []
    
    # File extensions to process - focusing on code files
    extensions = {'.py', '.js', '.mjs', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', 
                  '.cs', '.go', '.rs', '.php', '.rb', '.swift', '.kt', '.scala', '.r'}
    
    # Count files
    total_files = 0
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'venv', '.venv', 'docs', 'tests']]
        total_files += sum(1 for f in files if any(f.endswith(ext) for ext in extensions))
    
    print(f"📁 Found {total_files} code files to process")
    
    processed = 0
    for root, dirs, files in os.walk(repo_path):
        # Skip hidden directories and common non-code directories
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'venv', '.venv', 'docs', 'tests']]
        
        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                file_path = os.path.join(root, file)
                docs = process_file(file_path, repo_path, repo_name)
                all_documents.extend(docs)
                processed += 1
                
                if docs:
                    print(f"✅ Processed {file_path} ({len(docs)} chunks) [{processed}/{total_files}]")
    
    # Upload in batches
    batch_size = 10  # Small batches due to large vector size
    total_uploaded = 0
    
    for i in range(0, len(all_documents), batch_size):
        batch = all_documents[i:i+batch_size]
        try:
            result = search_client.upload_documents(documents=batch)
            total_uploaded += len(batch)
            print(f"✅ Uploaded batch {i//batch_size + 1} ({len(batch)} documents, total: {total_uploaded}/{len(all_documents)})")
        except Exception as e:
            print(f"❌ Error uploading batch: {e}")
    
    return len(all_documents)

def main():
    if not endpoint or not admin_key:
        print("❌ Missing ACS_ENDPOINT or ACS_ADMIN_KEY environment variables")
        sys.exit(1)
    
    if not azure_openai_client:
        print("❌ Azure OpenAI not configured properly")
        sys.exit(1)
    
    repo_path = "/home/azureuser/mcprag"
    repo_name = "mcprag"
    
    print(f"\n🔧 Re-indexing repository with Azure OpenAI embeddings...")
    print(f"📍 Repository path: {repo_path}")
    print(f"📦 Repository name: {repo_name}")
    print(f"🧠 Embedding model: {deployment_name} ({embedding_dimensions} dimensions)")
    
    # First, update the index to use 3072 dimensions
    print("\n📐 Updating index for 3072 dimensions...")
    os.system("python create_vector_index_rest.py")
    
    # Index the repository
    doc_count = index_repository(repo_path, repo_name)
    
    # Create search client for verification
    search_client = SearchClient(
        endpoint=endpoint,
        index_name=index_name,
        credential=AzureKeyCredential(admin_key)
    )
    
    # Verify the upload
    print("\n🔍 Verifying index...")
    count = search_client.get_document_count()
    print(f"✅ Total documents in index: {count}")
    
    # Test vector search
    print("\n🧪 Testing vector search...")
    test_query = "search for MCP tools implementation"
    print(f"Query: '{test_query}'")
    
    # Generate embedding for query
    query_vector = get_embedding(test_query)
    
    # Perform vector search
    vector_results = search_client.search(
        search_text=None,
        vector_queries=[{
            "vector": query_vector,
            "fields": "content_vector",
            "kind": "vector",
            "k": 5
        }],
        select=["file_path", "chunk_type", "function_name", "semantic_context"]
    )
    
    print("\nVector search results:")
    for i, result in enumerate(vector_results):
        print(f"{i+1}. {result.get('file_path', 'Unknown')} - {result.get('chunk_type', 'Unknown')}")
        if result.get('function_name'):
            print(f"   Function: {result['function_name']}")
        if result.get('semantic_context'):
            print(f"   Context: {result['semantic_context'][:100]}...")
    
    print(f"\n✅ Re-indexing complete! Indexed {doc_count} documents with Azure OpenAI embeddings.")

if __name__ == "__main__":
    main()