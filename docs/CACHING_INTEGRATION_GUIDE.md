# Caching Integration Guide

This guide explains how to integrate the new cached services for user profiles and achievements with proper revoke mechanisms.

## 🗂️ New Files Created

### Services
- `src/services/cached_user_service.py` - Enhanced user service with caching
- `src/services/cached_achievement_service.py` - Enhanced achievement service with caching

### Routes
- `src/routers/cached_user_routes.py` - User routes with caching
- `src/routers/cached_achievement_routes.py` - Achievement routes with caching

## 📋 Integration Steps

### 1. Update Dependencies

Ensure your `requirements.txt` includes the following Redis dependencies:

```txt
redis>=4.5.0
aioredis>=2.0.0
```

### 2. Update Main Application

Update `main.py` to include the new cached routes:

```python
from src.routers import cached_user_routes, cached_achievement_routes

# Add cached routes
app.include_router(cached_user_routes.router, prefix="/api/v1")
app.include_router(cached_achievement_routes.router, prefix="/api/v1")

# Optional: Keep original routes for backwards compatibility
# app.include_router(user_routes.router, prefix="/api/v1")
# app.include_router(achievement_routes.router, prefix="/api/v1")
```

### 3. Update Cache Manager Dependency

Create a proper cache manager dependency in `src/dependencies/cache.py`:

```python
from redis.asyncio import Redis
from src.utils.cache import CacheManager
from src.core.config import settings

async def get_cache_manager():
    """Get Redis cache manager"""
    redis_client = Redis.from_url(settings.redis_url)
    cache_manager = CacheManager(redis_client, prefix="katiba360")
    
    try:
        yield cache_manager
    finally:
        await redis_client.close()
```

### 4. Update Service Dependencies

Update the service dependencies in both cached services:

```python
# In cached_user_service.py and cached_achievement_service.py
from src.dependencies.cache import get_cache_manager

async def get_cached_user_service(
    db: AsyncSession = Depends(get_db),
    cache_manager: CacheManager = Depends(get_cache_manager)
) -> CachedUserService:
    return CachedUserService(db, cache_manager)

async def get_cached_achievement_service(
    db: AsyncSession = Depends(get_db),
    cache_manager: CacheManager = Depends(get_cache_manager)
) -> CachedAchievementService:
    return CachedAchievementService(db, cache_manager)
```

## 🔄 Cache Strategy Overview

### Cache Keys Pattern
```
user:{user_id}:profile               # User basic profile
user:{user_id}:full_profile          # Complete user profile
user:{user_id}:preferences           # User preferences
user:{user_id}:languages             # User languages
user:{user_id}:accessibility         # Accessibility settings
user:{user_id}:interests             # User interests
user:{user_id}:stats                 # User statistics

achievements:{user_id}:achievements   # User achievements
achievements:{user_id}:summary        # Achievement summary
achievements:{user_id}:stats          # Achievement statistics
achievements:global:leaderboard       # Global leaderboard
achievements:global:recent_achievements # Recent achievements
```

### Cache Expiration Times
- **User Profile Data**: 1 hour
- **User Achievements**: 30 minutes  
- **Global Leaderboards**: 15 minutes
- **Recent Achievements**: 5 minutes

### Cache Invalidation Strategy
1. **User Profile Updates**: Invalidate all `user:{user_id}:*` keys
2. **Achievement Awards**: Invalidate user achievement keys + global keys
3. **Preference Updates**: Invalidate user preferences + full profile
4. **Background Tasks**: Automatic cache warming for frequently accessed data

## 🚀 Usage Examples

### 1. Using Cached User Service

```python
from src.services.cached_user_service import CachedUserService

# Get user with caching
user = await cached_user_service.get_user_by_id_cached(user_id, background_tasks)

# Get full profile with caching
profile = await cached_user_service.get_full_user_profile_cached(user_id, background_tasks)

# Update user and invalidate cache
updated_user = await cached_user_service.update_user_profile_cached(
    user_id, update_data, background_tasks
)
```

### 2. Using Cached Achievement Service

```python
from src.services.cached_achievement_service import CachedAchievementService

# Get achievements with caching
achievements = await cached_achievement_service.get_user_achievements_cached(
    user_id, background_tasks
)

# Award achievement and invalidate cache
new_achievement = await cached_achievement_service.award_achievement_cached(
    user_id, badge_type, achievement_data, background_tasks
)

# Get leaderboard with caching
leaderboard = await cached_achievement_service.get_leaderboard_cached(
    limit=10, offset=0, background_tasks=background_tasks
)
```

## 🛠️ Cache Management

### Manual Cache Invalidation

Both services provide manual cache invalidation endpoints:

```bash
# Invalidate user cache
POST /api/v1/users/cache/invalidate

# Invalidate achievement cache
POST /api/v1/achievements/cache/invalidate

# Invalidate global achievement cache
POST /api/v1/achievements/cache/invalidate/global
```

### Cache Warming

The services automatically warm cache in the background:

