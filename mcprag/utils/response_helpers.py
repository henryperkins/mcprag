"""
Response helper utilities for consistent API responses.
"""

from typing import Any, Dict


def ok(data: Any) -> Dict[str, Any]:
    """Create a successful response."""
    return {"ok": True, "data": data}


def err(msg: str, code: str = "error") -> Dict[str, Any]:
    """Create an error response."""
    return {"ok": False, "error": msg, "code": code}
