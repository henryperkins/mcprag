"""
Configuration module for mcprag.
This module provides backwards compatibility for old uppercase property names.
"""

from enhanced_rag.core.unified_config import UnifiedConfig as _UnifiedConfig, get_config

class Config:
    """Backwards compatibility wrapper for UnifiedConfig."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._config = get_config()
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._config = get_config()
            self._initialized = True
    
    # Map old uppercase names to new lowercase names
    @property
    def ENDPOINT(self):
        return self._config.acs_endpoint
    
    @property
    def ADMIN_KEY(self):
        return self._config.acs_admin_key.get_secret_value() if self._config.acs_admin_key else None
    
    @property
    def QUERY_KEY(self):
        return self._config.acs_query_key.get_secret_value() if self._config.acs_query_key else None
    
    @property
    def INDEX_NAME(self):
        return self._config.acs_index_name
    
    @property
    def ADMIN_MODE(self):
        return self._config.mcp_admin_mode
    
    @ADMIN_MODE.setter
    def ADMIN_MODE(self, value):
        self._config.mcp_admin_mode = value
    
    @property
    def LOG_LEVEL(self):
        return self._config.mcp_log_level
    
    @property
    def CACHE_TTL_SECONDS(self):
        return self._config.cache_ttl_seconds
    
    @property
    def CACHE_MAX_ENTRIES(self):
        return self._config.cache_max_entries
    
    @property
    def DEBUG_TIMINGS(self):
        return self._config.debug_timings
    
    @property
    def DEV_MODE(self):
        return self._config.mcp_dev_mode
    
    @property
    def STYTCH_PROJECT_ID(self):
        return self._config.stytch_project_id
    
    @property
    def STYTCH_SECRET(self):
        return self._config.stytch_secret.get_secret_value() if self._config.stytch_secret else None
    
    @property
    def STYTCH_ENV(self):
        return self._config.stytch_env
    
    @property
    def SERVICE_API_KEY(self):
        return getattr(self._config, 'service_api_key', None)
    
    @property
    def REQUIRE_MFA_FOR_ADMIN(self):
        return getattr(self._config, 'require_mfa_for_admin', False)

# Create singleton instance
Config = Config()

__all__ = ['Config', 'get_config']