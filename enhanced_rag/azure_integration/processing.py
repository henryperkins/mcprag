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
import pathspec
from fnmatch import fnmatch

logger = logging.getLogger(__name__)

# Content truncation limits aligned with Azure Search string constraints (~32KB bytes for some analyzers/fields)
CONTENT_CHAR_LIMIT = 32000

# Repository name validation
_ALLOWED_REPO_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.")

# Default directories to exclude (moved here for use in validation functions)
DEFAULT_EXCLUDE_DIRS = {
    ".git", ".hg", ".svn", ".venv", "venv", "env", "node_modules",
    "dist", "build", "__pycache__", ".mypy_cache", ".pytest_cache",
    ".coverage", ".vscode", ".idea"
}

def validate_repo_name(name: str) -> Optional[str]:
    """
    Validate repository name: non-empty, no slashes/backslashes, sane length,
    and only [_-.A-Za-z0-9] characters.
    
    Args:
        name: Repository name to validate
        
    Returns:
        Error string if invalid, or None if valid.
    """
    if not name or not isinstance(name, str):
        return "Repository name is required"
    if len(name) > 100:
        return "Repository name too long (max 100 chars)"
    if any(c in name for c in "/\\"):
        return "Repository name must not contain slashes"
    if any(c not in _ALLOWED_REPO_CHARS for c in name):
        return "Repository name contains invalid characters; allowed: letters, numbers, '-', '_', '.'"
    return None

