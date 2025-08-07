"""Simple operations for Azure AI Search automation."""

from typing import Dict, Any, List, Optional
import logging
from .client import AzureSearchClient

logger = logging.getLogger(__name__)


class SearchOperations:
    """Simple operations for Azure AI Search automation."""
    
    def __init__(self, client: AzureSearchClient):
        """Initialize operations with a REST client."""
        self.client = client
    
    # ========== Index Operations ==========
    
    async def create_index(self, index_definition: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update an index.
        
        Args:
            index_definition: Complete index definition including name, fields, etc.
            
        Returns:
            Created/updated index definition
        """
        name = index_definition["name"]
        logger.info(f"Creating/updating index: {name}")
        return await self.client.request("PUT", f"/indexes/{name}", json=index_definition)
    
    async def delete_index(self, name: str) -> None:
        """Delete an index.
        
        Args:
            name: Index name to delete
        """
        logger.info(f"Deleting index: {name}")
        await self.client.request("DELETE", f"/indexes/{name}")
    
    async def get_index(self, name: str) -> Dict[str, Any]:
        """Get index definition.
        
        Args:
            name: Index name
            
        Returns:
            Index definition
        """
        return await self.client.request("GET", f"/indexes/{name}")
    
    async def list_indexes(self, select: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """List all indexes.
        
        Args:
            select: Optional list of fields to return
            
        Returns:
            List of index definitions
        """
        params = {}
        if select:
            params["$select"] = ",".join(select)
            
        result = await self.client.request("GET", "/indexes", params=params)
        return result.get("value", [])
    
    async def get_index_stats(self, name: str) -> Dict[str, Any]:
        """Get index statistics.
        
        Args:
            name: Index name
            
        Returns:
            Index statistics including document count and storage size
        """
        return await self.client.request("GET", f"/indexes/{name}/stats")
    
    async def analyze_text(self, index_name: str, analyzer: str, text: str) -> Dict[str, Any]:
        """Analyze text using an index analyzer.
        
        Args:
            index_name: Index name
            analyzer: Analyzer name
            text: Text to analyze
            
        Returns:
            Tokens produced by the analyzer
        """
        body = {
            "analyzer": analyzer,
            "text": text
        }
        return await self.client.request("POST", f"/indexes/{index_name}/analyze", json=body)
    
    # ========== Document Operations ==========
    
    async def upload_documents(
        self, 
        index_name: str, 
        documents: List[Dict[str, Any]],
        merge: bool = False
    ) -> Dict[str, Any]:
        """Upload documents to an index.
        
        Args:
            index_name: Target index name
            documents: List of documents to upload
            merge: If True, merge with existing documents; otherwise upload (replace)
            
        Returns:
            Upload result with status for each document
        """
        action = "merge" if merge else "upload"
        batch = {
            "value": [
                {"@search.action": action, **doc} 
                for doc in documents
            ]
        }
        return await self.client.request("POST", f"/indexes/{index_name}/docs/index", json=batch)
    
    async def delete_documents(self, index_name: str, keys: List[str]) -> Dict[str, Any]:
        """Delete documents by key.
        
        Args:
            index_name: Target index name
            keys: List of document keys to delete
            
        Returns:
            Delete result with status for each document
        """
        batch = {
            "value": [
                {"@search.action": "delete", "id": key} 
                for key in keys
            ]
        }
        return await self.client.request("POST", f"/indexes/{index_name}/docs/index", json=batch)
    
    async def get_document(self, index_name: str, key: str, select: Optional[List[str]] = None) -> Dict[str, Any]:
        """Get a single document by key.
        
        Args:
            index_name: Index name
            key: Document key
            select: Optional list of fields to return
            
        Returns:
            Document data
        """
        params = {}
        if select:
            params["$select"] = ",".join(select)
            
        return await self.client.request("GET", f"/indexes/{index_name}/docs/{key}", params=params)
    
    async def count_documents(self, index_name: str) -> int:
        """Get document count for an index.
        
        Args:
            index_name: Index name
            
        Returns:
            Document count
        """
        result = await self.client.request("GET", f"/indexes/{index_name}/docs/$count")
        # The count endpoint returns a plain integer, not a dictionary
        if isinstance(result, int):
            return result
        return result.get("@odata.count", 0)
    
    async def search(
        self, 
        index_name: str, 
        query: str = "*",
        **options
    ) -> Dict[str, Any]:
        """Search documents.
        
        Args:
            index_name: Index to search
            query: Search query (default: * for all documents)
            **options: Additional search options (filter, select, orderby, top, skip, etc.)
            
        Returns:
            Search results
        """
        body = {"search": query, **options}
        return await self.client.request("POST", f"/indexes/{index_name}/docs/search", json=body)
    
    # ========== Indexer Operations ==========
    
    async def create_indexer(self, indexer_definition: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update an indexer.
        
        Args:
            indexer_definition: Complete indexer definition
            
        Returns:
            Created/updated indexer definition
        """
        name = indexer_definition["name"]
        logger.info(f"Creating/updating indexer: {name}")
        return await self.client.request("PUT", f"/indexers/{name}", json=indexer_definition)
    
    async def delete_indexer(self, name: str) -> None:
        """Delete an indexer.
        
        Args:
            name: Indexer name to delete
        """
        logger.info(f"Deleting indexer: {name}")
        await self.client.request("DELETE", f"/indexers/{name}")
    
    async def get_indexer(self, name: str) -> Dict[str, Any]:
        """Get indexer definition.
        
        Args:
            name: Indexer name
            
        Returns:
            Indexer definition
        """
        return await self.client.request("GET", f"/indexers/{name}")
    
    async def list_indexers(self, select: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """List all indexers.
        
        Args:
            select: Optional list of fields to return
            
        Returns:
            List of indexer definitions
        """
        params = {}
        if select:
            params["$select"] = ",".join(select)
            
        result = await self.client.request("GET", "/indexers", params=params)
        return result.get("value", [])
    
    async def run_indexer(self, name: str, wait: bool = False, poll_interval: float = 2.0, timeout: float = 300.0) -> Dict[str, Any]:
        """Run an indexer on demand.
        
        Args:
            name: Indexer name to run
            wait: Whether to wait for completion
            poll_interval: Seconds between status checks when waiting
            timeout: Maximum seconds to wait for completion
            
        Returns:
            Status dictionary with run result
        """
        logger.info(f"Running indexer: {name}")
        await self.client.request("POST", f"/indexers/{name}/run")
        if not wait:
            return {"started": True}
        import asyncio, time
        start = time.time()
        while time.time() - start < timeout:
            status = await self.get_indexer_status(name)
            last = (status.get("lastResult") or {}).get("status") or (status.get("executionStatus") or "")
            if str(last).lower() in {"success", "transientfailure", "error"}:
                return {"completed": True, "status": status}
            await asyncio.sleep(poll_interval)
        return {"timeout": True}
    
    async def reset_indexer(self, name: str) -> None:
        """Reset an indexer.
        
        Args:
            name: Indexer name to reset
        """
        logger.info(f"Resetting indexer: {name}")
        await self.client.request("POST", f"/indexers/{name}/reset")
    
    async def get_indexer_status(self, name: str) -> Dict[str, Any]:
        """Get indexer execution status.
        
        Args:
            name: Indexer name
            
        Returns:
            Indexer status including execution history
        """
        return await self.client.request("GET", f"/indexers/{name}/status")
    
    # ========== Data Source Operations ==========
    
    async def create_datasource(self, datasource_definition: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update a data source.
        
        Args:
            datasource_definition: Complete data source definition
            
        Returns:
            Created/updated data source definition
        """
        name = datasource_definition["name"]
        logger.info(f"Creating/updating data source: {name}")
        return await self.client.request("PUT", f"/datasources/{name}", json=datasource_definition)
    
    async def delete_datasource(self, name: str) -> None:
        """Delete a data source.
        
        Args:
            name: Data source name to delete
        """
        logger.info(f"Deleting data source: {name}")
        await self.client.request("DELETE", f"/datasources/{name}")
    
    async def get_datasource(self, name: str) -> Dict[str, Any]:
        """Get data source definition.
        
        Args:
            name: Data source name
            
        Returns:
            Data source definition
        """
        return await self.client.request("GET", f"/datasources/{name}")
    
    async def list_datasources(self, select: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """List all data sources.
        
        Args:
            select: Optional list of fields to return
            
        Returns:
            List of data source definitions
        """
        params = {}
        if select:
            params["$select"] = ",".join(select)
            
        result = await self.client.request("GET", "/datasources", params=params)
        return result.get("value", [])
    
    # ========== Skillset Operations ==========
    
    async def create_skillset(self, skillset_definition: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update a skillset.
        
        Args:
            skillset_definition: Complete skillset definition
            
        Returns:
            Created/updated skillset definition
        """
        name = skillset_definition["name"]
        logger.info(f"Creating/updating skillset: {name}")
        return await self.client.request("PUT", f"/skillsets/{name}", json=skillset_definition)
    
    async def delete_skillset(self, name: str) -> None:
        """Delete a skillset.
        
        Args:
            name: Skillset name to delete
        """
        logger.info(f"Deleting skillset: {name}")
        await self.client.request("DELETE", f"/skillsets/{name}")
    
    async def get_skillset(self, name: str) -> Dict[str, Any]:
        """Get skillset definition.
        
        Args:
            name: Skillset name
            
        Returns:
            Skillset definition
        """
        return await self.client.request("GET", f"/skillsets/{name}")
    
    async def list_skillsets(self, select: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """List all skillsets.
        
        Args:
            select: Optional list of fields to return
            
        Returns:
            List of skillset definitions
        """
        params = {}
        if select:
            params["$select"] = ",".join(select)
            
        result = await self.client.request("GET", "/skillsets", params=params)
        return result.get("value", [])
    
    async def reset_skills(self, skillset_name: str, skill_names: Optional[List[str]] = None) -> None:
        """Reset specific skills in a skillset.
        
        Args:
            skillset_name: Skillset name
            skill_names: Optional list of skill names to reset (resets all if not specified)
        """
        logger.info(f"Resetting skills in skillset: {skillset_name}")
        body = {}
        if skill_names:
            body["skillNames"] = skill_names
            
        await self.client.request("POST", f"/skillsets/{skillset_name}/resetskills", json=body)
    
    # ========== Service Operations ==========
    
    async def get_service_statistics(self) -> Dict[str, Any]:
        """Get service-level statistics.
        
        Returns:
            Service statistics including counters and limits
        """
        return await self.client.request("GET", "/servicestats")