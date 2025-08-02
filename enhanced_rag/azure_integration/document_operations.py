"""Document operations for Azure AI Search"""

from typing import Dict, Any, List, Optional

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

from enhanced_rag.core.config import get_config


class DocumentOperations:
    """Handle document upload, update, and deletion"""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        admin_key: Optional[str] = None,
    ):
        cfg = get_config().azure
        self.endpoint = endpoint or cfg.endpoint
        self.credential = AzureKeyCredential(admin_key or cfg.admin_key)

    def _client(self, index_name: str) -> SearchClient:
        return SearchClient(
            endpoint=self.endpoint,
            index_name=index_name,
            credential=self.credential,
        )

    async def upload_documents(
        self, index_name: str, documents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Upload documents to index
        
        Note: If the index has integrated vectorization configured,
        Azure AI Search will automatically generate embeddings for
        text fields. No client-side vectorization is needed.
        """
        try:
            client = self._client(index_name)
            if hasattr(client, "merge_or_upload_documents"):
                result = client.merge_or_upload_documents(documents)
            else:
                result = client.upload_documents(documents)
            return {"status": "ok", "result": [r.succeeded for r in result]}
        except Exception as e:
            return {"error": str(e)}

    async def update_documents(
        self, index_name: str, documents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Update existing documents"""
        try:
            client = self._client(index_name)
            result = client.merge_or_upload_documents(documents)
            return {
                "status": "ok",
                "result": [r.succeeded for r in result],
            }
        except Exception as e:
            return {"error": str(e)}

    async def delete_documents(
        self, index_name: str, document_ids: List[str]
    ) -> Dict[str, Any]:
        """Delete documents from index"""
        try:
            docs = [{"id": did} for did in document_ids]
            result = self._client(index_name).delete_documents(docs)
            return {"status": "ok", "result": [r.succeeded for r in result]}
        except Exception as e:
            return {"error": str(e)}

    async def batch_process_documents(
        self, index_name: str, operations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Batch process multiple document operations.

        Note: For simplicity this method treats 'operations' as full
        documents to upload. If you need fine-grained action control,
        switch to SearchClient.upload_documents/merge_or_upload_documents/
        delete_documents with explicit actions payload.
        """
        try:
            result = self._client(index_name).upload_documents(operations)
            return {"status": "ok", "result": [r.succeeded for r in result]}
        except Exception as e:
            return {"error": str(e)}