def validate_repo_path(repo_path: str, excluded_dirs: Optional[Set[str]] = None) -> Optional[str]:
    """
    Validate repository path against excluded directories.
    
    Warns/guards if the provided repo_path resolves within a known noisy/excluded directory,
    unless MCP_ALLOW_EXTERNAL_ROOTS=true is set in env.
    
    Args:
        repo_path: Repository path to validate
        excluded_dirs: Set of directory names to exclude (uses FileProcessor.DEFAULT_EXCLUDE_DIRS if None)
        
    Returns:
        Warning string if guarded, or None to proceed.
    """
    if excluded_dirs is None:
        # Use default excludes
        excluded_dirs = DEFAULT_EXCLUDE_DIRS
        
    allow_external = os.getenv("MCP_ALLOW_EXTERNAL_ROOTS", "false").lower() == "true"
    resolved = Path(repo_path).resolve()
    parts = set(p.name for p in resolved.parents) | {resolved.name}
    
    if any(d in parts for d in excluded_dirs):
        if not allow_external:
            return (f"Repository path '{resolved}' appears to be inside an excluded directory "
                    f"({', '.join(sorted(excluded_dirs))}). Set MCP_ALLOW_EXTERNAL_ROOTS=true to override.")
        else:
            logger.warning("Proceeding with repo_path inside excluded directory due to MCP_ALLOW_EXTERNAL_ROOTS=true")
    return None

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

    # File patterns always excluded when MCP_INDEX_DEFAULT_EXCLUDES=true
    DEFAULT_EXCLUDE_FILES = {
        "*.pyc", "*.pyo", "*.pyd", "*.swp", "*.swo",
        ".DS_Store", "Thumbs.db"
    }
    
    def __init__(self, extensions: Optional[Set[str]] = None):
        """Initialize file processor with optional extension filtering.

        Loads ignore specifications and configures default-exclude behavior via
        environment flags:
        • MCP_RESPECT_GITIGNORE (default: true)
        • MCP_INDEX_DEFAULT_EXCLUDES (default: true)
        """
        self.extensions = extensions or self.DEFAULT_EXTENSIONS
        # Behaviour flags
        self.respect_gitignore = os.getenv("MCP_RESPECT_GITIGNORE", "true").lower() != "false"
        self.use_default_excludes = os.getenv("MCP_INDEX_DEFAULT_EXCLUDES", "true").lower() != "false"

        # Loaded ignore spec – populated on first repository call
        self._pathspec: Optional[pathspec.PathSpec] = None
        
    def get_language_from_extension(self, file_path: str) -> str:
        """Determine programming language from file extension."""
        ext = Path(file_path).suffix.lower()
        return self.LANGUAGE_MAP.get(ext, 'text')
    
    def should_process_file(self, file_path: str) -> bool:
        """Check if file should be processed based on extension."""
        ext = Path(file_path).suffix.lower()
        return ext in self.extensions

    def process_file(self, file_path: str, repo_path: str, repo_name: str) -> List[Dict[str, Any]]:
        """Wrapper to maintain backward compatibility with callers expecting a class method."""
        return process_file(file_path, repo_path, repo_name)


    # ------------------------------------------------------------------ #
    # Ignore / pruning helpers
    # ------------------------------------------------------------------ #

    def _load_ignore_spec(self, repo_root: Path) -> Optional[pathspec.PathSpec]:
        """Load combined .gitignore and .mcpragignore rules for repo."""
        patterns: List[str] = []
        for fname in (".gitignore", ".mcpragignore"):
            fp = repo_root / fname
            if fp.exists():
                try:
                    patterns.extend(fp.read_text().splitlines())
                except Exception:
                    continue
        if not patterns:
            return None
        # "gitwildmatch" factory avoids direct class import
        return pathspec.PathSpec.from_lines("gitwildmatch", patterns)

    def _should_prune_dir(self, rel_dir: str) -> bool:
        if self.use_default_excludes and Path(rel_dir).name in DEFAULT_EXCLUDE_DIRS:
            return True
        if self._pathspec and self._pathspec.match_file(rel_dir + "/"):
            return True
        return False

    def _should_skip_file(self, rel_file: str) -> bool:
        from fnmatch import fnmatch

        if self.use_default_excludes:
            for patt in self.DEFAULT_EXCLUDE_FILES:
                if fnmatch(Path(rel_file).name, patt):
                    return True
        if self._pathspec and self._pathspec.match_file(rel_file):
            return True
        return False

    def process_repository(self, repo_path: str, repo_name: str) -> List[Dict[str, Any]]:
        """Process entire repository into indexable documents with pruning."""
        base = Path(repo_path).resolve()
        if not base.exists() or not base.is_dir():
            return []

        # (Re)load ignore spec for this repository
        if self.respect_gitignore:
            self._pathspec = self._load_ignore_spec(base)

        documents: List[Dict[str, Any]] = []
        max_files = int(os.getenv("MCP_MAX_INDEX_FILES", "20000"))
        processed = skipped_ext = skipped_ignored = pruned_dirs = 0

        for root, dirnames, filenames in os.walk(base):
            rel_root = os.path.relpath(root, base)

            # Prune dirs in-place for performance
            original_len = len(dirnames)
            dirnames[:] = [d for d in dirnames if not self._should_prune_dir(os.path.join(rel_root, d))]
            pruned_dirs += original_len - len(dirnames)

            for fname in filenames:
                if processed >= max_files:
                    break
                rel_path = os.path.join(rel_root, fname) if rel_root != "." else fname

                if self._should_skip_file(rel_path):
                    skipped_ignored += 1
                    continue

                full_path = base / rel_path
                if not self.should_process_file(str(full_path)):
                    skipped_ext += 1
                    continue

                try:
                    docs = process_file(str(full_path), str(base), repo_name)
                    documents.extend(docs)
                    processed += 1
                except Exception:
                    # unreadable/problematic – skip
                    continue
            if processed >= max_files:
                break

        logger.info(
            "FileProcessor.process_repository summary | processed=%s skipped_ext=%s skipped_ignored=%s pruned_dirs=%s",
            processed,
            skipped_ext,
            skipped_ignored,
            pruned_dirs,
        )
        return documents

# (duplicate original process_repository method removed)




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


def find_repository_root(file_paths: List[str]) -> str:
    """Find the repository root by looking for .git directory.
    
    Args:
        file_paths: List of file paths to search from
        
    Returns:
        Repository root path (directory containing .git) or common parent if not found
    """
    for file_path in file_paths:
        current = Path(file_path).parent
        while current != current.parent:
            if (current / '.git').exists():
                return str(current)
            current = current.parent
    
    # Fall back to common parent directory
    if file_paths:
        return os.path.commonpath([os.path.dirname(p) for p in file_paths])
    return os.getcwd()


def process_file(file_path: str, repo_path: str, repo_name: str) -> List[Dict[str, Any]]:
    """Process a single file and create document chunks for indexing."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except (IOError, OSError):
        return []

    # Use FileProcessor for consistent language detection
    file_processor = FileProcessor()
    language = file_processor.get_language_from_extension(file_path)
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
