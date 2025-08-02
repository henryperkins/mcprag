#!/usr/bin/env python3
"""
Re-index mcprag repository with proper schema
"""
import os
import sys
import json
import hashlib
from pathlib import Path
from dotenv import load_dotenv
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from datetime import datetime
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
        '.sh': 'shell',
        '.bash': 'shell',
        '.zsh': 'shell',
        '.ps1': 'powershell',
        '.sql': 'sql',
        '.dockerfile': 'dockerfile',
        '.makefile': 'makefile',
        '.cmake': 'cmake',
        '.proto': 'protobuf',
        '.graphql': 'graphql',
        '.vim': 'vim',
        '.lua': 'lua',
        '.perl': 'perl',
        '.m': 'objc',
        '.mm': 'objcpp',
        '.dart': 'dart',
        '.ex': 'elixir',
        '.exs': 'elixir',
        '.elm': 'elm',
        '.clj': 'clojure',
        '.hs': 'haskell',
        '.ml': 'ocaml',
        '.fsharp': 'fsharp',
        '.fs': 'fsharp',
        '.jl': 'julia',
        '.nim': 'nim',
        '.v': 'vlang',
        '.zig': 'zig',
    }
    
    suffix = Path(file_path).suffix.lower()
    return ext_map.get(suffix, 'text')

def extract_python_functions(content, file_path):
    """Extract functions and classes from Python code"""
    chunks = []
    try:
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            chunk = None
            
            if isinstance(node, ast.FunctionDef):
                # Extract function
                start_line = node.lineno
                end_line = node.end_lineno or start_line
                
                # Get function signature
                args = []
                for arg in node.args.args:
                    args.append(arg.arg)
                signature = f"def {node.name}({', '.join(args)})"
                
                # Get docstring
                docstring = ast.get_docstring(node) or ""
                
                # Get function body lines
                lines = content.split('\n')[start_line-1:end_line]
                function_content = '\n'.join(lines)
                
                chunk = {
                    "chunk_type": "function",
                    "function_name": node.name,
                    "signature": signature,
                    "docstring": docstring,
                    "content": function_content,
                    "start_line": start_line,
                    "end_line": end_line,
                }
                
            elif isinstance(node, ast.ClassDef):
                # Extract class
                start_line = node.lineno
                end_line = node.end_lineno or start_line
                
                # Get class content
                lines = content.split('\n')[start_line-1:end_line]
                class_content = '\n'.join(lines)
                
                # Get docstring
                docstring = ast.get_docstring(node) or ""
                
                chunk = {
                    "chunk_type": "class",
                    "class_name": node.name,
                    "docstring": docstring,
                    "content": class_content,
                    "start_line": start_line,
                    "end_line": end_line,
                }
            
            if chunk:
                # Add common fields
                chunk.update({
                    "id": hashlib.md5(f"{file_path}:{chunk.get('function_name') or chunk.get('class_name')}".encode()).hexdigest(),
                    "file_path": file_path,
                    "file_name": Path(file_path).name,
                    "repository": "mcprag",
                    "language": "python",
                    "last_modified": datetime.utcnow().isoformat() + "Z",
                    "imports": [],  # Could extract these too
                    "dependencies": [],  # Could analyze function calls
                    "tags": [],
                    "framework": None,
                })
                chunks.append(chunk)
                
    except SyntaxError:
        # If parsing fails, create a single chunk for the whole file
        chunk = {
            "id": hashlib.md5(f"{file_path}:full".encode()).hexdigest(),
            "chunk_type": "file",
            "file_path": file_path,
            "file_name": Path(file_path).name,
            "repository": "mcprag",
            "language": "python",
            "content": content,
            "start_line": 1,
            "end_line": len(content.split('\n')),
            "last_modified": datetime.utcnow().isoformat() + "Z",
        }
        chunks.append(chunk)
    
    return chunks

def chunk_file(file_path, content):
    """Create chunks from a file based on its type"""
    language = get_language_from_extension(file_path)
    
    if language == 'python':
        return extract_python_functions(content, str(file_path))
    else:
        # For non-Python files, create a single chunk
        return [{
            "id": hashlib.md5(f"{file_path}:full".encode()).hexdigest(),
            "chunk_type": "file",
            "file_path": str(file_path),
            "file_name": Path(file_path).name,
            "repository": "mcprag",
            "language": language,
            "content": content,
            "start_line": 1,
            "end_line": len(content.split('\n')),
            "last_modified": datetime.utcnow().isoformat() + "Z",
        }]

def main():
    print("🔧 Re-indexing mcprag repository...")
    
    if not endpoint or not admin_key:
        print("❌ Missing Azure Search credentials")
        sys.exit(1)
    
    # Create search client
    search_client = SearchClient(
        endpoint=endpoint,
        index_name=index_name,
        credential=AzureKeyCredential(admin_key)
    )
    
    # Get current directory
    repo_path = Path.cwd()
    print(f"📍 Repository path: {repo_path}")
    
    # Collect all code files
    all_chunks = []
    file_extensions = {'.py', '.js', '.mjs', '.ts', '.jsx', '.tsx', '.md', '.json', '.yaml', '.yml'}
    
    for ext in file_extensions:
        for file_path in repo_path.rglob(f"*{ext}"):
            # Skip hidden directories and common exclusions
            if any(part.startswith('.') for part in file_path.parts):
                continue
            if any(part in ['node_modules', 'venv', '__pycache__', 'dist', 'build'] for part in file_path.parts):
                continue
            
            try:
                content = file_path.read_text(encoding='utf-8')
                chunks = chunk_file(file_path, content)
                all_chunks.extend(chunks)
                print(f"✅ Processed {file_path} ({len(chunks)} chunks)")
            except Exception as e:
                print(f"❌ Error processing {file_path}: {e}")
    
    print(f"\n📊 Total chunks to index: {len(all_chunks)}")
    
    # Delete existing mcprag documents
    print("\n🗑️  Deleting existing mcprag documents...")
    try:
        # Search for all mcprag documents
        results = search_client.search(
            search_text="*",
            filter="repository eq 'mcprag'",
            top=1000
        )
        
        docs_to_delete = []
        for doc in results:
            docs_to_delete.append({"id": doc["id"]})
        
        if docs_to_delete:
            search_client.delete_documents(docs_to_delete)
            print(f"✅ Deleted {len(docs_to_delete)} existing documents")
        else:
            print("ℹ️  No existing documents to delete")
            
    except Exception as e:
        print(f"⚠️  Error deleting existing documents: {e}")
    
    # Upload new documents in batches
    print("\n📝 Uploading new documents...")
    batch_size = 100
    for i in range(0, len(all_chunks), batch_size):
        batch = all_chunks[i:i+batch_size]
        try:
            result = search_client.merge_or_upload_documents(batch)
            print(f"✅ Uploaded batch {i//batch_size + 1}/{(len(all_chunks) + batch_size - 1)//batch_size}")
        except Exception as e:
            print(f"❌ Error uploading batch: {e}")
    
    # Verify the upload
    print("\n🔍 Verifying index...")
    count = search_client.get_document_count()
    print(f"✅ Total documents in index: {count}")
    
    # Test search
    print("\n🧪 Testing search...")
    test_results = search_client.search(
        search_text="mcp",
        filter="repository eq 'mcprag'",
        top=3
    )
    
    print("Search results for 'mcp' in mcprag repository:")
    for i, result in enumerate(test_results):
        print(f"{i+1}. {result.get('file_path', 'Unknown')} - {result.get('chunk_type', 'Unknown')}")
    
    print("\n✅ Re-indexing complete!")

if __name__ == "__main__":
    main()