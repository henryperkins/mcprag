"""Index management operations for Azure AI Search"""

from typing import Dict, Any, Optional
import asyncio

from azure.core.credentials import AzureKeyCredential
# NOTE: The Azure SDK for Python is synchronous. To avoid blocking an
# asyncio event-loop we execute SDK calls in a thread-pool.  This file keeps
# an async public surface so it can be awaited by the rest of the codebase
# without change, but internally each network call is delegated to
# `asyncio.get_running_loop().run_in_executor`.

from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import SearchIndex, SearchAlias
from ..utils.error_handler import with_retry

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

    async def _run_in_executor(self, func, *args, **kwargs):
        """Helper to off-load a blocking SDK call to a thread."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    @with_retry(op_name="index.create_or_update")
    async def create_or_update_index(self, index: SearchIndex) -> bool:
        """Create or update an index (thread-safe for asyncio)."""
        try:
            await self._run_in_executor(self.client.create_or_update_index, index)
            return True
        except Exception:
            return False

    @with_retry(op_name="index.delete")
    async def delete_index(self, index_name: str) -> bool:
        """Delete an index"""
        try:
            await self._run_in_executor(self.client.delete_index, index_name)
            return True
        except Exception:
            return False

    @with_retry(op_name="index.get_stats")
    async def get_index_statistics(self, index_name: str) -> Dict[str, Any]:
        """Get index statistics"""
        try:
            stats = await self._run_in_executor(
                self.client.get_index_statistics, index_name
            )
            return {
                "document_count": getattr(stats, "document_count", None),
                "storage_size": getattr(stats, "storage_size", None),
            }
        except Exception as e:
            return {"error": str(e)}

    @with_retry(op_name="index.optimize")
    async def optimize_index(self, index_name: str) -> bool:
        """
        Optimize index for better performance (placeholder: reapply index)
        """
        try:
            index = await self._run_in_executor(self.client.get_index, index_name)
            await self._run_in_executor(self.client.create_or_update_index, index)
            return True
        except Exception:
            return False

    @with_retry(op_name="index.swap_alias")
    async def swap_alias(self, alias: str, new_index: str) -> None:
        """Atomically repoint alias to a new index"""
        alias_obj = SearchAlias(name=alias, indexes=[new_index])
        await self._run_in_executor(self.client.create_or_update_alias, alias_obj)

    async def close(self):
        """Close the underlying HTTP session pool."""
        await self._run_in_executor(self.client.close)