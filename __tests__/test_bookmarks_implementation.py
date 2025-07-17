"""
Test script to verify the bookmark implementation works correctly.
This script tests the database operations for bookmarks.
"""

import asyncio
import sys
import os
import uuid
from datetime import datetime

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.database import get_async_session
from src.services.constitution_service import ConstitutionService
from src.utils.cache import CacheManager
from src.models.user_models import User, Bookmark
from sqlalchemy import select
from redis.asyncio import Redis

async def test_bookmark_operations():
    """Test all bookmark operations."""
    print("🧪 Testing Bookmark Implementation...")
    
    # Initialize dependencies
    redis_client = Redis.from_url("redis://localhost:6379")
    cache_manager = CacheManager(redis_client, prefix="katiba360_test")
    
    # Get database session
    async with get_async_session() as db_session:
        # Initialize the service
        service = ConstitutionService(cache_manager, db_session)
        
        # Create test user UUID
        test_user_id = str(uuid.uuid4())
        print(f"📝 Using test user ID: {test_user_id}")
        
        # Test 1: Get bookmarks for new user (should return empty list)
        print("\n🔍 Test 1: Get bookmarks for new user")
        bookmarks = await service.get_user_bookmarks(test_user_id)
        assert len(bookmarks) == 0, f"Expected 0 bookmarks, got {len(bookmarks)}"
        print("✅ New user has no bookmarks")
        
        # Test 2: Add a valid chapter bookmark
        print("\n🔍 Test 2: Add chapter bookmark")
        result = await service.add_user_bookmark(
            test_user_id, 
            "chapter", 
            "1", 
            "Sovereignty of the People and Supremacy of the Constitution"
        )
        assert result["success"] == True, f"Expected success, got {result}"
        print("✅ Chapter bookmark added successfully")
        
        # Test 3: Add a valid article bookmark
        print("\n🔍 Test 3: Add article bookmark")
        result = await service.add_user_bookmark(
            test_user_id, 
            "article", 
            "2.19", 
            "Rights and Fundamental Freedoms"
        )
        assert result["success"] == True, f"Expected success, got {result}"
        print("✅ Article bookmark added successfully")
        
        # Test 4: Try to add duplicate bookmark (should fail)
        print("\n🔍 Test 4: Add duplicate bookmark (should fail)")
        result = await service.add_user_bookmark(
            test_user_id, 
            "chapter", 
            "1", 
            "Sovereignty of the People and Supremacy of the Constitution"
        )
        assert result["success"] == False, f"Expected failure for duplicate, got {result}"
        assert "already exists" in result["message"], f"Expected 'already exists' message, got {result['message']}"
        print("✅ Duplicate bookmark correctly rejected")
        
        # Test 5: Add bookmark with invalid type (should fail)
        print("\n🔍 Test 5: Add bookmark with invalid type")
        result = await service.add_user_bookmark(
            test_user_id, 
            "invalid_type", 
            "1", 
            "Test Title"
        )
        assert result["success"] == False, f"Expected failure for invalid type, got {result}"
        assert "Invalid bookmark type" in result["message"], f"Expected validation error, got {result['message']}"
        print("✅ Invalid bookmark type correctly rejected")
        
        # Test 6: Add bookmark with invalid reference format (should fail)
        print("\n🔍 Test 6: Add bookmark with invalid reference")
        result = await service.add_user_bookmark(
            test_user_id, 
            "article", 
            "invalid_ref", 
            "Test Title"
        )
        assert result["success"] == False, f"Expected failure for invalid reference, got {result}"
        assert "Invalid reference format" in result["message"], f"Expected validation error, got {result['message']}"
        print("✅ Invalid reference format correctly rejected")
        
        # Test 7: Add bookmark with empty title (should fail)
        print("\n🔍 Test 7: Add bookmark with empty title")
        result = await service.add_user_bookmark(
            test_user_id, 
            "chapter", 
            "2", 
            ""
        )
        assert result["success"] == False, f"Expected failure for empty title, got {result}"
        assert "Title cannot be empty" in result["message"], f"Expected validation error, got {result['message']}"
        print("✅ Empty title correctly rejected")
        
        # Test 8: Get bookmarks (should return 2 bookmarks)
        print("\n🔍 Test 8: Get bookmarks after adding some")
        bookmarks = await service.get_user_bookmarks(test_user_id)
        assert len(bookmarks) == 2, f"Expected 2 bookmarks, got {len(bookmarks)}"
        print("✅ Correct number of bookmarks retrieved")
        
        # Verify bookmark structure
        for bookmark in bookmarks:
            assert "id" in bookmark, "Bookmark missing id field"
            assert "bookmark_id" in bookmark, "Bookmark missing bookmark_id field"
            assert "type" in bookmark, "Bookmark missing type field"
            assert "reference" in bookmark, "Bookmark missing reference field"
            assert "title" in bookmark, "Bookmark missing title field"
            assert "created_at" in bookmark, "Bookmark missing created_at field"
            assert "updated_at" in bookmark, "Bookmark missing updated_at field"
        print("✅ Bookmark structure is correct")
        
        # Test 9: Remove a bookmark
        print("\n🔍 Test 9: Remove a bookmark")
        bookmark_to_remove = bookmarks[0]
        result = await service.remove_user_bookmark(test_user_id, bookmark_to_remove["id"])
        assert result["success"] == True, f"Expected success removing bookmark, got {result}"
        print("✅ Bookmark removed successfully")
        
        # Test 10: Verify bookmark was removed
        print("\n🔍 Test 10: Verify bookmark was removed")
        bookmarks = await service.get_user_bookmarks(test_user_id)
        assert len(bookmarks) == 1, f"Expected 1 bookmark after removal, got {len(bookmarks)}"
        print("✅ Bookmark count correct after removal")
        
        # Test 11: Try to remove non-existent bookmark
        print("\n🔍 Test 11: Remove non-existent bookmark")
        fake_bookmark_id = str(uuid.uuid4())
        result = await service.remove_user_bookmark(test_user_id, fake_bookmark_id)
        assert result["success"] == False, f"Expected failure for non-existent bookmark, got {result}"
        assert "not found" in result["message"], f"Expected 'not found' message, got {result['message']}"
        print("✅ Non-existent bookmark removal correctly handled")
        
        # Test 12: Try to remove bookmark with invalid UUID
        print("\n🔍 Test 12: Remove bookmark with invalid UUID")
        result = await service.remove_user_bookmark(test_user_id, "invalid_uuid")
        assert result["success"] == False, f"Expected failure for invalid UUID, got {result}"
        assert "Invalid input" in result["message"], f"Expected validation error, got {result['message']}"
        print("✅ Invalid UUID correctly rejected")
        
        # Clean up: Remove remaining bookmarks
        print("\n🧹 Cleaning up test data...")
        remaining_bookmarks = await service.get_user_bookmarks(test_user_id)
        for bookmark in remaining_bookmarks:
            await service.remove_user_bookmark(test_user_id, bookmark["id"])
        
        # Verify cleanup
        final_bookmarks = await service.get_user_bookmarks(test_user_id)
        assert len(final_bookmarks) == 0, f"Expected 0 bookmarks after cleanup, got {len(final_bookmarks)}"
        print("✅ Cleanup completed successfully")
        
    # Close Redis connection
    await redis_client.close()
    
    print("\n🎉 All tests passed! Bookmark implementation is working correctly.")

if __name__ == "__main__":
    asyncio.run(test_bookmark_operations())