"""Azure AI Search REST API client for automation."""

from .client import AzureSearchClient
from .operations import SearchOperations

__all__ = ["AzureSearchClient", "SearchOperations"]