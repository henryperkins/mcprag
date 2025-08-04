"""CLI automation manager for Azure AI Search.

This module consolidates CLI functionality into the automation framework,
providing a unified interface for repository indexing, file processing,
and index management operations.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple, AsyncIterator
from datetime import datetime
from pathlib import Path
import os
import hashlib
import ast

from ..rest import SearchOperations
from ..embedding_provider import IEmbeddingProvider
from .data_manager import DataAutomation
from .embedding_manager import EmbeddingAutomation
from .reindex_manager import ReindexAutomation

logger = logging.getLogger(__name__)


class CLIAutomation:
    """Consolidates CLI operations into the automation framework."""
    
    def __init__(self,
                 operations: SearchOperations,
                 embedding_provider: Optional[IEmbeddingProvider] = None):
        """Initialize CLI automation.
        
        Args:
            operations: SearchOperations instance
            embedding_provider: Optional embedding provider
        """
        self.ops = operations
        self.data_automation = DataAutomation(operations)
        self.embedding_automation = EmbeddingAutomation(operations, embedding_provider)
        self.reindex_automation = ReindexAutomation(operations, embedding_provider)
        
        # File extension mapping
        self.language_map = {
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
        self.default_extensions = {
            '.py', '.js', '.mjs', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c',
            '.cs', '.go', '.rs', '.php', '.rb', '.swift', '.kt', '.scala', '.r',
            '.md', '.json', '.yaml', '.yml', '.xml', '.html', '.css'
        }
    
    def _get_language_from_extension(self, file_path: str) -> str:
        """Determine language from file extension."""
        ext = Path(file_path).suffix.lower()
        return self.language_map.get(ext, 'text')
    
    def _extract_python_chunks(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Extract semantic chunks from Python code."""
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
                        "signature": self._get_signature(node)
                    }
                    
                    # Extract code content
                    lines = content.split('\n')
                    chunk_content = '\n'.join(lines[chunk['start_line']-1:chunk['end_line']])
                    chunk['content'] = chunk_content
                    
                    chunks.append(chunk)
        except (SyntaxError, ValueError):
            # If AST parsing fails, return whole file as single chunk
            chunks.append({
                "chunk_type": "file",
                "content": content,
                "start_line": 1,
                "end_line": len(content.split('\n'))
            })
        
        return chunks
    
    def _get_signature(self, node) -> str:
        """Extract function/class signature."""
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            params = []
            for arg in node.args.args:
                params.append(arg.arg)
            param_str = ", ".join(params)
            prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
            return f"{prefix} {node.name}({param_str})"
        elif isinstance(node, ast.ClassDef):
            bases = [base.id if hasattr(base, 'id') else str(base) for base in node.bases]
            if bases:
                return f"class {node.name}({', '.join(bases)})"
            return f"class {node.name}"
        return ""
    
    async def process_file(
        self,
        file_path: str,
        repo_path: str,
        repo_name: str,
        generate_embeddings: bool = True
    ) -> List[Dict[str, Any]]:
        """Process a single file and create document chunks.
        
        Args:
            file_path: Path to file
            repo_path: Repository root path
            repo_name: Repository name
            generate_embeddings: Whether to generate embeddings
            
        Returns:
            List of document chunks
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except (IOError, OSError):
            logger.warning(f"Failed to read file: {file_path}")
            return []
        
        language = self._get_language_from_extension(file_path)
        relative_path = os.path.relpath(file_path, repo_path)
        
        # Extract chunks based on language
        if language == 'python':
            chunks = self._extract_python_chunks(content, file_path)
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
            doc_id = hashlib.sha256(f"{repo_name}:{relative_path}:{i}".encode()).hexdigest()[:16]
            
            doc = {
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
            
            # Add optional fields if they exist
            optional_fields = ['function_name', 'class_name', 'docstring', 'signature', 'start_line', 'end_line']
            for field in optional_fields:
                if chunk.get(field):
                    doc[field] = chunk[field]
            
            documents.append(doc)
        
        # Generate embeddings if requested
        if generate_embeddings and documents:
            context_fields = ['function_name', 'class_name', 'signature', 'docstring']
            documents, stats = await self.embedding_automation.enrich_documents_with_embeddings(
                documents=documents,
                text_field='content',
                embedding_field='content_vector',
                context_fields=context_fields
            )
            logger.info(f"Embedding stats for {file_path}: {stats}")
        
        return documents
    
    async def index_repository(
        self,
        repo_path: str,
        repo_name: str,
        index_name: str,
        patterns: Optional[List[str]] = None,
        generate_embeddings: bool = True,
        batch_size: int = 100,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """Index an entire repository.
        
        Args:
            repo_path: Repository path
            repo_name: Repository name
            index_name: Target index name
            patterns: Optional file patterns to include
            generate_embeddings: Whether to generate embeddings
            batch_size: Batch size for uploads
            progress_callback: Optional progress callback
            
        Returns:
            Indexing results
        """
        start_time = datetime.utcnow()
        logger.info(f"Starting repository indexing: {repo_name} from {repo_path}")
        
        # Determine extensions to process
        extensions = self.default_extensions
        if patterns:
            extensions = set()
            for pattern in patterns:
                if pattern.startswith('*.'):
                    extensions.add(pattern[1:])
        
        # Collect all files to process
        files_to_process = []
        for root, dirs, files in os.walk(repo_path):
            # Skip hidden directories and common non-code directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and 
                      d not in ['node_modules', '__pycache__', 'venv', '.venv', 'dist', 'build']]
            
            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    files_to_process.append(os.path.join(root, file))
        
        logger.info(f"Found {len(files_to_process)} files to process")
        
        # Process files and collect documents
        all_documents = []
        processed_files = 0
        
        for file_path in files_to_process:
            docs = await self.process_file(file_path, repo_path, repo_name, generate_embeddings)
            all_documents.extend(docs)
            processed_files += 1
            
            if docs:
                logger.info(f"Processed {file_path} ({len(docs)} chunks)")
            
            # Progress callback
            if progress_callback and processed_files % 10 == 0:
                await progress_callback({
                    "files_processed": processed_files,
                    "total_files": len(files_to_process),
                    "documents_created": len(all_documents)
                })
        
        # Upload documents
        logger.info(f"Uploading {len(all_documents)} documents to index {index_name}")
        
        async def document_generator():
            for doc in all_documents:
                yield doc
        
        upload_result = await self.data_automation.bulk_upload(
            index_name=index_name,
            documents=document_generator(),
            batch_size=batch_size,
            progress_callback=progress_callback
        )
        
        elapsed = (datetime.utcnow() - start_time).total_seconds()
        
        return {
            "repository": repo_name,
            "files_processed": processed_files,
            "documents_created": len(all_documents),
            "upload_result": upload_result,
            "elapsed_seconds": round(elapsed, 2),
            "files_per_second": round(processed_files / elapsed, 2) if elapsed > 0 else 0
        }
    
    async def index_changed_files(
        self,
        file_paths: List[str],
        repo_name: str,
        index_name: str,
        generate_embeddings: bool = True
    ) -> Dict[str, Any]:
        """Index specific changed files.
        
        Args:
            file_paths: List of file paths to index
            repo_name: Repository name
            index_name: Target index name
            generate_embeddings: Whether to generate embeddings
            
        Returns:
            Indexing results
        """
        start_time = datetime.utcnow()
        logger.info(f"Indexing {len(file_paths)} changed files")
        
        # Find the repo root
        repo_path = None
        for file_path in file_paths:
            current = Path(file_path).parent
            while current != current.parent:
                if (current / '.git').exists():
                    repo_path = str(current)
                    break
                current = current.parent
            if repo_path:
                break
        
        if not repo_path:
            # Fall back to common parent
            repo_path = os.path.commonpath([os.path.dirname(p) for p in file_paths])
        
        # Process files
        all_documents = []
        processed_files = 0
        
        for file_path in file_paths:
            if os.path.exists(file_path) and os.path.isfile(file_path):
                docs = await self.process_file(file_path, repo_path, repo_name, generate_embeddings)
                all_documents.extend(docs)
                processed_files += 1
                
                if docs:
                    logger.info(f"Processed {file_path} ({len(docs)} chunks)")
        
        # Upload documents
        async def document_generator():
            for doc in all_documents:
                yield doc
        
        upload_result = await self.data_automation.bulk_upload(
            index_name=index_name,
            documents=document_generator(),
            batch_size=100
        )
        
        elapsed = (datetime.utcnow() - start_time).total_seconds()
        
        return {
            "files_requested": len(file_paths),
            "files_processed": processed_files,
            "documents_created": len(all_documents),
            "upload_result": upload_result,
            "elapsed_seconds": round(elapsed, 2)
        }
    
    async def create_indexing_report(
        self,
        index_name: str,
        repo_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a comprehensive indexing report.
        
        Args:
            index_name: Index name
            repo_name: Optional repository name filter
            
        Returns:
            Indexing report
        """
        # Get index health
        health = await self.reindex_automation.get_index_health(index_name)
        
        # Get embedding stats
        embedding_stats = await self.embedding_automation.get_embedding_stats()
        
        # Get sample documents
        filter_query = f"repository eq '{repo_name}'" if repo_name else None
        sample_results = await self.ops.search_documents(
            index_name=index_name,
            search_text="*",
            filter=filter_query,
            select=["repository", "language", "chunk_type"],
            top=1000
        )
        
        documents = sample_results.get("value", [])
        
        # Analyze documents
        repo_counts = {}
        language_counts = {}
        chunk_type_counts = {}
        
        for doc in documents:
            # Repository counts
            repo = doc.get("repository", "unknown")
            repo_counts[repo] = repo_counts.get(repo, 0) + 1
            
            # Language counts
            lang = doc.get("language", "unknown")
            language_counts[lang] = language_counts.get(lang, 0) + 1
            
            # Chunk type counts
            chunk_type = doc.get("chunk_type", "unknown")
            chunk_type_counts[chunk_type] = chunk_type_counts.get(chunk_type, 0) + 1
        
        return {
            "index_name": index_name,
            "report_time": datetime.utcnow().isoformat(),
            "health": health,
            "embedding_stats": embedding_stats,
            "document_analysis": {
                "total_sampled": len(documents),
                "repositories": repo_counts,
                "languages": language_counts,
                "chunk_types": chunk_type_counts
            },
            "recommendations": await self.reindex_automation.analyze_reindex_need()
        }