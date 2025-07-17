#!/usr/bin/env python3
"""
Test script for Content Views Analytics implementation
"""
import asyncio
import uuid
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import async_session, Base, engine
from src.models.user_models import ContentView, User
from src.services.constitution_service import ConstitutionData
from src.utils.cache import CacheManager


async def test_content_views():
    """Test the content views analytics functionality"""
    print("Testing Content Views Analytics...")
    
    # Create test data
    async with async_session() as db_session:
        # Create a test user
        test_user = User(
            email="test@example.com",
            display_name="Test User",
            email_verified=True
        )
        db_session.add(test_user)
        await db_session.commit()
        await db_session.refresh(test_user)
        
        # Create some test content views
        views = [
            ContentView(
                content_type="chapter",
                content_reference="1",
                user_id=test_user.id,
                view_count=5,
                first_viewed_at=datetime.now() - timedelta(days=2),
                last_viewed_at=datetime.now() - timedelta(hours=1),
                device_type="desktop"
            ),
            ContentView(
                content_type="article",
                content_reference="1.2",
                user_id=test_user.id,
                view_count=3,
                first_viewed_at=datetime.now() - timedelta(days=1),
                last_viewed_at=datetime.now() - timedelta(minutes=30),
                device_type="mobile"
            ),
            ContentView(
                content_type="chapter",
                content_reference="2",
                user_id=None,  # Anonymous view
                view_count=2,
                first_viewed_at=datetime.now() - timedelta(hours=3),
                last_viewed_at=datetime.now() - timedelta(hours=2),
                device_type="tablet",
                ip_address="192.168.1.100"
            ),
            ContentView(
                content_type="search",
                content_reference="human rights",
                user_id=test_user.id,
                view_count=1,
                first_viewed_at=datetime.now() - timedelta(minutes=15),
                last_viewed_at=datetime.now() - timedelta(minutes=15),
                device_type="mobile"
            )
        ]
        
        for view in views:
            db_session.add(view)
        
        await db_session.commit()
        print(f"Created {len(views)} test content views")
        
        # Test the analytics methods
        cache_manager = CacheManager()
        constitution_data = ConstitutionData(cache_manager)
        constitution_data.db_session = db_session
        
        # Test get_popular_content_from_db
        print("\n--- Testing get_popular_content_from_db ---")
        popular_content = await constitution_data.get_popular_content_from_db(
            timeframe="daily",
            limit=10
        )
        print(f"Popular content (daily): {popular_content}")
        
        # Test get_view_trends
        print("\n--- Testing get_view_trends ---")
        trends = await constitution_data.get_view_trends(days=7)
        print(f"View trends (7 days): {trends}")
        
        # Test get_user_view_history
        print("\n--- Testing get_user_view_history ---")
        history = await constitution_data.get_user_view_history(str(test_user.id))
        print(f"User view history: {history}")
        
        # Test get_analytics_summary
        print("\n--- Testing get_analytics_summary ---")
        summary = await constitution_data.get_analytics_summary(timeframe="daily")
        print(f"Analytics summary: {summary}")
        
        # Clean up test data
        await db_session.delete(test_user)
        for view in views:
            await db_session.delete(view)
        await db_session.commit()
        
        print("\nTest completed successfully!")


if __name__ == "__main__":
    asyncio.run(test_content_views())