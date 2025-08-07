"""
Centralized logging configuration for Enhanced RAG
"""

import os
import logging
import logging.config
import sys
from typing import Any, Mapping, Optional, MutableMapping, Callable, cast

_logging_configured = False
_LOG_RECORD_FACTORY_SET = False
_ORIGINAL_FACTORY: Optional[Callable[..., logging.LogRecord]] = None
_SAFE_RESERVED = {
    # Reserved LogRecord attributes that must not be set via `extra`
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread", "threadName", "processName",
    "process", "message", "asctime"
}


def configure_logging(default_level: str = "INFO", component_name: str = None) -> logging.Logger:
    """Configure logging with centralized settings.
    
    Args:
        default_level: Default log level if not specified in environment
        component_name: Optional component name for the logger
        
    Returns:
        Logger instance for the component
    """
    global _logging_configured
    
    # Get log level from environment, respecting WEBHOOK_LOG_LEVEL first
    log_level = os.getenv("WEBHOOK_LOG_LEVEL") or os.getenv("LOG_LEVEL") or default_level
    
    # Only configure root logger once
    if not _logging_configured:
        # Defensive: avoid duplicate handlers if some other module already configured logging
        root = logging.getLogger()
        if not root.handlers:
            logging.basicConfig(
                level=log_level,
                format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
                handlers=[logging.StreamHandler(sys.stderr)]
            )
        else:
            # Respect existing handlers but ensure level/format are sane
            root.setLevel(log_level)
        _logging_configured = True

        # Install a safe LogRecordFactory that strips reserved keys from `extra`
        global _LOG_RECORD_FACTORY_SET, _ORIGINAL_FACTORY
        if not _LOG_RECORD_FACTORY_SET:
            _ORIGINAL_FACTORY = logging.getLogRecordFactory()

            def _safe_factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
                record = cast(Callable[..., logging.LogRecord], _ORIGINAL_FACTORY)(*args, **kwargs) if _ORIGINAL_FACTORY else logging.LogRecord(*args, **kwargs)  # type: ignore[arg-type]
                # If a logger passes `extra`, Python merges it into record.__dict__ before emit.
                # We defensively ensure no reserved attributes were overwritten by pruning.
                for key in list(record.__dict__.keys()):
                    if key in _SAFE_RESERVED and key not in {"levelname", "levelno", "name"}:
                        # Recompute 'message' safely; others are maintained by logging.
                        if key == "message":
                            try:
                                record.message = record.getMessage()
                            except Exception:
                                # If formatting fails, fall back to original msg
                                record.message = str(getattr(record, "msg", ""))
                        # For other reserved keys, do nothing (keep logger-managed values)
                        # Any 'extra' attempting to set them is effectively ignored.
                        # We don't delete them since logging expects them.
                        continue
                return record

            logging.setLogRecordFactory(_safe_factory)
            _LOG_RECORD_FACTORY_SET = True
        
        # Set specific log levels for noisy libraries
        logging.getLogger("azure").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("requests").setLevel(logging.WARNING)
    
    # Get or create logger for component
    if component_name:
        logger = logging.getLogger(component_name)
    else:
        logger = logging.getLogger()
    
    # Ensure logger uses the configured level
    logger.setLevel(log_level)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger with centralized configuration.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured logger instance
    """
    # Ensure logging is configured
    configure_logging()
    return logging.getLogger(name)