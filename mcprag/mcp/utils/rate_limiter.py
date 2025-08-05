"""Rate limiting middleware for MCP tools."""

import time
from functools import wraps
from collections import defaultdict
from typing import Dict, List, Callable, Any
import asyncio
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    max_requests: int = 100
    window_seconds: int = 60
    burst_limit: int = 10
    burst_window_seconds: int = 1


class RateLimiter:
    """Thread-safe rate limiter with configurable windows and burst protection."""
    
    def __init__(self, config: RateLimitConfig = None):
        """Initialize rate limiter.
        
        Args:
            config: Rate limiting configuration
        """
        self.config = config or RateLimitConfig()
        self.requests: Dict[str, List[float]] = defaultdict(list)
        self._lock = asyncio.Lock()
    
    async def check_rate_limit(self, client_id: str) -> bool:
        """Check if request is within rate limits.
        
        Args:
            client_id: Unique identifier for the client
            
        Returns:
            True if request is allowed, False if rate limited
        """
        async with self._lock:
            now = time.time()
            
            # Clean old requests from main window
            self.requests[client_id] = [
                req_time for req_time in self.requests[client_id] 
                if now - req_time < self.config.window_seconds
            ]
            
            # Check main rate limit
            if len(self.requests[client_id]) >= self.config.max_requests:
                logger.warning(f"Rate limit exceeded for client {client_id}: "
                             f"{len(self.requests[client_id])}/{self.config.max_requests} "
                             f"in {self.config.window_seconds}s window")
                return False
            
            # Check burst limit
            recent_requests = [
                req_time for req_time in self.requests[client_id]
                if now - req_time < self.config.burst_window_seconds
            ]
            
            if len(recent_requests) >= self.config.burst_limit:
                logger.warning(f"Burst limit exceeded for client {client_id}: "
                             f"{len(recent_requests)}/{self.config.burst_limit} "
                             f"in {self.config.burst_window_seconds}s window")
                return False
            
            # Record the request
            self.requests[client_id].append(now)
            return True
    
    def get_stats(self, client_id: str) -> Dict[str, Any]:
        """Get rate limiting statistics for a client.
        
        Args:
            client_id: Client identifier
            
        Returns:
            Statistics dictionary
        """
        now = time.time()
        requests_in_window = [
            req_time for req_time in self.requests[client_id]
            if now - req_time < self.config.window_seconds
        ]
        
        requests_in_burst = [
            req_time for req_time in self.requests[client_id]
            if now - req_time < self.config.burst_window_seconds
        ]
        
        return {
            "requests_in_window": len(requests_in_window),
            "max_requests": self.config.max_requests,
            "window_seconds": self.config.window_seconds,
            "requests_in_burst": len(requests_in_burst),
            "burst_limit": self.config.burst_limit,
            "burst_window_seconds": self.config.burst_window_seconds,
            "remaining_requests": max(0, self.config.max_requests - len(requests_in_window)),
            "window_reset_time": now + self.config.window_seconds
        }


class RateLimitError(Exception):
    """Exception raised when rate limit is exceeded."""
    
    def __init__(self, message: str, retry_after: float = None):
        """Initialize rate limit error.
        
        Args:
            message: Error message
            retry_after: Seconds to wait before retrying
        """
        super().__init__(message)
        self.retry_after = retry_after


def rate_limit(config: RateLimitConfig = None, client_id_func: Callable = None):
    """Decorator to add rate limiting to functions.
    
    Args:
        config: Rate limiting configuration
        client_id_func: Function to extract client ID from args/kwargs
    """
    rate_limiter = RateLimiter(config)
    
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Extract client ID
            if client_id_func:
                client_id = client_id_func(*args, **kwargs)
            else:
                # Default: use function name as client ID (global rate limit)
                client_id = f"{func.__module__}.{func.__name__}"
            
            # Check rate limit
            if not await rate_limiter.check_rate_limit(client_id):
                stats = rate_limiter.get_stats(client_id)
                raise RateLimitError(
                    f"Rate limit exceeded. Try again in {stats['window_reset_time'] - time.time():.1f} seconds",
                    retry_after=stats['window_reset_time'] - time.time()
                )
            
            # Execute function
            return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For sync functions, we need to handle rate limiting differently
            # This is a simplified version - for full async support, convert to async
            client_id = client_id_func(*args, **kwargs) if client_id_func else f"{func.__module__}.{func.__name__}"
            
            # Simple sync rate limiting (not thread-safe)
            now = time.time()
            if not hasattr(sync_wrapper, '_requests'):
                sync_wrapper._requests = defaultdict(list)
            
            # Clean old requests
            sync_wrapper._requests[client_id] = [
                req_time for req_time in sync_wrapper._requests[client_id]
                if now - req_time < (config.window_seconds if config else 60)
            ]
            
            max_reqs = config.max_requests if config else 100
            if len(sync_wrapper._requests[client_id]) >= max_reqs:
                raise RateLimitError(f"Rate limit exceeded for {client_id}")
            
            sync_wrapper._requests[client_id].append(now)
            return func(*args, **kwargs)
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Global rate limiter instance
default_rate_limiter = RateLimiter()


async def check_global_rate_limit(client_id: str) -> bool:
    """Check global rate limit for a client.
    
    Args:
        client_id: Client identifier
        
    Returns:
        True if request is allowed
    """
    return await default_rate_limiter.check_rate_limit(client_id)


def get_global_rate_limit_stats(client_id: str) -> Dict[str, Any]:
    """Get global rate limit statistics.
    
    Args:
        client_id: Client identifier
        
    Returns:
        Statistics dictionary
    """
    return default_rate_limiter.get_stats(client_id)