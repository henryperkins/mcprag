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
from typing import List, Dict, Any, Optional, Set, Tuple
import os

logger = logging.getLogger(__name__)

# Content truncation limits aligned with Azure Search string constraints (~32KB bytes for some analyzers/fields)
CONTENT_CHAR_LIMIT = 32000

# Lightweight extension-to-MIME map with overrides for common code types
EXT_MIME_MAP = {
    ".py": "text/x-python",
    ".sh": "application/x-sh",
    ".bash": "application/x-sh",
    ".zsh": "application/x-sh",
    ".js": "application/javascript",
    ".mjs": "application/javascript",
    ".ts": "text/typescript",
    ".tsx": "text/tsx",
    ".jsx": "text/jsx",
    ".json": "application/json",
    ".md": "text/markdown",
    ".txt": "text/plain",
    ".html": "text/html",
    ".css": "text/css",
    ".yaml": "text/yaml",
    ".yml": "text/yaml",
    ".xml": "application/xml",
    ".java": "text/x-java-source",
    ".c": "text/x-c",
    ".cpp": "text/x-c++",
    ".h": "text/x-c",
    ".hpp": "text/x-c++",
    ".rs": "text/rust",
    ".go": "text/x-go",
    ".rb": "text/x-ruby",
    ".php": "application/x-php",
    ".cs": "text/x-csharp",
    ".kt": "text/x-kotlin",
    ".scala": "text/x-scala",
    ".r": "text/x-r-source",
    ".dockerfile": "text/x-dockerfile",
}


class FileProcessor:
    """Consolidated file processor for all Azure Search indexing operations."""
    
    @staticmethod
    def truncate_content(content: str, limit: int = CONTENT_CHAR_LIMIT) -> Tuple[str, bool]:
        """Truncate content to a safe character limit with ellipsis.
        
        Returns:
            (possibly_truncated_content, was_truncated)
        """
        if content is None:
            return "", False
        if len(content) <= limit:
            return content, False
        # Reserve a small suffix for marker
        truncated = content[: max(0, limit - 3)] + "..."
        return truncated, True

    @staticmethod
    def detect_mime(file_path: str, fallback_content: Optional[bytes] = None) -> str:
        """Detect MIME type using extension map first, with optional python-magic fallback."""
        ext = Path(file_path).suffix.lower()
        if ext in EXT_MIME_MAP:
            return EXT_MIME_MAP[ext]
        # Optional python-magic if available
        try:
            import magic  # type: ignore
            if fallback_content is not None:
                return magic.from_buffer(fallback_content, mime=True) or "application/octet-stream"
            return magic.from_file(str(file_path), mime=True) or "application/octet-stream"
        except Exception:
            # Fallback to generic text for unknown code-like files
            return "application/octet-stream"

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

    def process_repository(self, repo_path: str, repo_name: str) -> List[Dict[str, Any]]:
        """Process an entire repository into indexable documents.

        Walks the repo directory, filters by known extensions, and delegates
        to process_file for chunk extraction.
        """
        base = Path(repo_path).resolve()
        if not base.exists() or not base.is_dir():
            return []

        documents: List[Dict[str, Any]] = []
        # Limit files to avoid accidental huge scans; reasonable default 20k files
        max_files = int(os.getenv("MCP_MAX_INDEX_FILES", "20000"))
        count = 0
        for p in base.rglob("*"):
            if count >= max_files:
                break
            if not p.is_file():
                continue
            if not self.should_process_file(str(p)):
                continue
            try:
                docs = process_file(str(p), str(base), repo_name)
                documents.extend(docs)
                count += 1
            except Exception:
                # Skip unreadable/problematic files
                continue
        return documents


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
    """Extract semantic chunks from Python code using AST.

    Applies content length limits before parsing to reduce DoS risk from
    pathological inputs.
    """
    chunks: List[Dict[str, Any]] = []
    try:
        # Enforce a reasonable cap before AST parsing
        safe_content, _ = FileProcessor.truncate_content(content, limit=min(CONTENT_CHAR_LIMIT, 32000))
        tree = ast.parse(safe_content)
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
                lines = safe_content.split('\n')
                chunk['content'] = '\n'.join(lines[start-1:end])
                chunks.append(chunk)
    except (SyntaxError, ValueError):
        chunks.append({
            "chunk_type": "file",
            "content": (content or "")[:CONTENT_CHAR_LIMIT],
            "start_line": 1,
            "end_line": len((content or "").split('\n'))
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
