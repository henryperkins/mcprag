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
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchAlias,
    SearchField,
    SearchFieldDataType,
    VectorSearch,
    VectorSearchProfile,
    VectorSearchAlgorithmConfiguration,
    HnswAlgorithmConfiguration,
    VectorSearchAlgorithmKind,
    VectorSearchAlgorithmMetric
)
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

    def create_codebase_index_schema(self, index_name: str = "codebase-mcp-sota") -> SearchIndex:
        """Create the index schema for codebase with vector search capabilities"""

        # Define vector search configuration
        vector_search = VectorSearch(
            profiles=[
                VectorSearchProfile(
                    name="vector-profile",
                    algorithm_configuration_name="vector-config"
                )
            ],
            algorithms=[
                HnswAlgorithmConfiguration(
                    name="vector-config",
                    kind=VectorSearchAlgorithmKind.HNSW,
                    parameters={
                        "m": 4,
                        "efConstruction": 400,
                        "efSearch": 500,
                        "metric": VectorSearchAlgorithmMetric.COSINE
                    }
                )
            ]
        )

        # Define all fields based on indexer field mappings
        fields = [
            # Key field
            SearchField(
                name="id",
                type=SearchFieldDataType.String,
                key=True,
                searchable=False,
                filterable=True
            ),

            # Basic file metadata
            SearchField(
                name="file_path",
                type=SearchFieldDataType.String,
                searchable=True,
                filterable=True,
                facetable=True
            ),
            SearchField(
                name="title",
                type=SearchFieldDataType.String,
                searchable=True,
                filterable=True
            ),
            SearchField(
                name="last_modified",
                type=SearchFieldDataType.DateTimeOffset,
                filterable=True,
                sortable=True
            ),
            SearchField(
                name="size_bytes",
                type=SearchFieldDataType.Int64,
                filterable=True,
                sortable=True
            ),
            SearchField(
                name="file_extension",
                type=SearchFieldDataType.String,
                filterable=True,
                facetable=True
            ),
            SearchField(
                name="content",
                type=SearchFieldDataType.String,
                searchable=True
            ),

            # Code content and vector
            SearchField(
                name="code_content",
                type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                searchable=True
            ),
            SearchField(
                name="content_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=3072,
                vector_search_profile_name="vector-profile"
            ),

            # Language and keywords
            SearchField(
                name="language",
                type=SearchFieldDataType.String,
                filterable=True,
                facetable=True
            ),
            SearchField(
                name="intent_keywords",
                type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                searchable=True,
                filterable=True
            ),

            # Code analysis fields
            SearchField(
                name="function_name",
                type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                searchable=True,
                filterable=True
            ),
            SearchField(
                name="class_name",
                type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                searchable=True,
                filterable=True
            ),
            SearchField(
                name="imports",
                type=SearchFieldDataType.String,
                searchable=True
            ),
            SearchField(
                name="dependencies",
                type=SearchFieldDataType.String,
                searchable=True
            ),
            SearchField(
                name="docstring",
                type=SearchFieldDataType.String,
                searchable=True
            ),
            SearchField(
                name="signature",
                type=SearchFieldDataType.String,
                searchable=True
            ),
            SearchField(
                name="comments",
                type=SearchFieldDataType.String,
                searchable=True
            ),
            SearchField(
                name="framework",
                type=SearchFieldDataType.String,
                filterable=True,
                facetable=True
            ),
            SearchField(
                name="complexity_score",
                type=SearchFieldDataType.Double,
                filterable=True,
                sortable=True
            ),
            SearchField(
                name="detected_patterns",
                type=SearchFieldDataType.String,
                searchable=True
            ),

            # Git metadata fields
            SearchField(
                name="git_branch",
                type=SearchFieldDataType.String,
                filterable=True,
                facetable=True
            ),
            SearchField(
                name="git_commit",
                type=SearchFieldDataType.String,
                filterable=True
            ),
            SearchField(
                name="git_authors",
                type=SearchFieldDataType.String,
                filterable=True,
                facetable=True
            ),
            SearchField(
                name="git_commit_count",
                type=SearchFieldDataType.Int32,
                filterable=True,
                sortable=True
            ),
            SearchField(
                name="git_last_modified",
                type=SearchFieldDataType.DateTimeOffset,
                filterable=True,
                sortable=True
            )
        ]

        return SearchIndex(
            name=index_name,
            fields=fields,
            vector_search=vector_search
        )

    @with_retry(op_name="index.create_codebase")
    async def create_codebase_index(self, index_name: str = "codebase-mcp-sota") -> bool:
        """Create the complete codebase index with vector search"""
        try:
            index_schema = self.create_codebase_index_schema(index_name)
            await self._run_in_executor(self.client.create_or_update_index, index_schema)
            return True
        except Exception as e:
            print(f"Error creating codebase index: {e}")
            return False

    async def close(self):
        """Close the underlying HTTP session pool."""
        await self._run_in_executor(self.client.close)
