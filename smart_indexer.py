# smart_indexer.py
import ast
import os
import hashlib
import subprocess
import json
import argparse
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

    def _parse_js_ts(self, path: Path) -> dict:
        """Parse JavaScript/TypeScript files using Babel AST."""
        try:
            res = subprocess.run(
                ["node", "parse_js.mjs", str(path)],
                capture_output=True, text=True, check=False
            )
            if res.returncode == 0 and res.stdout:
                return json.loads(res.stdout)
        except Exception as e:
            print(f"Warning: Failed to parse {path} with Babel: {e}")

        # Fallback to empty metadata
        return {
            "function_signature": "",
            "imports_used": [],
            "calls_functions": []
        }

    def chunk_js_ts_file(self, content: str, file_path: str) -> List[Dict]:
        """Extract semantic chunks from JavaScript/TypeScript code."""
        chunks = []
        path = Path(file_path)

        # Get metadata from Babel parser
        meta = self._parse_js_ts(path)

        # Create a single chunk for the file (can be enhanced to split by functions)
        chunk = {
            "code_chunk": content[:8000],  # Keep chunks manageable
            "semantic_context": f"{meta.get('function_signature', '')} in {file_path}",
            "function_signature": meta.get("function_signature", ""),
            "imports_used": meta.get("imports_used", []),
            "calls_functions": meta.get("calls_functions", []),
            "chunk_type": "function-or-file",
            "line_range": "1-"
        }
        chunks.append(chunk)

        return chunks

    def index_repository(self, repo_path: str, repo_name: str):
        """Index repository with smart chunking."""
        documents = []

        # Define file patterns and their handlers
        file_patterns = [
            ("*.py", "python", self.chunk_python_file),
            ("*.js", "javascript", self.chunk_js_ts_file),
            ("*.ts", "typescript", self.chunk_js_ts_file),
        ]

        for pattern, language, chunker_func in file_patterns:
            for file_path in Path(repo_path).rglob(pattern):
                try:
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                    chunks = chunker_func(content, str(file_path))

                    for i, chunk in enumerate(chunks):
                        doc_id = hashlib.md5(
                            f"{repo_name}:{file_path}:{i}".encode()
                        ).hexdigest()

                        documents.append({
                            "id": doc_id,
                            "repo_name": repo_name,
                            "file_path": str(file_path),
                            "language": language,
                            **chunk
                        })

                        if len(documents) >= 50:
                            self.client.merge_or_upload_documents(documents)
                            documents = []

                except Exception as e:
                    print(f"Error: {file_path}: {e}")

        if documents:
            self.client.merge_or_upload_documents(documents)

        print(f"✅ Indexed {repo_name} with semantic chunking")

    def index_changed_files(self, file_paths: List[str], repo_name: str = "current-repo"):
        """Index only the specified changed files."""
        documents = []

        for file_path_str in file_paths:
            file_path = Path(file_path_str)
            if not file_path.exists():
                continue

            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')

                # Determine language and chunker
                if file_path.suffix == '.py':
                    chunks = self.chunk_python_file(content, str(file_path))
                    language = "python"
                elif file_path.suffix in {'.js', '.ts'}:
                    chunks = self.chunk_js_ts_file(content, str(file_path))
                    language = "javascript" if file_path.suffix == '.js' else "typescript"
                else:
                    continue  # Skip unsupported file types

                for i, chunk in enumerate(chunks):
                    doc_id = hashlib.md5(
                        f"{repo_name}:{file_path}:{i}".encode()
                    ).hexdigest()

                    documents.append({
                        "id": doc_id,
                        "repo_name": repo_name,
                        "file_path": str(file_path),
                        "language": language,
                        **chunk
                    })

            except Exception as e:
                print(f"Error processing {file_path}: {e}")

        if documents:
            self.client.merge_or_upload_documents(documents)
            print(f"✅ Re-indexed {len(documents)} documents from changed files")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Smart code indexer for Azure Cognitive Search")
    parser.add_argument("--files", nargs="*", help="Specific files to (re)index")
    parser.add_argument("--repo-path", default="./", help="Repository path to index")
    parser.add_argument("--repo-name", default="mcprag", help="Repository name for indexing")
    args = parser.parse_args()

    chunker = CodeChunker()

    if args.files:
        # Index only changed files (for CI/CD)
        chunker.index_changed_files(args.files, args.repo_name)
    else:
        # Index entire repository
        chunker.index_repository(args.repo_path, args.repo_name)

        # Also index the example repository if it exists
        if Path("./example-repo").exists():
            chunker.index_repository("./example-repo", "example-project")
