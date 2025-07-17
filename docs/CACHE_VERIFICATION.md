# Cache Verification Guide

## Quick Steps to Verify Caching is Working

### 1. Check Backend Logs (Simplest Method)

**Before caching (what you saw):**
```
INFO:     GET /api/v1/users/profile
SQL query: SELECT users.id, users.email, users.name... FROM users WHERE users.id = $1
SQL query: SELECT user_preferences.* FROM user_preferences WHERE user_preferences.user_id = $1
```

**After caching (what you should see now):**
```
INFO:     GET /api/v1/users/profile
# First call - should still show SQL
SQL query: SELECT users.id, users.email, users.name... FROM users WHERE users.id = $1

INFO:     GET /api/v1/users/profile  
# Second call - should NOT show SQL (cache hit)
```

### 2. Check Redis Cache Keys

**Method 1: Redis CLI**
```bash
redis-cli
> KEYS katiba360:*
> TTL katiba360:user:{user-id}:profile
```

**Method 2: Redis Browser Tool**
- Use Redis Desktop Manager or RedisInsight
- Look for keys starting with `katiba360:`

### 3. Performance Testing

**Manual Test:**
1. Open browser dev tools → Network tab
2. Go to /profile page
3. Check response time for first load
4. Refresh page immediately
5. Second load should be faster

**Expected Cache Keys:**
```
katiba360:user:{user-id}:profile
katiba360:achievements:{user-id}:achievements
katiba360:constitution:user:{user-id}:bookmarks
katiba360:constitution:user:{user-id}:progress
```

### 4. Verify Cache Invalidation

**Test Steps:**
1. Load profile page (cache populated)
2. Update profile (name, bio, etc.)
3. Refresh profile page
4. Should see SQL in logs again (cache invalidated)

### 5. Check Cache Headers (Optional)

Add this to your route temporarily:
```python
return generate_response(
    status_code=status.HTTP_200_OK,
    response_message="User profile retrieved successfully",
    customer_message="Your profile has been retrieved",
    body={
        # ... existing data ...
        "cache_debug": {
            "cache_hit": cached_data is not None,
            "cache_key": f"user:{user.id}:profile"
        }
    }
)
```

## Troubleshooting

### If You Still See SQL Logs:

**1. Check Redis Connection:**
```bash
redis-cli ping
# Should return PONG
```

**2. Check Backend Configuration:**
```python
# In settings.py or config.py
REDIS_URL = "redis://localhost:6379/0"
```

**3. Verify Route is Using Cached Service:**
```python
# user_routes.py should import and use:
from src.services.cached_user_service import CachedUserService
user_service: CachedUserService = Depends(get_cached_user_service)
```

**4. Check for Import Errors:**
```bash
# Check backend startup logs for import errors
python -m uvicorn main:app --reload
```

### Common Issues:

**Issue 1: Redis Not Running**
```bash
# Start Redis
redis-server

# Or with Docker
docker run -d -p 6379:6379 redis:alpine
```

**Issue 2: Cache Manager Not Working**
```python
# Add debug logging in cached service
async def get_user_by_id_cached(self, user_id: uuid.UUID, ...):
    cache_key = self._get_cache_key("profile", str(user_id))
    print(f"DEBUG: Checking cache key: {cache_key}")
    
    cached_user = await self.cache.get(cache_key)
    print(f"DEBUG: Cache hit: {cached_user is not None}")
    
    # ... rest of method
```

**Issue 3: Background Tasks Not Working**
```python
# Make sure BackgroundTasks is imported and used
from fastapi import BackgroundTasks

@router.get("/profile")
async def get_user_profile(
    background_tasks: BackgroundTasks,  # ← This is required
    # ... other deps
):
```

## Quick Test Script

Save this as `quick_cache_test.py`:

```python
import requests
import time

# Replace with your actual token
TOKEN = "your_jwt_token_here"
BASE_URL = "http://localhost:8000"

headers = {"Authorization": f"Bearer {TOKEN}"}

# Test 1: Profile endpoint
print("Testing /api/v1/users/profile")
start = time.time()
r1 = requests.get(f"{BASE_URL}/api/v1/users/profile", headers=headers)
first_time = time.time() - start
print(f"First call: {first_time:.3f}s")

start = time.time()
r2 = requests.get(f"{BASE_URL}/api/v1/users/profile", headers=headers)
second_time = time.time() - start
print(f"Second call: {second_time:.3f}s")

if second_time < first_time:
    print("✅ Caching working!")
else:
    print("❌ Caching not working")

# Test 2: Achievements endpoint
print("\nTesting /api/v1/achievements")
start = time.time()
r3 = requests.get(f"{BASE_URL}/api/v1/achievements", headers=headers)
first_time = time.time() - start
print(f"First call: {first_time:.3f}s")

start = time.time()
r4 = requests.get(f"{BASE_URL}/api/v1/achievements", headers=headers)
second_time = time.time() - start
print(f"Second call: {second_time:.3f}s")

if second_time < first_time:
    print("✅ Caching working!")
else:
    print("❌ Caching not working")
```

## Expected Results

**✅ SUCCESS - Caching Working:**
- First API call: Shows SQL in logs + slower response
- Second API call: No SQL in logs + faster response
- Redis contains cache keys
- Performance improvement of 50-80%

**❌ FAILURE - Caching Not Working:**
- Every API call shows SQL in logs
- No performance improvement
- No cache keys in Redis
- Import or configuration errors in logs

## Next Steps

Once caching is confirmed working:

1. **Monitor Performance**: Track response times and cache hit rates
2. **Adjust TTL**: Tune cache expiration times based on usage
3. **Add More Endpoints**: Cache other frequently accessed endpoints
4. **Set Up Monitoring**: Use tools like Redis Monitor or custom metrics

The key indicator is **reduced SQL queries in logs** for subsequent requests to the same endpoint.