```python
# Cache warming happens automatically when background_tasks is provided
user = await cached_user_service.get_user_by_id_cached(user_id, background_tasks)
```

## 📊 Performance Benefits

### Expected Improvements
1. **User Profile Load Time**: ~70% reduction (from DB query to Redis lookup)
2. **Achievement Pages**: ~60% reduction (cached summaries and stats)
3. **Leaderboards**: ~80% reduction (cached rankings)
4. **Database Load**: ~50% reduction (fewer repeated queries)

### Cache Hit Rates
- **User Profile**: Expected 85-90% hit rate
- **Achievements**: Expected 80-85% hit rate
- **Leaderboards**: Expected 90-95% hit rate

## 🔧 Configuration

### Redis Configuration

Update `src/core/config.py`:

```python
class Settings:
    redis_url: str = "redis://localhost:6379/0"
    cache_default_ttl: int = 3600  # 1 hour
    cache_user_ttl: int = 3600     # 1 hour
    cache_achievement_ttl: int = 1800  # 30 minutes
    cache_leaderboard_ttl: int = 900   # 15 minutes
```

### Environment Variables

```env
REDIS_URL=redis://localhost:6379/0
CACHE_DEFAULT_TTL=3600
CACHE_USER_TTL=3600
CACHE_ACHIEVEMENT_TTL=1800
CACHE_LEADERBOARD_TTL=900
```

## 🧪 Testing

### Unit Tests

```python
import pytest
from unittest.mock import AsyncMock, patch
from src.services.cached_user_service import CachedUserService

@pytest.mark.asyncio
async def test_get_user_by_id_cached():
    # Test cache hit
    cache_manager = AsyncMock()
    cache_manager.get.return_value = '{"id": "123", "name": "Test User"}'
    
    service = CachedUserService(db_mock, cache_manager)
    user = await service.get_user_by_id_cached(uuid.UUID("123"))
    
    assert user.name == "Test User"
    cache_manager.get.assert_called_once()
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_cache_invalidation_on_update():
    # Test that cache is invalidated when user is updated
    service = CachedUserService(db, cache_manager)
    
    # Update user
    await service.update_user_profile_cached(user_id, update_data)
    
    # Verify cache was invalidated
    cache_manager.delete.assert_called()
```

## 🔍 Monitoring

### Cache Metrics

Track these metrics for cache performance:

```python
# Add to your monitoring system
cache_hit_rate = cache_hits / (cache_hits + cache_misses)
cache_eviction_rate = cache_evictions / total_cache_operations
average_response_time = sum(response_times) / len(response_times)
```

### Logging

The services automatically log cache operations:

```python
# Cache operations are logged with activity_logger
await self.activity_logger.log_activity(
    user_id=user_id,
    action="cache_invalidation",
    details={"cache_patterns": cache_patterns}
)
```

## 🚨 Error Handling

### Cache Fallback Strategy

Both services implement graceful fallback:

```python
# If cache fails, fall back to database
try:
    cached_data = await self.cache.get(cache_key)
    if cached_data:
        return cached_data
except Exception:
    # Log error but continue with database query
    pass

# Always have database fallback
return await self.get_from_database(user_id)
```

### Cache Invalidation Errors

If cache invalidation fails, the system continues normally:

```python
try:
    await self._invalidate_user_cache(user_id)
except Exception as e:
    # Log error but don't fail the operation
    logger.error(f"Cache invalidation failed: {e}")
```

## 📝 Migration Guide

### From Original Services

1. **Replace service imports**:
```python
# Before
from src.services.user_service import UserService
from src.services.achievement_service import AchievementService

# After
from src.services.cached_user_service import CachedUserService
from src.services.cached_achievement_service import CachedAchievementService
```

2. **Update route dependencies**:
```python
# Before
user_service: UserService = Depends(get_user_service)

# After
user_service: CachedUserService = Depends(get_cached_user_service)
```

3. **Add background_tasks parameter**:
```python
# Before
user = await user_service.get_user_by_id(user_id)

# After
user = await user_service.get_user_by_id_cached(user_id, background_tasks)
```

## 🎯 Best Practices

1. **Always use background_tasks**: Enables cache warming and better performance
2. **Monitor cache hit rates**: Aim for >80% hit rate for user data
3. **Use appropriate TTL**: Balance between data freshness and performance
4. **Implement graceful fallback**: Always have database fallback for cache failures
5. **Log cache operations**: Monitor cache performance and debug issues
6. **Regular cache cleanup**: Monitor Redis memory usage and implement cleanup
7. **Test cache invalidation**: Ensure data consistency after updates

## 🔄 Rollback Plan

If issues arise, you can easily rollback:

1. **Switch back to original routes** in `main.py`
2. **Keep both services running** during transition period
3. **Monitor error rates** and performance metrics
4. **Use feature flags** to gradually enable caching

This implementation provides a robust, scalable caching solution that significantly improves performance while maintaining data consistency through proper cache invalidation mechanisms.