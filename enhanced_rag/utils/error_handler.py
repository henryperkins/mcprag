"""
Error handling utilities for Enhanced RAG system
"""

import logging
import traceback
from typing import Dict, Any, Optional, Type
from datetime import datetime

logger = logging.getLogger(__name__)


class ErrorHandler:
    """
    Centralized error handling for the RAG pipeline
    """

    def __init__(self):
        self.error_counts: Dict[str, int] = {}
        self.last_errors: Dict[str, datetime] = {}

    async def handle_error(
        self,
        error: Exception,
        context: Dict[str, Any],
        reraise: bool = False
    ) -> str:
        """
        Handle an error with context information

        Args:
            error: The exception that occurred
            context: Context information about where the error occurred
            reraise: Whether to reraise the exception after handling

        Returns:
            Error message string
        """
        error_type = type(error).__name__
        error_msg = str(error)

        # Track error frequency
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        self.last_errors[error_type] = datetime.utcnow()

        # Create detailed error message
        detailed_msg = f"{error_type}: {error_msg}"

        # Add context if available
        if context:
            context_str = ", ".join([f"{k}={v}" for k, v in context.items()])
            detailed_msg += f" (Context: {context_str})"

        # Log the error
        logger.error(f"❌ {detailed_msg}")
        logger.debug(f"Stack trace: {traceback.format_exc()}")

        if reraise:
            raise error

        return detailed_msg

    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        return {
            'error_counts': dict(self.error_counts),
            'last_errors': {
                error_type: timestamp.isoformat()
                for error_type, timestamp in self.last_errors.items()
            },
            'total_errors': sum(self.error_counts.values())
        }
