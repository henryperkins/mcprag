"""Consolidated file processing utilities for Azure Search indexing.

This module serves as the single source of truth for all file processing
operations across the azure_integration package. It consolidates the
previously duplicated implementations from:
- processing.py (this file)
- reindex_operations.py 
- automation/cli_manager.py

Usage:
    from .processing import FileProcessor
    
    processor = FileProcessor()
    documents = processor.process_file(file_path, repo_path, repo_name)
"""
from __future__ import annotations
import ast
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
import os

logger = logging.getLogger(__name__)


class FileProcessor:
    """Consolidated file processor for all Azure Search indexing operations."""
    
    # Language mapping - single source of truth
    LANGUAGE_MAP = {
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
    
    # Default extensions to process
    DEFAULT_EXTENSIONS = {
        '.py', '.js', '.mjs', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c',
        '.cs', '.go', '.rs', '.php', '.rb', '.swift', '.kt', '.scala', '.r',
        '.md', '.json', '.yaml', '.yml', '.xml', '.html', '.css'
    }
    
    def __init__(self, extensions: Optional[Set[str]] = None):
        """Initialize file processor."""
        self.extensions = extensions or self.DEFAULT_EXTENSIONS
        
    def get_language_from_extension(self, file_path: str) -> str:
        """Determine programming language from file extension."""
        ext = Path(file_path).suffix.lower()
        return self.LANGUAGE_MAP.get(ext, 'text')
    
    def should_process_file(self, file_path: str) -> bool:
        """Check if file should be processed based on extension."""
        ext = Path(file_path).suffix.lower()
        return ext in self.extensions


def get_language_from_extension(file_path: str) -> str:
    """Legacy function - use FileProcessor.get_language_from_extension() instead."""
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


def extract_python_chunks(content: str, file_path: str) -> List[Dict[str, Any]]:
    """Extract semantic chunks from Python code using AST."""
    chunks: List[Dict[str, Any]] = []
    try:
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                start = getattr(node, "lineno", 1)
                end = getattr(node, "end_lineno", start)
                chunk = {
                    "chunk_type": "function" if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else "class",
                    "function_name": node.name if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else None,
                    "class_name": node.name if isinstance(node, ast.ClassDef) else None,
                    "start_line": start,
                    "end_line": end,
                    "docstring": ast.get_docstring(node) or "",
                    "signature": f"def {node.name}" if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else f"class {node.name}",
                }
                lines = content.split('\n')
                chunk['content'] = '\n'.join(lines[start-1:end])
                chunks.append(chunk)
    except (SyntaxError, ValueError):
        chunks.append({
            "chunk_type": "file",
            "content": content,
            "start_line": 1,
            "end_line": len(content.split('\n'))
        })
    return chunks


def process_file(file_path: str, repo_path: str, repo_name: str) -> List[Dict[str, Any]]:
    """Process a single file and create document chunks for indexing."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except (IOError, OSError):
        return []

    language = get_language_from_extension(file_path)
    relative_path = os.path.relpath(file_path, repo_path)

    if language == 'python':
        chunks = extract_python_chunks(content, file_path)
    else:
        chunks = [{
            "chunk_type": "file",
            "content": content,
            "start_line": 1,
            "end_line": len(content.split('\n'))
        }]

    documents: List[Dict[str, Any]] = []
    for i, chunk in enumerate(chunks):
        doc_id = hashlib.sha256(f"{repo_name}:{relative_path}:{i}".encode()).hexdigest()[:16]
        doc: Dict[str, Any] = {
            "id": doc_id,
            "content": chunk.get('content', ''),
            "file_path": relative_path,
            "repository": repo_name,
            "language": language,
            "chunk_type": chunk.get('chunk_type', 'file'),
            "chunk_id": f"{relative_path}:{i}",
            "last_modified": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")[:-4] + "Z",
            "file_extension": Path(file_path).suffix
        }
        for key in ("function_name", "class_name", "docstring", "signature", "start_line", "end_line"):
            if key in chunk and chunk[key] is not None:
                doc[key] = chunk[key]
        documents.append(doc)
    return documents