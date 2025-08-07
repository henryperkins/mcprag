"""
Response helper utilities for consistent API responses.
"""

from typing import Any, Dict
import logging

logger = logging.getLogger(__name__)


def ok(data: Any) -> Dict[str, Any]:
    """Create a successful response."""
    return {"ok": True, "data": data}


def err(msg: str, code: str = "error") -> Dict[str, Any]:
    """Create an error response."""
    # Emit a structured log entry so that operational tooling can pick up on
    # user-visible errors.  We purposefully log at INFO level – many callers
    # treat user errors as part of the expected control flow and therefore do
    # not want them to appear as noisy WARNING/ERROR lines.
    logger.info("mcp_response_error", extra={"code": code, "message": msg})
    return {"ok": False, "error": msg, "code": code}
