"""
Remote Repository Indexer
Indexes GitHub repositories without local checkout using the GitHub API
"""

import os
import hashlib
import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

try:
    from azure.search.documents import SearchClient
    from azure.core.credentials import AzureKeyCredential
except ImportError:
    raise ImportError("azure-search-documents package required for remote indexing. "
                      "Install with: pip install azure-search-documents")

from enhanced_rag.core.config import get_config
from enhanced_rag.azure_integration.embedding_provider import AzureOpenAIEmbeddingProvider
from enhanced_rag.code_understanding import CodeChunker
from .api_client import GitHubClient

logger = logging.getLogger(__name__)


def get_document_byte_size(doc: Dict[str, Any]) -> int:
    """Calculate the byte size of a document when serialized to JSON.

    Args:
        doc: Document dictionary to check

    Returns:
        Size in bytes of the JSON serialized document
    """
    try:
        # Serialize to JSON to get actual payload size
        json_str = json.dumps(doc, ensure_ascii=False)
        return len(json_str.encode('utf-8'))
    except Exception:
        # Fallback to character count if serialization fails
        content = doc.get("content", "")
        return len(str(content)) if content else 0


class RemoteIndexer:
    """Indexes remote GitHub repositories directly via API."""

    def __init__(self, config=None):
        """Initialize the remote repository indexer.

        Args:
            config: Configuration object (uses get_config() if not provided)
        """
        # --------------------------------------------------------------
        # Resolve configuration – accept either the EnhancedConfig object
        # or a plain ``dict`` produced via ``Config.model_dump()``.  Falling
        # back to the global singleton keeps existing behaviour while
        # allowing callers to inject an ad-hoc JSON/dict configuration.
        # --------------------------------------------------------------

        if config is None:
            config = get_config()

        elif isinstance(config, dict):
            # Reconstruct an EnhancedConfig instance so downstream attribute
            # access (``config.azure.*``) works uniformly.
            from enhanced_rag.core.config import get_config as _get_default
            base = _get_default()
            azure_overrides = config.get("azure", {})
            for key in ("endpoint", "admin_key", "index_name"):
                if key in azure_overrides:
                    setattr(base.azure, key, azure_overrides[key])
            # Other top-level sections can be merged similarly if required.
            config = base

        # Check for network disabled environment
        self.network_disabled = os.getenv("CODEX_SANDBOX_NETWORK_DISABLED") == "1"

        # Get Azure Search configuration
        self.endpoint = config.azure.endpoint
        self.admin_key = config.azure.admin_key
        self.index_name = config.azure.index_name or "codebase-mcp-sota"

        # Create search client
        if self.network_disabled:
            logger.warning("Network is disabled (CODEX_SANDBOX_NETWORK_DISABLED=1). "
                          "Azure Search operations will be stubbed.")
            self.search_client = None  # Will be checked in methods
        else:
            self.search_client = SearchClient(
                endpoint=self.endpoint,
                index_name=self.index_name,
                credential=AzureKeyCredential(self.admin_key)
            )

        # Initialize embedding provider based on config
        self.provider = None
        if config.embedding.provider == "client":
            self.provider = AzureOpenAIEmbeddingProvider()
        elif config.embedding.provider in {"none", "azure_openai_http"}:
            # No client-side embedding for these modes
            self.provider = None

        # Initialize GitHub client
        self.github_client = GitHubClient()

        # Initialize code chunker
        self.chunker = CodeChunker()

        self.batch_size = 50
        self.logger = logging.getLogger(__name__)

        # Determine if integrated vectorization is configured on target index
        self._integrated_vectors = False
        try:
            from azure.search.documents.indexes import SearchIndexClient
            idx_client = SearchIndexClient(endpoint=self.endpoint, credential=AzureKeyCredential(self.admin_key))
            idx = idx_client.get_index(self.index_name)
            self._integrated_vectors = bool(getattr(idx, "vector_search", None) and getattr(idx.vector_search, "vectorizers", None))
        except Exception:
            self._integrated_vectors = False

    def index_remote_repository(
        self,
        owner: str,
        repo: str,
        ref: str = "main"
    ) -> Dict[str, Any]:
        """Index an entire remote repository.

        Args:
            owner: Repository owner
            repo: Repository name
            ref: Git ref (branch, tag, or commit SHA)

        Returns:
            Summary of indexing results
        """
        self.logger.info(f"🔄 Indexing remote repository: {owner}/{repo} (ref: {ref})")

        # Get all code files
        files = self.github_client.get_repository_files(
            owner, repo, ref=ref,
            extensions=[".py", ".js", ".ts"]
        )

        self.logger.info(f"📁 Found {len(files)} code files to index")

        documents = []
        indexed_count = 0
        error_count = 0

        for file_info in files:
            try:
                # Get file content
                content = self.github_client.get_file_content(
                    owner, repo, file_info["path"], ref
                )

                # Determine language and chunk
                if file_info["name"].endswith(".py"):
                    chunks = self.chunker.chunk_python_file(content, file_info["path"])
                    language = "python"
                elif file_info["name"].endswith((".js", ".ts")):
                    chunks = self.chunker.chunk_js_ts_file(content, file_info["path"])
                    language = "javascript" if file_info["name"].endswith(".js") else "typescript"
                else:
                    continue

                # Create documents for each chunk
                for i, chunk in enumerate(chunks):
                    doc_id = self._generate_document_id(
                        f"{owner}/{repo}", file_info["path"], chunk["chunk_type"], i
                    )

                    raw_content = chunk["content"]
                    # Enforce 32k char limit for safety
                    content = raw_content[:31997] + "..." if isinstance(raw_content, str) and len(raw_content) > 32000 else raw_content
                    doc = {
                        "id": doc_id,
                        "repository": f"{owner}/{repo}",
                        "file_path": file_info["path"],
                        "file_name": Path(file_info["path"]).name,
                        "language": language,
                        "last_modified": datetime.utcnow().isoformat() + "+00:00",
                        "content": content,
                        "semantic_context": chunk["semantic_context"],
                        "signature": chunk["signature"],
                        "imports": chunk["imports"],
                        "dependencies": chunk["dependencies"],
                        "chunk_type": chunk["chunk_type"],
                        "start_line": chunk["start_line"],
                        "end_line": chunk["end_line"],
                        "function_name": chunk.get("function_name"),
                        "class_name": chunk.get("class_name"),
                        "docstring": chunk.get("docstring", "")
                    }
                    if content is not raw_content:
                        doc["truncated"] = True

                    # Add vector embedding if enabled
                    if self.provider and not self._integrated_vectors:
                        embedding = self.provider.generate_code_embedding(
                            chunk["content"], chunk["semantic_context"]
                        )
                        if embedding:
                            doc["content_vector"] = embedding
                        else:
                            self.logger.warning(
                                f"Failed to generate embedding for {file_info['path']}"
                            )

                    # Safety check: Azure Search has 16MB payload limit per batch
                    # Keep individual documents well below this (use 1MB as safe limit)
                    doc_size = get_document_byte_size(doc)
                    if doc_size > 1024 * 1024:  # 1MB in bytes
                        # Truncate content to fit within size limit
                        content = doc.get("content", "")
                        if content:
                            # Estimate how much to truncate (rough approximation)
                            truncate_ratio = (1024 * 1024 * 0.8) / doc_size  # Target 80% of 1MB
                            truncate_chars = int(len(content) * truncate_ratio)
                            doc["content"] = content[:truncate_chars] + "\n... (truncated for size)"

                    documents.append(doc)

                    # Upload in batches
                    if len(documents) >= self.batch_size:
                        self._upload_documents(documents)
                        indexed_count += len(documents)
                        documents = []

            except Exception as e:
                self.logger.error(f"Error processing {file_info['path']}: {e}")
                error_count += 1

        # Upload remaining documents
        if documents:
            self._upload_documents(documents)
            indexed_count += len(documents)

        self.logger.info(f"✅ Indexed {indexed_count} chunks from {owner}/{repo}")

        return {
            "repository": f"{owner}/{repo}",
            "ref": ref,
            "files_processed": len(files),
            "chunks_indexed": indexed_count,
            "errors": error_count
        }

    def index_changed_files_remote(
        self,
        owner: str,
        repo: str,
        file_paths: List[str]
    ) -> Dict[str, Any]:
        """Index specific changed files from a remote repository.

        Args:
            owner: Repository owner
            repo: Repository name
            file_paths: List of file paths to index

        Returns:
            Summary of indexing results
        """
        self.logger.info(f"🔄 Indexing {len(file_paths)} changed files from {owner}/{repo}")

        documents = []
        indexed_count = 0
        error_count = 0

        for file_path in file_paths:
            # Skip non-code files
            if not any(file_path.endswith(ext) for ext in [".py", ".js", ".ts"]):
                continue

            try:
                # Get file content
                content = self.github_client.get_file_content(owner, repo, file_path)

                # Determine language and chunk
                if file_path.endswith(".py"):
                    chunks = self.chunker.chunk_python_file(content, file_path)
                    language = "python"
                elif file_path.endswith((".js", ".ts")):
                    chunks = self.chunker.chunk_js_ts_file(content, file_path)
                    language = "javascript" if file_path.endswith(".js") else "typescript"
                else:
                    continue

                # Create documents for each chunk
                for i, chunk in enumerate(chunks):
                    doc_id = self._generate_document_id(
                        f"{owner}/{repo}", file_path, chunk["chunk_type"], i
                    )

                    raw_content = chunk["content"]
                    # Enforce 32k char limit for safety
                    content = raw_content[:31997] + "..." if isinstance(raw_content, str) and len(raw_content) > 32000 else raw_content
                    doc = {
                        "id": doc_id,
                        "repository": f"{owner}/{repo}",
                        "file_path": file_path,
                        "file_name": Path(file_path).name,
                        "language": language,
                        "last_modified": datetime.utcnow().isoformat() + "+00:00",
                        "content": content,
                        "semantic_context": chunk["semantic_context"],
                        "signature": chunk["signature"],
                        "imports": chunk["imports"],
                        "dependencies": chunk["dependencies"],
                        "chunk_type": chunk["chunk_type"],
                        "start_line": chunk["start_line"],
                        "end_line": chunk["end_line"],
                        "function_name": chunk.get("function_name"),
                        "class_name": chunk.get("class_name"),
                        "docstring": chunk.get("docstring", "")
                    }
                    if content is not raw_content:
                        doc["truncated"] = True

                    # Add vector embedding if enabled
                    if self.provider and not self._integrated_vectors:
                        embedding = self.provider.generate_code_embedding(
                            chunk["content"], chunk["semantic_context"]
                        )
                        if embedding:
                            doc["content_vector"] = embedding

                    # Safety check: Azure Search has 16MB payload limit per batch
                    # Keep individual documents well below this (use 1MB as safe limit)
                    doc_size = get_document_byte_size(doc)
                    if doc_size > 1024 * 1024:  # 1MB in bytes
                        # Truncate content to fit within size limit
                        content = doc.get("content", "")
                        if content:
                            # Estimate how much to truncate (rough approximation)
                            truncate_ratio = (1024 * 1024 * 0.8) / doc_size  # Target 80% of 1MB
                            truncate_chars = int(len(content) * truncate_ratio)
                            doc["content"] = content[:truncate_chars] + "\n... (truncated for size)"

                    documents.append(doc)

            except Exception as e:
                self.logger.error(f"Error processing {file_path}: {e}")
                error_count += 1

        # Upload all documents
        if documents:
            self._upload_documents(documents)
            indexed_count = len(documents)

        self.logger.info(f"✅ Indexed {indexed_count} chunks from changed files")

        return {
            "repository": f"{owner}/{repo}",
            "files_processed": len(file_paths),
            "chunks_indexed": indexed_count,
            "errors": error_count
        }

    def get_changed_files_from_push(
        self,
        owner: str,
        repo: str,
        before_sha: str,
        after_sha: str
    ) -> List[str]:
        """Get list of changed files from a push event.

        Args:
            owner: Repository owner
            repo: Repository name
            before_sha: Base commit SHA
            after_sha: Head commit SHA

        Returns:
            List of changed file paths
        """
        changed_files = self.github_client.compare_commits(
            owner, repo, before_sha, after_sha
        )

        # Filter for code files
        return [
            f for f in changed_files
            if any(f.endswith(ext) for ext in [".py", ".js", ".ts"])
        ]

    def get_pull_request_files(
        self,
        owner: str,
        repo: str,
        pr_number: int
    ) -> List[str]:
        """Get list of files changed in a pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number

        Returns:
            List of changed file paths
        """
        pr_files = self.github_client.list_pull_request_files(
            owner, repo, pr_number
        )

        # Filter for code files
        return [
            f for f in pr_files
            if any(f.endswith(ext) for ext in [".py", ".js", ".ts"])
        ]

    def _generate_document_id(
        self,
        repo: str,
        file_path: str,
        chunk_type: str,
        index: int
    ) -> str:
        """Generate deterministic document ID.

        Args:
            repo: Repository identifier (owner/repo)
            file_path: Path to file
            chunk_type: Type of chunk (function, class, file)
            index: Chunk index within file

        Returns:
            MD5 hash as document ID
        """
        raw = f"{repo}:{file_path}:{chunk_type}:{index}".encode()
        return hashlib.md5(raw).hexdigest()

    def _upload_documents(self, documents: List[Dict[str, Any]]):
        """Upload documents to Azure Search.

        Args:
            documents: List of document dictionaries
        """
        if self.search_client is None:
            self.logger.warning("Search client is not initialized (network disabled); skipping document upload.")
            return

        try:
            # Use merge_or_upload if available, otherwise upload
            if hasattr(self.search_client, "merge_or_upload_documents"):
                result = self.search_client.merge_or_upload_documents(documents)
            else:
                result = self.search_client.upload_documents(documents)

            self.logger.debug(f"Uploaded {len(documents)} documents")
        except Exception as e:
            self.logger.error(f"Error uploading documents: {e}")
            raise
