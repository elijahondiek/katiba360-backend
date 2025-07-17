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
from src.models.user_models import User, ReadingHistory
from src.utils.logging.activity_logger import ActivityLogger
from src.utils.cache import CacheManager, HOUR, DAY
from src.core.config import settings
from src.services.constitution import ConstitutionOrchestrator

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
        # Initialize constitution orchestrator with redis client
        from redis.asyncio import Redis
        redis_client = cache.redis  # Get redis client from cache manager
        self.constitution_service = ConstitutionOrchestrator(redis_client, db)
    
    def _count_content_words(self, content: str) -> int:
        """
        Count words in a given content string.
        
        Args:
            content: The content string to count words in
            
        Returns:
            int: Number of words in the content
        """
        if not content:
            return 0
        
        # Simple word counting - split by whitespace and filter empty strings
        words = [word for word in content.split() if word.strip()]
        return len(words)
    
    async def _calculate_chapter_word_count(self, chapter_number: int) -> int:
        """
        Calculate the total word count for a chapter including all its articles.
        
        Args:
            chapter_number: The chapter number
            
        Returns:
            int: Total word count for the chapter
        """
        try:
            # Get chapter data from constitution service
            chapter_data = await self.constitution_service.get_chapter_by_number(chapter_number)
            
            if not chapter_data:
                logger.warning(f"No data found for chapter {chapter_number}")
                return 0
            
            total_words = 0
            
            # Count words in chapter title
            if chapter_data.get('chapter_title'):
                total_words += self._count_content_words(chapter_data['chapter_title'])
            
            # Count words in all articles
            articles = chapter_data.get('articles', [])
            for article in articles:
                # Count words in article title
                if article.get('article_title'):
                    total_words += self._count_content_words(article['article_title'])
                
                # Count words in all clauses
                clauses = article.get('clauses', [])
                for clause in clauses:
                    # Count words in clause content
                    if clause.get('content'):
                        total_words += self._count_content_words(clause['content'])
                    
                    # Count words in sub-clauses
                    sub_clauses = clause.get('sub_clauses', [])
                    for sub_clause in sub_clauses:
                        if sub_clause.get('content'):
                            total_words += self._count_content_words(sub_clause['content'])
            
            logger.info(f"Chapter {chapter_number} has {total_words} words")
            return total_words
            
        except Exception as e:
            logger.error(f"Error calculating word count for chapter {chapter_number}: {e}")
            return 0
    
    async def _calculate_article_word_count(self, chapter_number: int, article_number: int) -> int:
        """
        Calculate the total word count for a specific article.
        
        Args:
            chapter_number: The chapter number
            article_number: The article number
            
        Returns:
            int: Total word count for the article
        """
        try:
            # Get article data from constitution service
            article_data = await self.constitution_service.get_article_by_number(chapter_number, article_number)
            
            if not article_data:
                logger.warning(f"No data found for article {chapter_number}.{article_number}")
                return 0
            
            total_words = 0
            
            # Count words in article title
            if article_data.get('article_title'):
                total_words += self._count_content_words(article_data['article_title'])
            
            # Count words in all clauses
            clauses = article_data.get('clauses', [])
            for clause in clauses:
                # Count words in clause content
                if clause.get('content'):
                    total_words += self._count_content_words(clause['content'])
                
                # Count words in sub-clauses
                sub_clauses = clause.get('sub_clauses', [])
                for sub_clause in sub_clauses:
                    if sub_clause.get('content'):
                        total_words += self._count_content_words(sub_clause['content'])
            
            logger.info(f"Article {chapter_number}.{article_number} has {total_words} words")
            return total_words
            
        except Exception as e:
            logger.error(f"Error calculating word count for article {chapter_number}.{article_number}: {e}")
            return 0
    
    async def _calculate_completion_threshold(self, item_type: str, reference: str) -> float:
        """
        Calculate the completion threshold in minutes based on content length.
        
        Args:
            item_type: The type of item ('chapter' or 'article')
            reference: The reference string (e.g., '1' for chapter 1, '1.2' for article 2)
            
        Returns:
            float: Completion threshold in minutes
        """
        try:
            # Default reading speed: 200 words per minute
            reading_speed_wpm = 200
            
            # Completion threshold: 30% of estimated reading time
            completion_percentage = 0.3
            
            # Minimum threshold: 2 minutes (current system minimum)
            min_threshold = 2.0
            
            word_count = 0
            
            if item_type == "chapter":
                chapter_number = int(reference)
                word_count = await self._calculate_chapter_word_count(chapter_number)
            elif item_type == "article":
                # Parse reference like "1.2" to get chapter and article numbers
                parts = reference.split('.')
                if len(parts) == 2:
                    chapter_number = int(parts[0])
                    article_number = int(parts[1])
                    word_count = await self._calculate_article_word_count(chapter_number, article_number)
            
            if word_count == 0:
                logger.warning(f"No words found for {item_type} {reference}, using minimum threshold")
                return min_threshold
            
            # Calculate estimated reading time in minutes
            estimated_reading_time = word_count / reading_speed_wpm
            
            # Calculate completion threshold (30% of estimated time)
            threshold = estimated_reading_time * completion_percentage
            
            # Ensure minimum threshold
            threshold = max(threshold, min_threshold)
            
            logger.info(f"{item_type} {reference}: {word_count} words, estimated {estimated_reading_time:.1f} min, threshold {threshold:.1f} min")
            return threshold
            
        except Exception as e:
            logger.error(f"Error calculating completion threshold for {item_type} {reference}: {e}")
            return min_threshold
    
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
                                          read_time_minutes: float = 1.0, 
                                          background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """
        Update reading progress for a specific user.
        
        Args:
            user_id: The user ID
            item_type: The type of item (chapter, article)
            reference: The reference (e.g., "1" for chapter 1, "1.2" for article 2 in chapter 1)
            read_time_minutes: The time spent reading in minutes (supports decimals)
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
                
                # Calculate dynamic completion threshold based on content length
                completion_threshold = await self._calculate_completion_threshold(item_type, reference)
                
                # Mark as completed if it meets the content-aware threshold
                if existing_entry.read_time_minutes >= completion_threshold:
                    existing_entry.is_completed = True
                    logger.info(f"Marked {item_type} {reference} as completed (threshold: {completion_threshold:.1f} min, read: {existing_entry.read_time_minutes:.1f} min)")
                
                # Create ReadingHistory entry
                reading_history = ReadingHistory(
                    user_id=uuid.UUID(user_id),
                    content_id=reference,
                    content_type=item_type,
                    reading_time_minutes=read_time_minutes,
                    time_spent_seconds=int(read_time_minutes * 60),
                    read_at=datetime.now(timezone.utc),
                    started_at=datetime.now(timezone.utc),
                    position=0.0,
                    total_length=1.0,
                    progress_percentage=0.0
                )
                self.db.add(reading_history)
                
                await self.db.commit()
                logger.info(f"Updated reading progress for user {user_id}, {item_type} {reference}")
            else:
                # Calculate dynamic completion threshold based on content length
                completion_threshold = await self._calculate_completion_threshold(item_type, reference)
                
                # Create new entry
                is_completed = read_time_minutes >= completion_threshold
                new_entry = UserReadingProgress(
                    user_id=uuid.UUID(user_id),
                    item_type=item_type,
                    reference=reference,
                    read_time_minutes=read_time_minutes,
                    is_completed=is_completed,
                    first_read_at=datetime.now(timezone.utc),
                    last_read_at=datetime.now(timezone.utc)
                )
                self.db.add(new_entry)
                
                # Create ReadingHistory entry
                reading_history = ReadingHistory(
                    user_id=uuid.UUID(user_id),
                    content_id=reference,
                    content_type=item_type,
                    reading_time_minutes=read_time_minutes,
                    time_spent_seconds=int(read_time_minutes * 60),
                    read_at=datetime.now(timezone.utc),
                    started_at=datetime.now(timezone.utc),
                    position=0.0,
                    total_length=1.0,
                    progress_percentage=0.0
                )
                self.db.add(reading_history)
                
                await self.db.commit()
                
                if is_completed:
                    logger.info(f"Created and marked {item_type} {reference} as completed (threshold: {completion_threshold:.1f} min, read: {read_time_minutes:.1f} min)")
                else:
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
