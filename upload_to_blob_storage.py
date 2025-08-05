#!/usr/bin/env python3
"""
Upload local repository files to Azure Blob Storage using SAS token.
This prepares files for integrated vectorization.
"""

import os
import asyncio
import logging
from pathlib import Path
from typing import List, Set
from datetime import datetime
from azure.storage.blob import BlobServiceClient, ContainerClient
from azure.core.exceptions import ResourceExistsError
import fnmatch

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default file patterns to include
DEFAULT_INCLUDE_PATTERNS = [
    "*.py", "*.js", "*.ts", "*.jsx", "*.tsx", "*.java", "*.cs", "*.cpp", "*.c", "*.h",
    "*.go", "*.rs", "*.rb", "*.php", "*.swift", "*.kt", "*.scala", "*.r", "*.m",
    "*.md", "*.txt", "*.json", "*.xml", "*.yaml", "*.yml", "*.toml", "*.ini",
    "*.sh", "*.bash", "*.ps1", "*.dockerfile", "Dockerfile", "*.sql"
]

# Patterns to exclude
EXCLUDE_PATTERNS = [
    "*.pyc", "__pycache__/*", "*.pyo", "*.pyd", ".git/*", ".svn/*", 
    "node_modules/*", "venv/*", ".venv/*", "env/*", ".env/*",
    "*.log", "*.tmp", "*.temp", "*.cache", ".DS_Store", "Thumbs.db",
    "*.exe", "*.dll", "*.so", "*.dylib", "*.bin", "*.obj", "*.o",
    "dist/*", "build/*", "target/*", "out/*", ".idea/*", ".vscode/*",
    "*.lock", "package-lock.json", "yarn.lock", "poetry.lock"
]


