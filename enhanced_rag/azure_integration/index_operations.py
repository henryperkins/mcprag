"""Index management operations for Azure AI Search"""

from typing import Dict, Any, Optional

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import SearchIndex

from enhanced_rag.core.config import get_config


class IndexOperations:
    """Manage index operations like create, update, delete"""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        admin_key: Optional[str] = None
    ):
        cfg = get_config().azure
        self.client = SearchIndexClient(
            endpoint=endpoint or cfg.endpoint,
            credential=AzureKeyCredential(admin_key or cfg.admin_key),
        )

    async def create_or_update_index(self, index: SearchIndex) -> bool:
        """Create or update an index"""
        try:
            self.client.create_or_update_index(index)
            return True
        except Exception:
            return False

    async def delete_index(self, index_name: str) -> bool:
        """Delete an index"""
        try:
            self.client.delete_index(index_name)
            return True
        except Exception:
            return False

    async def get_index_statistics(self, index_name: str) -> Dict[str, Any]:
        """Get index statistics"""
        try:
            stats = self.client.get_index_statistics(index_name)
            return {
                "document_count": getattr(stats, "document_count", None),
                "storage_size": getattr(stats, "storage_size", None),
            }
        except Exception as e:
            return {"error": str(e)}

    async def optimize_index(self, index_name: str) -> bool:
        """
        Optimize index for better performance (placeholder: reapply index)
        """
        try:
            index = self.client.get_index(index_name)
            self.client.create_or_update_index(index)
            return True
        except Exception:
            return False