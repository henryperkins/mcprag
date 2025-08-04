"""Simple REST client for Azure AI Search automation."""

import httpx
from typing import Dict, Any, Optional
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class AzureSearchClient:
    """Simple REST client for Azure AI Search automation."""
    
    def __init__(
        self, 
        endpoint: str, 
        api_key: str, 
        api_version: str = "2025-05-01-preview",
        timeout: float = 30.0
    ):
        """Initialize the Azure Search REST client.
        
        Args:
            endpoint: Azure Search service endpoint
            api_key: Admin API key for authentication
            api_version: API version to use (default: 2025-05-01-preview)
            timeout: Request timeout in seconds
        """
        self.endpoint = endpoint.rstrip('/')
        self.api_key = api_key
        self.api_version = api_version
        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers={
                "api-key": api_key,
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
        )
    
    @retry(
        stop=stop_after_attempt(3), 
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True
    )
    async def request(
        self, 
        method: str, 
        path: str, 
        **kwargs
    ) -> Dict[str, Any]:
        """Make a REST API request with automatic retry.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            path: API path (e.g., /indexes/my-index)
            **kwargs: Additional arguments passed to httpx
            
        Returns:
            JSON response as dictionary
            
        Raises:
            httpx.HTTPStatusError: If request fails after retries
        """
        url = f"{self.endpoint}{path}"
        params = kwargs.pop("params", {})
        params["api-version"] = self.api_version
        
        logger.debug(f"{method} {url}")
        
        try:
            response = await self.client.request(
                method=method,
                url=url,
                params=params,
                **kwargs
            )
            response.raise_for_status()
            
            # Return empty dict for 204 No Content responses
            if response.status_code == 204:
                return {}
                
            return response.json() if response.text else {}
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code}: {e.response.text}")
            # Try to parse error details
            try:
                error_detail = e.response.json()
                logger.error(f"Error details: {error_detail}")
            except:
                pass
            raise
        except Exception as e:
            logger.error(f"Request failed: {e}")
            raise
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()