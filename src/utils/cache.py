from typing import Any, Optional
import json
from datetime import timedelta
from uuid import UUID
from fastapi import BackgroundTasks
from pydantic import UUID4

# Cache duration constants
MINUTE = 60
HOUR = MINUTE * 60
DAY = HOUR * 24

class UUIDEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, UUID):
            # Convert UUID to string
            return str(obj)
        return super().default(obj)

class CacheManager:
    def __init__(self, redis_client, prefix: str = "cache"):
        self.redis = redis_client
        self.prefix = prefix

    def _get_key(self, key: str) -> str:
        """Generate prefixed cache key"""
        return f"{self.prefix}:{key}"
        
    async def clear_pattern(self, pattern: str) -> int:
        """Clear all cache entries matching a pattern
        
        Args:
            pattern: Pattern to match (e.g., "constitution:search:*")
            
        Returns:
            int: Number of keys deleted
        """
        try:
            # Get all keys matching the pattern
            pattern_with_prefix = self._get_key(pattern)
            keys = await self.redis.keys(pattern_with_prefix)
            
            # Delete all matching keys
            if keys:
                return await self.redis.delete(*keys)
            return 0
        except Exception as e:
            print(f"Cache clear error: {e}")  # Consider proper logging
            return 0

    async def delete(self, key: str) -> bool:
        """Delete a specific key from cache
        
        Args:
            key: The key to delete
            
        Returns:
            bool: True if key was deleted, False otherwise
        """
        try:
            result = await self.redis.delete(self._get_key(key))
            return result > 0
        except Exception as e:
            print(f"Cache delete error: {e}")  # Consider proper logging
            return False
    
    async def get(self, key: str) -> Optional[Any]:
        """Get data from cache"""
        try:
            data = await self.redis.get(self._get_key(key))
            return json.loads(data) if data else None
        except Exception as e:
            print(f"Cache get error: {e}")  # Consider proper logging
            return None

    async def set(
        self,
        key: str,
        data: Any,
        expire: int = HOUR,  # Default 1 hour
    ) -> bool:
        """Set data in cache with expiration"""
        try:
            serialized_data = json.dumps(data, cls=UUIDEncoder)
            await self.redis.set(
                self._get_key(key),
                serialized_data,
                ex=expire
            )
            return True
        except Exception as e:
            print(f"Cache set error: {e}")  # Consider proper logging
            return False

    async def delete(self, key: str) -> bool:
        """Delete data from cache"""
        try:
            await self.redis.delete(self._get_key(key))
            return True
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False

    async def set_background(
        self,
        background_tasks: BackgroundTasks,
        key: str,
        data: Any,
        expire: int = HOUR,
    ):
        """Set cache in background task"""
        background_tasks.add_task(self.set, key, data, expire)
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        try:
            return await self.redis.exists(self._get_key(key))
        except Exception as e:
            print(f"Cache exists error: {e}")
            return False

    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment a numeric value in cache"""
        try:
            return await self.redis.incr(self._get_key(key), amount)
        except Exception as e:
            print(f"Cache increment error: {e}")
            return 0

    async def expire_at(self, key: str, timestamp: int) -> bool:
        """Set a specific expiration timestamp for a key"""
        try:
            return await self.redis.expireat(self._get_key(key), timestamp)
        except Exception as e:
            print(f"Cache expire_at error: {e}")
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching a pattern"""
        try:
            keys = await self.redis.keys(self._get_key(pattern))
            if keys:
                return await self.redis.delete(*keys)
            return 0
        except Exception as e:
            print(f"Cache clear_pattern error: {e}")
            return 0
        
