"""Structured audit logging for authentication and authorization events."""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum

logger = logging.getLogger("mcprag.audit")


class AuditEvent(Enum):
    """Audit event types."""
    AUTH_SUCCESS = "auth.success"
    AUTH_FAILURE = "auth.failure"
    TIER_DENIED = "tier.denied"
    TIER_GRANTED = "tier.granted"
    TOOL_EXECUTED = "tool.executed"
    TOOL_DENIED = "tool.denied"
    MFA_REQUIRED = "mfa.required"
    API_KEY_USED = "api_key.used"


class AuditLogger:
    """Structured audit logger for security events."""
    
    @staticmethod
    def log(
        event: AuditEvent,
        user_id: Optional[str] = None,
        tier: Optional[str] = None,
        tool: Optional[str] = None,
        transport: Optional[str] = None,
        success: bool = True,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log an audit event with structured data."""
        audit_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": event.value,
            "success": success,
            "user_id": user_id,
            "tier": tier,
            "tool": tool,
            "transport": transport,
            "details": details or {}
        }
        
        # Remove None values
        audit_record = {k: v for k, v in audit_record.items() if v is not None}
        
        # Log as JSON for easy parsing
        if success:
            logger.info(json.dumps(audit_record))
        else:
            logger.warning(json.dumps(audit_record))
    
    @staticmethod
    def auth_success(user_id: str, tier: str, method: str, transport: str = "unknown"):
        """Log successful authentication."""
        AuditLogger.log(
            AuditEvent.AUTH_SUCCESS,
            user_id=user_id,
            tier=tier,
            transport=transport,
            details={"method": method}
        )
    
    @staticmethod
    def auth_failure(reason: str, transport: str = "unknown", token_prefix: Optional[str] = None):
        """Log failed authentication."""
        AuditLogger.log(
            AuditEvent.AUTH_FAILURE,
            transport=transport,
            success=False,
            details={"reason": reason, "token_prefix": token_prefix}
        )
    
    @staticmethod
    def tool_access(user_id: str, tool: str, tier: str, granted: bool, transport: str = "unknown"):
        """Log tool access attempt."""
        event = AuditEvent.TOOL_EXECUTED if granted else AuditEvent.TOOL_DENIED
        AuditLogger.log(
            event,
            user_id=user_id,
            tier=tier,
            tool=tool,
            transport=transport,
            success=granted
        )