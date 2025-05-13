from typing import Optional, List, Dict, Any, Union
import uuid
from datetime import datetime, date, timedelta, timezone
from fastapi import HTTPException, status, Depends, BackgroundTasks
from sqlalchemy import select, func, update, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from redis.asyncio import Redis

from src.database import get_db
from src.models.reading_progress import UserReadingProgress
from src.models.user_models import User
from src.utils.logging.activity_logger import ActivityLogger
from src.utils.cache import CacheManager, HOUR, DAY
from src.core.config import settings

import logging
logger = logging.getLogger(__name__)

# Cache key constants
CACHE_KEY_USER_PROGRESS_PREFIX = "constitution:user:"

class ReadingProgressService:
    """
    Service for handling user reading progress operations.
    """
    
    def __init__(self, db: AsyncSession, cache: CacheManager):
        self.db = db
        self.cache = cache
        self.activity_logger = ActivityLogger()
    
    async def get_user_reading_progress(self, user_id: str, background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """
        Get reading progress for a specific user.
        
        Args:
            user_id: The user ID
            background_tasks: Optional background tasks for async caching
            
        Returns:
            Dict: User reading progress
        """
        # Generate cache key for user reading progress
        cache_key = f"{CACHE_KEY_USER_PROGRESS_PREFIX}{user_id}:progress"
        
        # Try to get from cache first
        cached_progress = await self.cache.get(cache_key)
        if cached_progress:
            logger.info(f"Reading progress for user {user_id} retrieved from cache")
            return cached_progress
        
        # If not in cache, get from database
        try:
            # Query for all reading progress entries for this user
            query = select(UserReadingProgress).where(
                UserReadingProgress.user_id == uuid.UUID(user_id)
            )
            result = await self.db.execute(query)
            progress_entries = result.scalars().all()
            
            # Calculate last read item
            last_read_item = None
            if progress_entries:
                # Find the entry with the most recent last_read_at
                last_entry = max(progress_entries, key=lambda x: x.last_read_at)
                last_read_item = {
                    "type": last_entry.item_type,
                    "reference": last_entry.reference,
                    "timestamp": last_entry.last_read_at.isoformat()
                }
            
            # Calculate completed chapters and articles
            completed_chapters = []
            completed_articles = []
            total_read_time_minutes = 0
            
            for entry in progress_entries:
                total_read_time_minutes += entry.read_time_minutes
                
                if entry.is_completed:
                    if entry.item_type == "chapter":
                        completed_chapters.append(entry.reference)
                    elif entry.item_type == "article":
                        completed_articles.append(entry.reference)
            
            # Construct the progress object
            progress = {
                "last_read": last_read_item or {
                    "type": None,
                    "reference": None,
                    "timestamp": None
                },
                "completed_chapters": completed_chapters,
                "completed_articles": completed_articles,
                "total_read_time_minutes": total_read_time_minutes
            }
            
            # Cache the reading progress
            if background_tasks:
                await self.cache.set_background(
                    background_tasks,
                    cache_key,
                    progress,
                    expire=HOUR  # Cache for 1 hour
                )
            else:
                await self.cache.set(
                    cache_key,
                    progress,
                    expire=HOUR  # Cache for 1 hour
                )
            
            return progress
            
        except Exception as e:
            logger.error(f"Error retrieving reading progress for user {user_id}: {e}")
            # Return default progress structure on error
            return {
                "last_read": {
                    "type": None,
                    "reference": None,
                    "timestamp": None
                },
                "completed_chapters": [],
                "completed_articles": [],
                "total_read_time_minutes": 0
            }
    
    async def update_user_reading_progress(self, user_id: str, item_type: str, reference: str, 
                                          read_time_minutes: int = 1, 
                                          background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """
        Update reading progress for a specific user.
        
        Args:
            user_id: The user ID
            item_type: The type of item (chapter, article)
            reference: The reference (e.g., "1" for chapter 1, "1.2" for article 2 in chapter 1)
            read_time_minutes: The time spent reading in minutes
            background_tasks: Optional background tasks for async caching
            
        Returns:
            Dict: Updated reading progress
        """
        try:
            # Check if an entry already exists for this item
            query = select(UserReadingProgress).where(
                and_(
                    UserReadingProgress.user_id == uuid.UUID(user_id),
                    UserReadingProgress.item_type == item_type,
                    UserReadingProgress.reference == reference
                )
            )
            result = await self.db.execute(query)
            existing_entry = result.scalars().first()
            
            if existing_entry:
                # Update existing entry
                existing_entry.read_time_minutes += read_time_minutes
                existing_entry.total_views += 1
                existing_entry.last_read_at = datetime.now(timezone.utc)
                
                # Mark as completed if it's a significant reading time
                if existing_entry.read_time_minutes >= 2:  # Consider completed if read for 2+ minutes
                    existing_entry.is_completed = True
                
                await self.db.commit()
                logger.info(f"Updated reading progress for user {user_id}, {item_type} {reference}")
            else:
                # Create new entry
                new_entry = UserReadingProgress(
                    user_id=uuid.UUID(user_id),
                    item_type=item_type,
                    reference=reference,
                    read_time_minutes=read_time_minutes,
                    is_completed=(read_time_minutes >= 2),  # Consider completed if read for 2+ minutes
                    first_read_at=datetime.now(timezone.utc),
                    last_read_at=datetime.now(timezone.utc)
                )
                self.db.add(new_entry)
                await self.db.commit()
                logger.info(f"Created new reading progress for user {user_id}, {item_type} {reference}")
            
            # Invalidate cache
            cache_key = f"{CACHE_KEY_USER_PROGRESS_PREFIX}{user_id}:progress"
            await self.cache.delete(cache_key)
            
            # Get updated progress
            return await self.get_user_reading_progress(user_id, background_tasks)
            
        except Exception as e:
            logger.error(f"Error updating reading progress for user {user_id}: {e}")
            await self.db.rollback()
            raise

# Cache manager dependency
async def get_reading_progress_cache():
    # Get Redis client using the URL from settings
    redis_client = Redis.from_url(settings.redis_url)
    
    # Create cache manager
    cache_manager = CacheManager(redis_client, prefix="katiba360")
    
    try:
        yield cache_manager
    finally:
        await redis_client.close()

# Dependency to get reading progress service
async def get_reading_progress_service(
    db: AsyncSession = Depends(get_db),
    cache: CacheManager = Depends(get_reading_progress_cache)
):
    return ReadingProgressService(db, cache)