class BlobUploader:
    """Upload files to Azure Blob Storage."""
    
    def __init__(self, sas_url: str):
        """Initialize with SAS URL."""
        self.container_client = ContainerClient.from_container_url(sas_url)
        self.uploaded_count = 0
        self.skipped_count = 0
        self.error_count = 0
    
    def should_include_file(self, file_path: Path, include_patterns: List[str], exclude_patterns: List[str]) -> bool:
        """Check if file should be included based on patterns."""
        file_str = str(file_path)
        
        # Check exclude patterns first
        for pattern in exclude_patterns:
            if fnmatch.fnmatch(file_str, pattern) or fnmatch.fnmatch(file_path.name, pattern):
                return False
        
        # Check include patterns
        for pattern in include_patterns:
            if fnmatch.fnmatch(file_str, pattern) or fnmatch.fnmatch(file_path.name, pattern):
                return True
        
        return False
    
    def get_blob_name(self, file_path: Path, repo_name: str, base_path: Path) -> str:
        """Generate blob name with repository structure."""
        # Get relative path from base
        try:
            relative_path = file_path.relative_to(base_path)
        except ValueError:
            relative_path = file_path
        
        # Create blob name: repo_name/relative_path
        blob_name = f"{repo_name}/{relative_path}".replace("\\", "/")
        return blob_name
    
    async def upload_file(self, file_path: Path, blob_name: str) -> bool:
        """Upload a single file to blob storage."""
        try:
            # Check file size
            file_size = file_path.stat().st_size
            if file_size > 100 * 1024 * 1024:  # 100MB limit
                logger.warning(f"Skipping large file (>100MB): {file_path}")
                self.skipped_count += 1
                return False
            
            # Read file content
            try:
                with open(file_path, 'rb') as f:
                    data = f.read()
            except Exception as e:
                logger.error(f"Error reading file {file_path}: {e}")
                self.error_count += 1
                return False
            
            # Upload to blob
            blob_client = self.container_client.get_blob_client(blob_name)
            
            # Set content type based on extension
            content_type = "text/plain"
            if file_path.suffix == ".json":
                content_type = "application/json"
            elif file_path.suffix in [".py", ".js", ".ts", ".java", ".cs", ".cpp", ".go", ".rs"]:
                content_type = "text/plain; charset=utf-8"
            
            blob_client.upload_blob(
                data, 
                overwrite=True,
                content_settings={"content_type": content_type}
            )
            
            self.uploaded_count += 1
            logger.info(f"Uploaded: {blob_name} ({file_size:,} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"Error uploading {file_path}: {e}")
            self.error_count += 1
            return False
    
    async def upload_repository(
        self, 
        repo_path: str, 
        repo_name: str,
        include_patterns: List[str] = None,
        exclude_patterns: List[str] = None
    ):
        """Upload an entire repository to blob storage."""
        base_path = Path(repo_path).resolve()
        
        if not base_path.exists():
            raise ValueError(f"Repository path does not exist: {repo_path}")
        
        include_patterns = include_patterns or DEFAULT_INCLUDE_PATTERNS
        exclude_patterns = exclude_patterns or EXCLUDE_PATTERNS
        
        logger.info(f"Scanning repository: {base_path}")
        logger.info(f"Repository name: {repo_name}")
        
        # Collect files to upload
        files_to_upload = []
        for file_path in base_path.rglob("*"):
            if file_path.is_file() and self.should_include_file(file_path, include_patterns, exclude_patterns):
                blob_name = self.get_blob_name(file_path, repo_name, base_path)
                files_to_upload.append((file_path, blob_name))
        
        logger.info(f"Found {len(files_to_upload)} files to upload")
        
        # Upload files
        for i, (file_path, blob_name) in enumerate(files_to_upload):
            logger.info(f"[{i+1}/{len(files_to_upload)}] Uploading {file_path.name}...")
            await self.upload_file(file_path, blob_name)
            
            # Rate limiting
            if i % 10 == 0:
                await asyncio.sleep(0.5)
        
        logger.info("\n" + "="*60)
        logger.info("UPLOAD COMPLETE")
        logger.info("="*60)
        logger.info(f"  Uploaded: {self.uploaded_count}")
        logger.info(f"  Skipped: {self.skipped_count}")
        logger.info(f"  Errors: {self.error_count}")
        logger.info(f"  Total: {len(files_to_upload)}")


async def main():
    """Main function to upload repository to blob storage."""
    
    # Storage configuration
    storage_account = "codebasestorage2025"
    container_name = "code-repositories"
    sas_token = "st=2025-08-04T15:15:24Z&se=2025-08-09T23:30:24Z&si=aisearch&sv=2024-11-04&sr=c&sig=lthGhNUB9BVCI4MVrcit2KIn36%2FzIOIbwmlzGaCCI8k%3D"
    
    # Construct SAS URL
    sas_url = f"https://{storage_account}.blob.core.windows.net/{container_name}?{sas_token}"
    
    print("\n" + "="*60)
    print("UPLOAD REPOSITORY TO BLOB STORAGE")
    print("="*60)
    print(f"\nStorage Account: {storage_account}")
    print(f"Container: {container_name}")
    print("SAS Token: Valid until 2025-08-09")
    
    # Get repository path
    repo_path = input("\nEnter repository path (default: current directory): ").strip() or "."
    repo_name = input("Enter repository name (default: mcprag): ").strip() or "mcprag"
    
    # Custom patterns
    print("\nDefault file patterns will be used.")
    custom = input("Do you want to specify custom patterns? (y/N): ").strip().lower()
    
    include_patterns = None
    exclude_patterns = None
    
    if custom == 'y':
        print("\nEnter include patterns (comma-separated, e.g., *.py,*.js):")
        include_input = input("> ").strip()
        if include_input:
            include_patterns = [p.strip() for p in include_input.split(",")]
        
        print("\nEnter additional exclude patterns (comma-separated):")
        exclude_input = input("> ").strip()
        if exclude_input:
            exclude_patterns = EXCLUDE_PATTERNS + [p.strip() for p in exclude_input.split(",")]
    
    print("\n" + "="*60)
    print("STARTING UPLOAD")
    print("="*60)
    
    # Create uploader and upload
    uploader = BlobUploader(sas_url)
    
    try:
        await uploader.upload_repository(
            repo_path=repo_path,
            repo_name=repo_name,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns
        )
        
        print("\n" + "="*60)
        print("NEXT STEPS")
        print("="*60)
        print("\n1. Your files are now in blob storage")
        print("2. Run the integrated vectorization setup if not already done:")
        print("   python setup_with_sas_token.py")
        print("3. The indexer will process these files and generate embeddings")
        print("4. Monitor indexer status:")
        print("   python -m enhanced_rag.azure_integration.cli indexer-status --name mcp-codebase-indexer")
        
    except Exception as e:
        print(f"\nERROR: {e}")
        logger.exception("Upload failed")


if __name__ == "__main__":
    asyncio.run(main())