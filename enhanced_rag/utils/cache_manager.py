"""
Simple cache manager for enhanced RAG pipeline
"""

import time
from typing import Dict, Any, Optional
from collections import OrderedDict
import asyncio
import fnmatch


class CacheManager:
    """TTL-based cache with LRU eviction"""
    
    def __init__(self, ttl: int = 60, max_size: int = 500):
        self.ttl = ttl
        self.max_size = max_size
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._lock = asyncio.Lock()
        
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired"""
        async with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if time.time() - entry['timestamp'] < self.ttl:
                    # Move to end (LRU)
                    self._cache.move_to_end(key)
                    return entry['value']
                else:
                    # Expired
                    del self._cache[key]
            return None
            
    async def set(self, key: str, value: Any) -> None:
        """Set value in cache"""
        async with self._lock:
            # Remove oldest if at capacity
            if len(self._cache) >= self.max_size and key not in self._cache:
                self._cache.popitem(last=False)
                
            self._cache[key] = {
                'value': value,
                'timestamp': time.time()
            }
            # Move to end
            self._cache.move_to_end(key)
            
    async def clear(self) -> None:
        """Clear all cache entries"""
        async with self._lock:
            self._cache.clear()

    async def clear_scope(self, scope: str) -> int:
        """Clear entries whose keys start with the given scope prefix.

        Example:
            scope = "search" will clear keys like "search:..."
        
        Returns:
            Number of entries cleared.
        """
        prefix = f"{scope.strip()}:" if not scope.endswith(":") else scope
        async with self._lock:
            keys = [k for k in list(self._cache.keys()) if k.startswith(prefix)]
            for k in keys:
                del self._cache[k]
            return len(keys)

    async def clear_pattern(self, pattern: str) -> int:
        """Clear entries matching a glob-style pattern (e.g., 'search:*query*').

        Returns:
            Number of entries cleared.
        """
        async with self._lock:
            keys = [k for k in list(self._cache.keys()) if fnmatch.fnmatch(k, pattern)]
            for k in keys:
                del self._cache[k]
            return len(keys)
            
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        async with self._lock:
            total_entries = len(self._cache)
            expired = 0
            current_time = time.time()
            
            for entry in self._cache.values():
                if current_time - entry['timestamp'] >= self.ttl:
                    expired += 1
                    
            return {
                'total_entries': total_entries,
                'active_entries': total_entries - expired,
                'expired_entries': expired,
                'max_size': self.max_size,
                'ttl_seconds': self.ttl
            }