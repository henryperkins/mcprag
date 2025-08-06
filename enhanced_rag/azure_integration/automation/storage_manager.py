"""Azure Blob Storage management for indexer data sources."""

import os
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

try:
    from azure.storage.blob import BlobServiceClient, ContainerClient
    from azure.identity import DefaultAzureCredential
    from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
except ImportError:
    BlobServiceClient = None
    ContainerClient = None
    DefaultAzureCredential = None
    ResourceExistsError = Exception
    ResourceNotFoundError = Exception

logger = logging.getLogger(__name__)


class StorageManager:
    """Manages Azure Blob Storage operations for indexer data sources."""
    
    def __init__(self, storage_account_name: Optional[str] = None, connection_string: Optional[str] = None):
        """Initialize storage manager."""
        if not BlobServiceClient:
            raise ImportError("azure-storage-blob package required")
        
        self.storage_account_name = storage_account_name or os.getenv('AZURE_STORAGE_ACCOUNT_NAME')
        self.connection_string = connection_string or os.getenv('AZURE_STORAGE_CONNECTION_STRING')
        
        # Initialize blob service client
        if self.connection_string:
            logger.info("Using connection string authentication")
            self.blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)
        elif self.storage_account_name:
            logger.info("Using managed identity authentication")
            account_url = f"https://{self.storage_account_name}.blob.core.windows.net"
            credential = DefaultAzureCredential()
            self.blob_service_client = BlobServiceClient(account_url, credential=credential)
        else:
            raise ValueError("Either storage_account_name or connection_string must be provided")
    
    def ensure_container(self, container_name: str) -> Dict[str, Any]:
        """Ensure container exists, create if it doesn't."""
        try:
            container_client = self.blob_service_client.get_container_client(container_name)
            
            try:
                properties = container_client.get_container_properties()
                return {"status": "exists", "container_name": container_name, "created": False}
            except ResourceNotFoundError:
                container_client.create_container()
                return {"status": "created", "container_name": container_name, "created": True}
                
        except Exception as e:
            return {"status": "error", "container_name": container_name, "error": str(e)}
    
    def upload_repository_files(self, repo_path: str, container_name: str, blob_prefix: str = "") -> Dict[str, Any]:
        """Upload repository files to blob storage."""
        file_patterns = [
            "*.py", "*.js", "*.ts", "*.jsx", "*.tsx", "*.java", "*.c", "*.cpp", 
            "*.h", "*.hpp", "*.cs", "*.go", "*.rs", "*.php", "*.rb", "*.swift", 
            "*.kt", "*.scala", "*.r", "*.sql", "*.html", "*.css", "*.json", 
            "*.xml", "*.yaml", "*.yml", "*.md", "*.txt", "*.sh", "*.dockerfile"
        ]
        
        try:
            container_client = self.blob_service_client.get_container_client(container_name)
            repo_path = Path(repo_path)
            
            uploaded_files = []
            failed_files = []
            total_size = 0
            
            # Find files matching patterns
            files_to_upload = []
            for pattern in file_patterns:
                files_to_upload.extend(repo_path.rglob(pattern))
            
            for file_path in files_to_upload:
                try:
                    relative_path = file_path.relative_to(repo_path)
                    blob_name = f"{blob_prefix}{relative_path}".replace("\\", "/")
                    
                    with open(file_path, 'rb') as file_data:
                        content = file_data.read()
                        file_size = len(content)
                    
                    blob_client = container_client.get_blob_client(blob_name)
                    blob_client.upload_blob(content, overwrite=True)
                    
                    uploaded_files.append({"local_path": str(file_path), "blob_name": blob_name, "size": file_size})
                    total_size += file_size
                
                except Exception as e:
                    failed_files.append({"local_path": str(file_path), "error": str(e)})
            
            return {
                "status": "completed",
                "container_name": container_name,
                "uploaded_count": len(uploaded_files),
                "failed_count": len(failed_files),
                "total_size_bytes": total_size
            }
            
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information for indexer data source."""
        if self.connection_string:
            return {"connection_type": "connection_string", "connection_string": self.connection_string}
        elif self.storage_account_name:
            return {
                "connection_type": "managed_identity",
                "storage_account_name": self.storage_account_name,
                "account_url": f"https://{self.storage_account_name}.blob.core.windows.net"
            }
        else:
            return {"connection_type": "none", "error": "No connection method configured"}
EOF < /dev/null
