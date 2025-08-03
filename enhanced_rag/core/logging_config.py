"""
Centralized logging configuration for Enhanced RAG
"""

import os
import logging
import sys

_logging_configured = False


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
        # Configure root logger
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )
        _logging_configured = True
        
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