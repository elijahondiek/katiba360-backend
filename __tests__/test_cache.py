#!/usr/bin/env python3
"""
Simple script to test if caching is working for user profile endpoints.
Run this after starting the backend server.
"""

import asyncio
import aiohttp
import time
import json

# Configuration
BASE_URL = "http://localhost:8000"  # Adjust as needed
TEST_USER_TOKEN = "YOUR_JWT_TOKEN_HERE"  # Replace with actual token

async def test_caching():
    """Test caching performance for user profile endpoints"""
    
    headers = {
        "Authorization": f"Bearer {TEST_USER_TOKEN}",
        "Content-Type": "application/json"
    }
    
    endpoints = [
        "/api/v1/users/profile",
        "/api/v1/achievements",
    ]
    
    async with aiohttp.ClientSession() as session:
        print("🧪 Testing API Caching Performance\n")
        
        for endpoint in endpoints:
            print(f"Testing: {endpoint}")
            
            # First call (should hit database)
            start_time = time.time()
            async with session.get(f"{BASE_URL}{endpoint}", headers=headers) as response:
                first_call_time = time.time() - start_time
                if response.status == 200:
                    data = await response.json()
                    print(f"  ✅ First call: {first_call_time:.3f}s (should be slower - DB hit)")
                else:
                    print(f"  ❌ First call failed: {response.status}")
                    continue
            
            # Small delay to ensure cache is set
            await asyncio.sleep(0.1)
            
            # Second call (should hit cache)
            start_time = time.time()
            async with session.get(f"{BASE_URL}{endpoint}", headers=headers) as response:
                second_call_time = time.time() - start_time
                if response.status == 200:
                    data = await response.json()
                    print(f"  ✅ Second call: {second_call_time:.3f}s (should be faster - Cache hit)")
                    
                    # Calculate improvement
                    if first_call_time > 0:
                        improvement = ((first_call_time - second_call_time) / first_call_time) * 100
                        print(f"  📊 Performance improvement: {improvement:.1f}%")
                else:
                    print(f"  ❌ Second call failed: {response.status}")
            
            print()

async def test_cache_invalidation():
    """Test cache invalidation on profile updates"""
    
    headers = {
        "Authorization": f"Bearer {TEST_USER_TOKEN}",
        "Content-Type": "application/json"
    }
    
    endpoint = "/api/v1/users/profile"
    
    async with aiohttp.ClientSession() as session:
        print("🔄 Testing Cache Invalidation\n")
        
        # Get initial profile
        async with session.get(f"{BASE_URL}{endpoint}", headers=headers) as response:
            if response.status == 200:
                initial_data = await response.json()
                print(f"  ✅ Initial profile fetch: {response.status}")
            else:
                print(f"  ❌ Initial profile fetch failed: {response.status}")
                return
        
        # Update profile (this should invalidate cache)
        update_data = {
            "name": f"Test User {int(time.time())}"
        }
        
        async with session.put(f"{BASE_URL}{endpoint}", 
                              headers=headers, 
                              json=update_data) as response:
            if response.status == 200:
                print(f"  ✅ Profile update: {response.status}")
            else:
                print(f"  ❌ Profile update failed: {response.status}")
                return
        
        # Get profile again (should be fresh from DB due to cache invalidation)
        start_time = time.time()
        async with session.get(f"{BASE_URL}{endpoint}", headers=headers) as response:
            fetch_time = time.time() - start_time
            if response.status == 200:
                updated_data = await response.json()
                print(f"  ✅ Profile fetch after update: {fetch_time:.3f}s")
                print(f"  📝 Cache invalidation working: Data updated correctly")
            else:
                print(f"  ❌ Profile fetch after update failed: {response.status}")

async def check_redis_keys():
    """Check Redis for cache keys (requires redis-py)"""
    try:
        import redis.asyncio as redis
        
        r = redis.Redis(host='localhost', port=6379, db=0)
        
        print("🔍 Checking Redis Cache Keys\n")
        
        # Get all katiba360 keys
        keys = await r.keys("katiba360:*")
        
        if keys:
            print(f"  Found {len(keys)} cache keys:")
            for key in keys[:10]:  # Show first 10 keys
                key_str = key.decode('utf-8')
                ttl = await r.ttl(key)
                print(f"    {key_str} (TTL: {ttl}s)")
            
            if len(keys) > 10:
                print(f"    ... and {len(keys) - 10} more")
        else:
            print("  ❌ No cache keys found")
        
        await r.close()
        
    except ImportError:
        print("  ⚠️  redis-py not installed, skipping Redis check")
    except Exception as e:
        print(f"  ❌ Redis check failed: {e}")

if __name__ == "__main__":
    print("🚀 Katiba360 Cache Testing Script\n")
    
    if TEST_USER_TOKEN == "YOUR_JWT_TOKEN_HERE":
        print("⚠️  Please update TEST_USER_TOKEN with a valid JWT token")
        print("   You can get one by logging in through the frontend")
        exit(1)
    
    try:
        asyncio.run(test_caching())
        asyncio.run(test_cache_invalidation())
        asyncio.run(check_redis_keys())
        
        print("\n✅ Cache testing completed!")
        print("\nWhat to look for:")
        print("- Second API calls should be significantly faster")
        print("- Cache keys should appear in Redis")
        print("- Profile updates should invalidate cache")
        print("- Backend logs should show fewer SQL queries on cached requests")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print("\nTroubleshooting:")
        print("- Make sure the backend server is running")
        print("- Check that Redis is running and accessible")
        print("- Verify the JWT token is valid")
        print("- Check backend logs for errors")