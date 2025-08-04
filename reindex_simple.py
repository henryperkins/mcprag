#!/usr/bin/env python3
"""
Simple re-index script for mcprag repository without repository field
"""
import os
import sys
import json
import hashlib
from pathlib import Path
from dotenv import load_dotenv
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from datetime import datetime, timezone
import ast

# Load environment
load_dotenv()

# Configuration
endpoint = os.getenv("ACS_ENDPOINT")
admin_key = os.getenv("ACS_ADMIN_KEY")
index_name = "codebase-mcp-sota"

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
        '.css': 'css',
        '.scss': 'scss',
        '.sass': 'sass'
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
                
                chunks.append(chunk)
    except:
        # If AST parsing fails, return whole file as single chunk
        chunks.append({
            "chunk_type": "file",
            "content": content,
            "start_line": 1,
            "end_line": len(content.split('\n'))
        })
    
    return chunks

def process_file(file_path, repo_path):
    """Process a single file and create document chunks"""
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
            "end_line": len(content.split('\n'))
        }]
    
    # Create documents for each chunk
    documents = []
    for i, chunk in enumerate(chunks):
        doc_id = hashlib.sha256(f"{relative_path}:{i}".encode()).hexdigest()[:16]
        
        doc = {
            "id": doc_id,
            "content": chunk.get('content', ''),
            "file_path": relative_path,
            "language": language,
            "chunk_type": chunk.get('chunk_type', 'file'),
            "chunk_id": f"{relative_path}:{i}",
            "last_modified": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")[:-4] + "Z",
            "file_extension": Path(file_path).suffix
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

def index_repository(repo_path):
    """Index an entire repository"""
    search_client = SearchClient(
        endpoint=endpoint,
        index_name=index_name,
        credential=AzureKeyCredential(admin_key)
    )
    
    # Collect all documents
    all_documents = []
    
    # File extensions to process
    extensions = {'.py', '.js', '.mjs', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', 
                  '.cs', '.go', '.rs', '.php', '.rb', '.swift', '.kt', '.scala', '.r',
                  '.md', '.json', '.yaml', '.yml', '.xml', '.html', '.css'}
    
    for root, dirs, files in os.walk(repo_path):
        # Skip hidden directories and common non-code directories
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'venv', '.venv']]
        
        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                file_path = os.path.join(root, file)
                docs = process_file(file_path, repo_path)
                all_documents.extend(docs)
                
                if docs:
                    print(f"✅ Processed {file_path} ({len(docs)} chunks)")
    
    # Upload in batches
    batch_size = 100
    for i in range(0, len(all_documents), batch_size):
        batch = all_documents[i:i+batch_size]
        try:
            result = search_client.upload_documents(documents=batch)
            print(f"✅ Uploaded batch {i//batch_size + 1} ({len(batch)} documents)")
        except Exception as e:
            print(f"❌ Error uploading batch: {e}")
    
    return len(all_documents)

def main():
    if not endpoint or not admin_key:
        print("❌ Missing ACS_ENDPOINT or ACS_ADMIN_KEY environment variables")
        sys.exit(1)
    
    repo_path = "/home/azureuser/mcprag"
    
    print(f"🔧 Re-indexing repository...")
    print(f"📍 Repository path: {repo_path}")
    
    # Index the repository
    doc_count = index_repository(repo_path)
    
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
    
    # Test search
    print("\n🧪 Testing search...")
    test_results = search_client.search(
        search_text="mcp",
        top=3
    )
    
    print("Search results for 'mcp':")
    for i, result in enumerate(test_results):
        print(f"{i+1}. {result.get('file_path', 'Unknown')} - {result.get('chunk_type', 'Unknown')}")
    
    print(f"\n✅ Re-indexing complete! Indexed {doc_count} documents.")

if __name__ == "__main__":
    main()