"""Response helper utilities for MCP tools."""
from typing import Any, Dict


def ok(data: Any) -> Dict[str, Any]:
    """Create a successful response."""
    return {"success": True, "data": data}


def err(message: str) -> Dict[str, Any]:
    """Create an error response."""
    return {"success": False, "error": message}
