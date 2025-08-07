"""Azure Search Client Pool for connection reuse."""
import os
import threading
from typing import Dict, Optional, Tuple
from weakref import WeakValueDictionary
from enhanced_rag.azure_integration.rest.client import AzureSearchClient
import logging

logger = logging.getLogger(__name__)


class AzureSearchClientPool:
    """Singleton pool for managing AzureSearchClient instances."""
    
    _instance = None
    _lock = threading.Lock()
    _clients: WeakValueDictionary = WeakValueDictionary()
    _pool_size = int(os.getenv("ACS_CONN_POOL", "100"))
    
    def __new__(cls):
        """Ensure singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the pool (only once)."""
        if not hasattr(self, '_initialized'):
            self._initialized = True
            logger.info(f"Azure Search Client Pool initialized with max size: {self._pool_size}")
    
    @classmethod
    def get_client(cls, endpoint: str, admin_key: str, index_name: str = "main") -> AzureSearchClient:
        """
        Get or create a client for the given credentials.
        
        Args:
            endpoint: Azure Search endpoint URL
            admin_key: Admin API key
            index_name: Index name (default: "main")
            
        Returns:
            AzureSearchClient instance (shared)
        """
        instance = cls()
        
        # Create a unique key for this client configuration
        client_key = (endpoint, admin_key, index_name)
        
        with cls._lock:
            # Check if we have an existing client
            if client_key in cls._clients:
                client = cls._clients[client_key]
                if client is not None:
                    logger.debug(f"Reusing existing client for {endpoint}/{index_name}")
                    return client
            
            # Check pool size limit
            if len(cls._clients) >= cls._pool_size:
                # Remove oldest entries (WeakValueDictionary will auto-cleanup)
                logger.warning(f"Client pool at capacity ({cls._pool_size}), relying on GC")
            
            # Create new client
            logger.info(f"Creating new client for {endpoint}/{index_name}")
            client = AzureSearchClient(
                endpoint=endpoint,
                admin_key=admin_key,
                index_name=index_name
            )
            cls._clients[client_key] = client
            return client
    
    @classmethod
    def clear_pool(cls):
        """Clear all cached clients."""
        with cls._lock:
            cls._clients.clear()
            logger.info("Client pool cleared")
    
    @classmethod
    def pool_stats(cls) -> Dict[str, int]:
        """Get pool statistics."""
        with cls._lock:
            return {
                "active_clients": len(cls._clients),
                "max_pool_size": cls._pool_size
            }


# Convenience function for backward compatibility
def get_azure_search_client(endpoint: str, admin_key: str, index_name: str = "main") -> AzureSearchClient:
    """Get a pooled Azure Search client."""
    return AzureSearchClientPool.get_client(endpoint, admin_key, index_name)