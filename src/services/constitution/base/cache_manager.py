"""
Enhanced cache manager specifically for constitution services.
Extends the base cache manager with constitution-specific functionality.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from ....utils.cache import CacheManager, MINUTE, HOUR, DAY

logger = logging.getLogger(__name__)

# Constitution-specific cache key prefixes
CACHE_KEY_OVERVIEW = "constitution:overview"
CACHE_KEY_CHAPTER_PREFIX = "constitution:chapter:"
CACHE_KEY_ARTICLE_PREFIX = "constitution:article:"
CACHE_KEY_SEARCH_PREFIX = "constitution:search:"
CACHE_KEY_POPULAR_PREFIX = "constitution:popular:"
CACHE_KEY_USER_BOOKMARKS_PREFIX = "constitution:user:"
CACHE_KEY_USER_PROGRESS_PREFIX = "constitution:user:"
CACHE_KEY_VIEWS_PREFIX = "constitution:views:"
CACHE_KEY_ANALYTICS_PREFIX = "constitution:analytics:"
CACHE_KEY_RELATIONS_PREFIX = "constitution:relations:"


class ConstitutionCacheManager(CacheManager):
    """
    Enhanced cache manager for constitution services.
    Provides constitution-specific caching patterns and optimizations.
    """
    
    def __init__(self, redis_client, prefix: str = "constitution"):
        super().__init__(redis_client, prefix)
        self.logger = logger
    
    async def get_constitution_overview(self) -> Optional[Dict]:
        """
        Get cached constitution overview.
        
        Returns:
            Optional[Dict]: Cached overview data or None
        """
        return await self.get(CACHE_KEY_OVERVIEW)
    
    async def set_constitution_overview(self, data: Dict, expire: int = 6 * HOUR):
        """
        Cache constitution overview data.
        
        Args:
            data: Overview data to cache
            expire: Expiration time in seconds
        """
        await self.set(CACHE_KEY_OVERVIEW, data, expire)
    
    async def get_chapter(self, chapter_num: int) -> Optional[Dict]:
        """
        Get cached chapter data.
        
        Args:
            chapter_num: Chapter number
            
        Returns:
            Optional[Dict]: Cached chapter data or None
        """
        cache_key = f"{CACHE_KEY_CHAPTER_PREFIX}{chapter_num}"
        return await self.get(cache_key)
    
    async def set_chapter(self, chapter_num: int, data: Dict, expire: int = DAY):
        """
        Cache chapter data.
        
        Args:
            chapter_num: Chapter number
            data: Chapter data to cache
            expire: Expiration time in seconds
        """
        cache_key = f"{CACHE_KEY_CHAPTER_PREFIX}{chapter_num}"
        await self.set(cache_key, data, expire)
    
    async def get_article(self, chapter_num: int, article_num: int) -> Optional[Dict]:
        """
        Get cached article data.
        
        Args:
            chapter_num: Chapter number
            article_num: Article number
            
        Returns:
            Optional[Dict]: Cached article data or None
        """
        cache_key = f"{CACHE_KEY_ARTICLE_PREFIX}{chapter_num}:{article_num}"
        return await self.get(cache_key)
    
    async def set_article(self, chapter_num: int, article_num: int, data: Dict, expire: int = DAY):
        """
        Cache article data.
        
        Args:
            chapter_num: Chapter number
            article_num: Article number
            data: Article data to cache
            expire: Expiration time in seconds
        """
        cache_key = f"{CACHE_KEY_ARTICLE_PREFIX}{chapter_num}:{article_num}"
        await self.set(cache_key, data, expire)
    
    async def get_search_results(self, query_hash: str) -> Optional[Dict]:
        """
        Get cached search results.
        
        Args:
            query_hash: Search query hash
            
        Returns:
            Optional[Dict]: Cached search results or None
        """
        cache_key = f"{CACHE_KEY_SEARCH_PREFIX}{query_hash}"
        return await self.get(cache_key)
    
    async def set_search_results(self, query_hash: str, data: Dict, expire: int = HOUR):
        """
        Cache search results.
        
        Args:
            query_hash: Search query hash
            data: Search results to cache
            expire: Expiration time in seconds
        """
        cache_key = f"{CACHE_KEY_SEARCH_PREFIX}{query_hash}"
        await self.set(cache_key, data, expire)
    
    async def get_popular_content(self, timeframe: str) -> Optional[Dict]:
        """
        Get cached popular content.
        
        Args:
            timeframe: Timeframe for popular content
            
        Returns:
            Optional[Dict]: Cached popular content or None
        """
        cache_key = f"{CACHE_KEY_POPULAR_PREFIX}{timeframe}"
        return await self.get(cache_key)
    
    async def set_popular_content(self, timeframe: str, data: Dict, expire: int = HOUR):
        """
        Cache popular content.
        
        Args:
            timeframe: Timeframe for popular content
            data: Popular content data to cache
            expire: Expiration time in seconds
        """
        cache_key = f"{CACHE_KEY_POPULAR_PREFIX}{timeframe}"
        await self.set(cache_key, data, expire)
    
    async def get_user_bookmarks(self, user_id: str) -> Optional[Dict]:
        """
        Get cached user bookmarks.
        
        Args:
            user_id: User ID
            
        Returns:
            Optional[Dict]: Cached user bookmarks or None
        """
        cache_key = f"{CACHE_KEY_USER_BOOKMARKS_PREFIX}{user_id}:bookmarks"
        return await self.get(cache_key)
    
    async def set_user_bookmarks(self, user_id: str, data: Dict, expire: int = HOUR):
        """
        Cache user bookmarks.
        
        Args:
            user_id: User ID
            data: Bookmarks data to cache
            expire: Expiration time in seconds
        """
        cache_key = f"{CACHE_KEY_USER_BOOKMARKS_PREFIX}{user_id}:bookmarks"
        await self.set(cache_key, data, expire)
    
    async def clear_user_bookmarks(self, user_id: str):
        """
        Clear cached user bookmarks.
        
        Args:
            user_id: User ID
        """
        cache_key = f"{CACHE_KEY_USER_BOOKMARKS_PREFIX}{user_id}:bookmarks"
        await self.delete(cache_key)
    
    async def get_user_progress(self, user_id: str) -> Optional[Dict]:
        """
        Get cached user reading progress.
        
        Args:
            user_id: User ID
            
        Returns:
            Optional[Dict]: Cached user progress or None
        """
        cache_key = f"{CACHE_KEY_USER_PROGRESS_PREFIX}{user_id}:progress"
        return await self.get(cache_key)
    
    async def set_user_progress(self, user_id: str, data: Dict, expire: int = HOUR):
        """
        Cache user reading progress.
        
        Args:
            user_id: User ID
            data: Progress data to cache
            expire: Expiration time in seconds
        """
        cache_key = f"{CACHE_KEY_USER_PROGRESS_PREFIX}{user_id}:progress"
        await self.set(cache_key, data, expire)
    
    async def clear_user_progress(self, user_id: str):
        """
        Clear cached user reading progress.
        
        Args:
            user_id: User ID
        """
        cache_key = f"{CACHE_KEY_USER_PROGRESS_PREFIX}{user_id}:progress"
        await self.delete(cache_key)
    
    async def increment_view_count(self, item_type: str, item_id: str) -> int:
        """
        Increment view count for an item.
        
        Args:
            item_type: Type of item (chapter, article, search)
            item_id: ID of the item
            
        Returns:
            int: New view count
        """
        view_key = f"{CACHE_KEY_VIEWS_PREFIX}{item_type}:{item_id}"
        return await self.increment(view_key)
    
    async def get_view_count(self, item_type: str, item_id: str) -> int:
        """
        Get view count for an item.
        
        Args:
            item_type: Type of item (chapter, article, search)
            item_id: ID of the item
            
        Returns:
            int: Current view count
        """
        view_key = f"{CACHE_KEY_VIEWS_PREFIX}{item_type}:{item_id}"
        count = await self.get(view_key)
        return count if count is not None else 0
    
    async def clear_all_constitution_cache(self):
        """
        Clear all constitution-related cache entries.
        """
        patterns = [
            f"{CACHE_KEY_OVERVIEW}*",
            f"{CACHE_KEY_CHAPTER_PREFIX}*",
            f"{CACHE_KEY_ARTICLE_PREFIX}*",
            f"{CACHE_KEY_SEARCH_PREFIX}*",
            f"{CACHE_KEY_POPULAR_PREFIX}*",
            f"{CACHE_KEY_USER_BOOKMARKS_PREFIX}*",
            f"{CACHE_KEY_USER_PROGRESS_PREFIX}*",
            f"{CACHE_KEY_VIEWS_PREFIX}*",
            f"{CACHE_KEY_ANALYTICS_PREFIX}*",
            f"{CACHE_KEY_RELATIONS_PREFIX}*"
        ]
        
        total_cleared = 0
        for pattern in patterns:
            cleared = await self.clear_pattern(pattern)
            total_cleared += cleared
        
        self.logger.info(f"Cleared {total_cleared} constitution cache entries")
        return total_cleared
    
    async def clear_user_cache(self, user_id: str):
        """
        Clear all cached data for a specific user.
        
        Args:
            user_id: User ID
        """
        patterns = [
            f"{CACHE_KEY_USER_BOOKMARKS_PREFIX}{user_id}:*",
            f"{CACHE_KEY_USER_PROGRESS_PREFIX}{user_id}:*"
        ]
        
        total_cleared = 0
        for pattern in patterns:
            cleared = await self.clear_pattern(pattern)
            total_cleared += cleared
        
        self.logger.info(f"Cleared {total_cleared} cache entries for user {user_id}")
        return total_cleared
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics for constitution services.
        
        Returns:
            Dict[str, Any]: Cache statistics
        """
        try:
            # Get basic cache info
            info = await self.redis.info()
            
            # Count constitution-specific keys
            constitution_keys = await self.redis.keys(f"{self.prefix}:*")
            key_count = len(constitution_keys)
            
            # Get memory usage
            memory_usage = info.get('used_memory_human', 'Unknown')
            
            # Get hit rate (approximation)
            keyspace_hits = info.get('keyspace_hits', 0)
            keyspace_misses = info.get('keyspace_misses', 0)
            total_requests = keyspace_hits + keyspace_misses
            hit_rate = (keyspace_hits / total_requests * 100) if total_requests > 0 else 0
            
            return {
                "constitution_keys": key_count,
                "memory_usage": memory_usage,
                "hit_rate_percent": round(hit_rate, 2),
                "total_requests": total_requests,
                "keyspace_hits": keyspace_hits,
                "keyspace_misses": keyspace_misses
            }
        except Exception as e:
            self.logger.error(f"Error getting cache stats: {str(e)}")
            return {"error": str(e)}
    
    async def health_check(self) -> bool:
        """
        Perform health check on the cache.
        
        Returns:
            bool: True if healthy, False otherwise
        """
        try:
            # Try to set and get a test value
            test_key = f"{self.prefix}:health_check"
            test_value = {"timestamp": datetime.now().isoformat()}
            
            await self.set(test_key, test_value, expire=10)
            result = await self.get(test_key)
            
            # Clean up test key
            await self.delete(test_key)
            
            return result is not None
        except Exception as e:
            self.logger.error(f"Cache health check failed: {str(e)}")
            return False