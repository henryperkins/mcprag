"""Azure AI Search automation utilities."""

from .index_manager import IndexAutomation
from .data_manager import DataAutomation
from .indexer_manager import IndexerAutomation
from .health_monitor import HealthMonitor
from .reindex_manager import ReindexAutomation
from .embedding_manager import EmbeddingAutomation
from .cli_manager import CLIAutomation
from .unified_manager import UnifiedAutomation

__all__ = [
    "IndexAutomation",
    "DataAutomation",
    "IndexerAutomation",
    "HealthMonitor",
    "ReindexAutomation",
    "EmbeddingAutomation",
    "CLIAutomation",
    "UnifiedAutomation"
]