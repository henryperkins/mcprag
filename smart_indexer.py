# smart_indexer.py
import ast
import os
import hashlib
from pathlib import Path
from typing import List, Dict
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv

load_dotenv()

class CodeChunker:
    """Smart code chunking for optimal MCP context."""
    
    def __init__(self):
        self.client = SearchClient(
            endpoint=os.getenv("ACS_ENDPOINT"),
            index_name="codebase-mcp-sota",
            credential=AzureKeyCredential(os.getenv("ACS_ADMIN_KEY"))
        )
    
    def chunk_python_file(self, content: str, file_path: str) -> List[Dict]:
        """Extract semantic chunks from Python code."""
        chunks = []
        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    # Extract function/class with context
                    start_line = node.lineno - 1
                    end_line = node.end_lineno or start_line + 10
                    
                    chunk_lines = content.splitlines()[start_line:end_line]
                    chunk_code = '\n'.join(chunk_lines)
                    
                    # Extract semantic information
                    imports = self._extract_imports(tree)
                    calls = self._extract_function_calls(node)
                    signature = self._get_signature(node)
                    
                    # Create semantic context for better retrieval
                    semantic_context = f"""
{signature} in {file_path}
Uses: {', '.join(imports[:5])}
Calls: {', '.join(calls[:5])}
Purpose: {self._extract_docstring(node) or 'Implementation details in code'}
                    """.strip()
                    
                    chunks.append({
                        "code_chunk": chunk_code,
                        "semantic_context": semantic_context,
                        "function_signature": signature,
                        "imports_used": imports,
                        "calls_functions": calls,
                        "chunk_type": "function" if isinstance(node, ast.FunctionDef) else "class",
                        "line_range": f"{start_line+1}-{end_line}"
                    })
                    
        except:
            # Fallback for non-parseable code
            chunks.append({
                "code_chunk": content[:5000],
                "semantic_context": f"Code from {file_path}",
                "function_signature": "",
                "imports_used": [],
                "calls_functions": [],
                "chunk_type": "file",
                "line_range": "1-"
            })
        
        return chunks
    
    def _extract_imports(self, tree) -> List[str]:
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
        return list(set(imports))
    
    def _extract_function_calls(self, node) -> List[str]:
        calls = []
        for child in ast.walk(node):
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                calls.append(child.func.id)
        return list(set(calls))
    
    def _get_signature(self, node) -> str:
        if isinstance(node, ast.FunctionDef):
            args = [arg.arg for arg in node.args.args]
            return f"def {node.name}({', '.join(args)})"
        elif isinstance(node, ast.ClassDef):
            return f"class {node.name}"
        return ""
    
    def _extract_docstring(self, node) -> str:
        return ast.get_docstring(node) or ""
    
    def index_repository(self, repo_path: str, repo_name: str):
        """Index repository with smart chunking."""
        documents = []
        
        for file_path in Path(repo_path).rglob("*.py"):  # Extend for other languages
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                chunks = self.chunk_python_file(content, str(file_path))
                
                for i, chunk in enumerate(chunks):
                    doc_id = hashlib.md5(
                        f"{repo_name}:{file_path}:{i}".encode()
                    ).hexdigest()
                    
                    documents.append({
                        "id": doc_id,
                        "repo_name": repo_name,
                        "file_path": str(file_path),
                        "language": "python",
                        **chunk
                    })
                    
                    if len(documents) >= 50:
                        self.client.upload_documents(documents)
                        documents = []
                        
            except Exception as e:
                print(f"Error: {file_path}: {e}")
        
        if documents:
            self.client.upload_documents(documents)
        
        print(f"✅ Indexed {repo_name} with semantic chunking")

if __name__ == "__main__":
    chunker = CodeChunker()
    # Index the example repository
    chunker.index_repository("./example-repo", "example-project")
    
    # Add your own repositories here:
    # chunker.index_repository("./path/to/your/repo", "your-project-name")
