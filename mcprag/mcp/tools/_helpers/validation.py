"""Validation helpers for MCP tools."""

import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)


def check_component(component: Optional[Any], name: str) -> bool:
    """Check if a component is available and log if not."""
    if not component:
        logger.debug(f"{name} component not available")
        return False
    return True