"""Thread-safe configuration management for concurrent auth operations."""

import threading
from typing import Any
from contextlib import contextmanager


class ThreadSafeConfig:
    """Thread-local configuration wrapper to prevent race conditions."""
    
    _local = threading.local()
    _defaults = {
        'ADMIN_MODE': False,
        'DEV_MODE': False,
        'REQUIRE_MFA_FOR_ADMIN': False
    }
    
    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """Get thread-local config value."""
        if not hasattr(cls._local, 'config'):
            cls._local.config = cls._defaults.copy()
        return cls._local.config.get(key, default)
    
    @classmethod
    def set(cls, key: str, value: Any) -> None:
        """Set thread-local config value."""
        if not hasattr(cls._local, 'config'):
            cls._local.config = cls._defaults.copy()
        cls._local.config[key] = value
    
    @classmethod
    @contextmanager
    def override(cls, **kwargs):
        """Context manager for temporary config overrides."""
        if not hasattr(cls._local, 'config'):
            cls._local.config = cls._defaults.copy()
        
        old_values = {}
        for key, value in kwargs.items():
            old_values[key] = cls._local.config.get(key)
            cls._local.config[key] = value
        
        try:
            yield
        finally:
            for key, value in old_values.items():
                if value is None and key in cls._local.config:
                    del cls._local.config[key]
                else:
                    cls._local.config[key] = value