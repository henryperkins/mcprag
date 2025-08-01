"""
GitHub Integration Module for Enhanced RAG
Provides GitHub repository indexing and webhook integration
"""

from .api_client import GitHubClient
from .remote_indexer import RemoteIndexer

__all__ = [
    'GitHubClient',
    'RemoteIndexer',
]

# Make the webhook app available for uvicorn
try:
    from .webhook_app import app
    __all__.append('app')
except ImportError:
    # Webhook app requires FastAPI and other dependencies
    pass