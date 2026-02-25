"""
Redis caching utility for FinSight backend.
Provides async caching with JSON serialization for API responses.
"""
import json
import logging
from typing import Any, Optional
from datetime import timedelta

logger = logging.getLogger(__name__)

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("redis-py not installed. Caching disabled.")


class CacheManager:
    """Async Redis cache manager with JSON serialization."""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self._client: Optional[redis.Redis] = None
        self._enabled = False

    async def connect(self, redis_url: Optional[str] = None) -> bool:
        """Initialize Redis connection. Returns True if successful."""
        # Use provided URL or fall back to instance URL
        if redis_url:
            self.redis_url = redis_url

        if not REDIS_AVAILABLE:
            return False

        try:
            self._client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
            )
            await self._client.ping()
            self._enabled = True
            logger.info(f"Connected to Redis at {self.redis_url}")
            return True
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Caching disabled.")
            self._enabled = False
            return False
    
    async def disconnect(self):
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._enabled = False
            logger.info("Disconnected from Redis")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get cached value. Returns None if not found or cache disabled."""
        if not self._enabled or not self._client:
            return None
        
        try:
            value = await self._client.get(key)
            if value is None:
                return None
            return json.loads(value)
        except Exception as e:
            logger.error(f"Cache GET error for {key}: {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: timedelta = timedelta(minutes=5)
    ) -> bool:
        """Cache a value with TTL. Returns True if successful."""
        if not self._enabled or not self._client:
            return False
        
        try:
            serialized = json.dumps(value, default=str)
            await self._client.setex(key, int(ttl.total_seconds()), serialized)
            return True
        except Exception as e:
            logger.error(f"Cache SET error for {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete a cached key. Returns True if deleted."""
        if not self._enabled or not self._client:
            return False
        
        try:
            await self._client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache DELETE error for {key}: {e}")
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern. Returns count deleted."""
        if not self._enabled or not self._client:
            return 0
        
        try:
            keys = await self._client.keys(pattern)
            if keys:
                return await self._client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache CLEAR error for pattern {pattern}: {e}")
            return 0
    
    @property
    def enabled(self) -> bool:
        """Check if caching is enabled."""
        return self._enabled


# Global cache instance
cache_manager = CacheManager()


# Cache key helpers
def make_cache_key(prefix: str, *args, **kwargs) -> str:
    """Create a cache key from arguments."""
    key_parts = [prefix]
    for arg in args:
        key_parts.append(str(arg))
    for k, v in sorted(kwargs.items()):
        key_parts.append(f"{k}={v}")
    return ":".join(key_parts).replace(" ", "_").lower()


# Decorator for caching async function results
def cached(
    prefix: str,
    ttl: timedelta = timedelta(minutes=5),
    key_func: Optional[callable] = None
):
    """
    Decorator to cache async function results.
    
    Usage:
        @cached("stock:quote", ttl=timedelta(minutes=2))
        async def get_stock_quote(symbol: str):
            ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                key = make_cache_key(prefix, *args, **kwargs)
            
            # Try cache first
            cached_result = await cache_manager.get(key)
            if cached_result is not None:
                logger.debug(f"Cache HIT: {key}")
                return cached_result
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache result
            if result is not None:
                await cache_manager.set(key, result, ttl)
                logger.debug(f"Cache SET: {key}")
            
            return result
        return wrapper
    return decorator
