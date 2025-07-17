"""
Reading progress manager for constitution content.
Handles user reading progress tracking and management.
"""

import uuid
from typing import Dict, List, Optional
from datetime import datetime
from fastapi import BackgroundTasks
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..base import BaseService, ConstitutionCacheManager
from ....utils.cache import HOUR
from ....models.reading_progress import UserReadingProgress


class ReadingProgressManager(BaseService):
    """
    Service for managing user reading progress.
    Handles progress tracking, completion status, and reading statistics.
    """
    
    def __init__(self, cache_manager: ConstitutionCacheManager, 
                 db_session: Optional[AsyncSession] = None):
        """
        Initialize the reading progress manager.
        
        Args:
            cache_manager: Cache manager instance
            db_session: Database session
        """
        super().__init__(cache_manager, db_session)
    
    def get_service_name(self) -> str:
        """Get the service name."""
        return "reading_progress"
    
    async def get_user_reading_progress(self, user_id: str,
                                       background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """
        Get comprehensive reading progress for a user.
        
        Args:
            user_id: User ID
            background_tasks: Optional background tasks
            
        Returns:
            Dict: User reading progress
        """
        try:
            # Validate user ID
            user_id = self.validator.validate_user_id(user_id)
            
            # Check cache first
            cached_progress = await self.cache.get_user_progress(user_id)
            if cached_progress:
                return cached_progress
            
            # Get from database
            progress = await self._get_progress_from_database(user_id)
            
            # Cache the progress
            await self.cache.set_user_progress(user_id, progress, HOUR)
            
            return progress
            
        except Exception as e:
            self._handle_service_error(e, f"Error getting reading progress for user {user_id}")
    
    async def _get_progress_from_database(self, user_id: str) -> Dict:
        """
        Get reading progress from database.
        
        Args:
            user_id: User ID
            
        Returns:
            Dict: Reading progress data
        """
        try:
            # Default progress structure
            progress = {
                "last_read": {
                    "type": None,
                    "reference": None,
                    "timestamp": None
                },
                "completed_chapters": [],
                "completed_articles": [],
                "total_read_time_minutes": 0,
                "reading_statistics": {
                    "total_sessions": 0,
                    "completion_rate": 0.0,
                    "average_session_time": 0.0
                }
            }
            
            if not self.db_session:
                return progress
            
            user_uuid = uuid.UUID(user_id)
            
            # Get all reading progress for the user
            stmt = select(UserReadingProgress).where(
                UserReadingProgress.user_id == user_uuid
            ).order_by(UserReadingProgress.last_read_at.desc())
            
            result = await self.db_session.execute(stmt)
            progress_records = result.scalars().all()
            
            if not progress_records:
                return progress
            
            # Process progress records
            latest_record = progress_records[0]
            progress["last_read"] = {
                "type": latest_record.item_type,
                "reference": latest_record.reference,
                "timestamp": latest_record.last_read_at.isoformat()
            }
            
            # Calculate completion and statistics
            completed_chapters = []
            completed_articles = []
            total_read_time = 0
            total_sessions = len(progress_records)
            
            for record in progress_records:
                total_read_time += record.read_time_minutes
                
                if record.is_completed:
                    if record.item_type == "chapter":
                        completed_chapters.append(record.reference)
                    elif record.item_type == "article":
                        completed_articles.append(record.reference)
            
            progress["completed_chapters"] = completed_chapters
            progress["completed_articles"] = completed_articles
            progress["total_read_time_minutes"] = total_read_time
            progress["reading_statistics"] = {
                "total_sessions": total_sessions,
                "completion_rate": len(completed_chapters + completed_articles) / total_sessions if total_sessions > 0 else 0.0,
                "average_session_time": total_read_time / total_sessions if total_sessions > 0 else 0.0
            }
            
            return progress
            
        except Exception as e:
            self.logger.error(f"Error getting progress from database: {str(e)}")
            return {
                "last_read": {"type": None, "reference": None, "timestamp": None},
                "completed_chapters": [],
                "completed_articles": [],
                "total_read_time_minutes": 0,
                "reading_statistics": {"total_sessions": 0, "completion_rate": 0.0, "average_session_time": 0.0}
            }
    
    async def update_reading_progress(self, user_id: str, item_type: str, reference: str,
                                    read_time_minutes: float = 1.0,
                                    background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """
        Update reading progress for a user.
        
        Args:
            user_id: User ID
            item_type: Type of item (chapter, article)
            reference: Reference string
            read_time_minutes: Time spent reading
            background_tasks: Optional background tasks
            
        Returns:
            Dict: Updated reading progress
        """
        try:
            # Validate inputs
            user_id = self.validator.validate_user_id(user_id)
            item_type = self.validator.validate_content_type(item_type)
            read_time_minutes = self.validator.validate_reading_time(read_time_minutes)
            
            # Update database
            if self.db_session:
                await self._update_progress_in_database(user_id, item_type, reference, read_time_minutes)
            
            # Invalidate cache
            await self.cache.clear_user_progress(user_id)
            
            # Get updated progress
            updated_progress = await self.get_user_reading_progress(user_id, background_tasks)
            
            return updated_progress
            
        except Exception as e:
            self._handle_service_error(e, f"Error updating reading progress for user {user_id}")
    
    async def _update_progress_in_database(self, user_id: str, item_type: str, 
                                         reference: str, read_time_minutes: float):
        """
        Update reading progress in database.
        
        Args:
            user_id: User ID
            item_type: Type of item
            reference: Reference string
            read_time_minutes: Time spent reading
        """
        try:
            user_uuid = uuid.UUID(user_id)
            
            # Check if progress record exists
            stmt = select(UserReadingProgress).where(
                and_(
                    UserReadingProgress.user_id == user_uuid,
                    UserReadingProgress.item_type == item_type,
                    UserReadingProgress.reference == reference
                )
            )
            result = await self.db_session.execute(stmt)
            existing_record = result.scalar_one_or_none()
            
            now = datetime.now()
            
            if existing_record:
                # Update existing record
                existing_record.read_time_minutes += read_time_minutes
                existing_record.total_views += 1
                existing_record.last_read_at = now
                
                # Mark as completed if significant reading time
                if existing_record.read_time_minutes >= 2.0:
                    existing_record.is_completed = True
                
                self.logger.info(f"Updated reading progress for user {user_id}, {item_type} {reference}")
            else:
                # Create new record
                new_progress = UserReadingProgress(
                    user_id=user_uuid,
                    item_type=item_type,
                    reference=reference,
                    read_time_minutes=read_time_minutes,
                    total_views=1,
                    is_completed=read_time_minutes >= 2.0,
                    first_read_at=now,
                    last_read_at=now
                )
                self.db_session.add(new_progress)
                self.logger.info(f"Created new reading progress for user {user_id}, {item_type} {reference}")
            
            await self.db_session.commit()
            
        except Exception as e:
            self.logger.error(f"Error updating progress in database: {str(e)}")
            await self.db_session.rollback()
    
    async def get_reading_history(self, user_id: str, limit: int = 50) -> List[Dict]:
        """
        Get reading history for a user.
        
        Args:
            user_id: User ID
            limit: Maximum number of records
            
        Returns:
            List[Dict]: Reading history
        """
        try:
            # Validate user ID
            user_id = self.validator.validate_user_id(user_id)
            
            if not self.db_session:
                return []
            
            user_uuid = uuid.UUID(user_id)
            
            # Get reading history
            stmt = select(UserReadingProgress).where(
                UserReadingProgress.user_id == user_uuid
            ).order_by(UserReadingProgress.last_read_at.desc()).limit(limit)
            
            result = await self.db_session.execute(stmt)
            records = result.scalars().all()
            
            # Convert to response format
            history = []
            for record in records:
                history.append({
                    "item_type": record.item_type,
                    "reference": record.reference,
                    "read_time_minutes": record.read_time_minutes,
                    "total_views": record.total_views,
                    "is_completed": record.is_completed,
                    "first_read_at": record.first_read_at.isoformat(),
                    "last_read_at": record.last_read_at.isoformat()
                })
            
            return history
            
        except Exception as e:
            self.logger.error(f"Error getting reading history: {str(e)}")
            return []
    
    async def get_completion_status(self, user_id: str, item_type: str, reference: str) -> Dict:
        """
        Get completion status for a specific item.
        
        Args:
            user_id: User ID
            item_type: Type of item
            reference: Reference string
            
        Returns:
            Dict: Completion status
        """
        try:
            # Validate inputs
            user_id = self.validator.validate_user_id(user_id)
            item_type = self.validator.validate_content_type(item_type)
            
            if not self.db_session:
                return {"is_completed": False, "read_time_minutes": 0}
            
            user_uuid = uuid.UUID(user_id)
            
            # Get specific progress record
            stmt = select(UserReadingProgress).where(
                and_(
                    UserReadingProgress.user_id == user_uuid,
                    UserReadingProgress.item_type == item_type,
                    UserReadingProgress.reference == reference
                )
            )
            result = await self.db_session.execute(stmt)
            record = result.scalar_one_or_none()
            
            if not record:
                return {"is_completed": False, "read_time_minutes": 0}
            
            return {
                "is_completed": record.is_completed,
                "read_time_minutes": record.read_time_minutes,
                "total_views": record.total_views,
                "first_read_at": record.first_read_at.isoformat(),
                "last_read_at": record.last_read_at.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting completion status: {str(e)}")
            return {"error": str(e)}
    
    async def mark_as_completed(self, user_id: str, item_type: str, reference: str,
                               background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """
        Mark an item as completed.
        
        Args:
            user_id: User ID
            item_type: Type of item
            reference: Reference string
            background_tasks: Optional background tasks
            
        Returns:
            Dict: Operation result
        """
        try:
            # Validate inputs
            user_id = self.validator.validate_user_id(user_id)
            item_type = self.validator.validate_content_type(item_type)
            
            if not self.db_session:
                return {"success": False, "message": "Database session not available"}
            
            user_uuid = uuid.UUID(user_id)
            
            # Get or create progress record
            stmt = select(UserReadingProgress).where(
                and_(
                    UserReadingProgress.user_id == user_uuid,
                    UserReadingProgress.item_type == item_type,
                    UserReadingProgress.reference == reference
                )
            )
            result = await self.db_session.execute(stmt)
            record = result.scalar_one_or_none()
            
            now = datetime.now()
            
            if record:
                # Update existing record
                record.is_completed = True
                record.last_read_at = now
                if record.read_time_minutes < 2.0:
                    record.read_time_minutes = 2.0  # Minimum time for completion
            else:
                # Create new record
                new_progress = UserReadingProgress(
                    user_id=user_uuid,
                    item_type=item_type,
                    reference=reference,
                    read_time_minutes=2.0,
                    total_views=1,
                    is_completed=True,
                    first_read_at=now,
                    last_read_at=now
                )
                self.db_session.add(new_progress)
            
            await self.db_session.commit()
            
            # Invalidate cache
            await self.cache.clear_user_progress(user_id)
            
            return {"success": True, "message": "Item marked as completed"}
            
        except Exception as e:
            if self.db_session:
                await self.db_session.rollback()
            self.logger.error(f"Error marking as completed: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def get_reading_statistics(self, user_id: str) -> Dict:
        """
        Get comprehensive reading statistics for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Dict: Reading statistics
        """
        try:
            # Validate user ID
            user_id = self.validator.validate_user_id(user_id)
            
            # Get reading progress
            progress = await self.get_user_reading_progress(user_id)
            
            # Get reading history
            history = await self.get_reading_history(user_id, 100)
            
            # Calculate additional statistics
            stats = {
                "total_read_time_minutes": progress["total_read_time_minutes"],
                "total_sessions": len(history),
                "completed_chapters": len(progress["completed_chapters"]),
                "completed_articles": len(progress["completed_articles"]),
                "completion_rate": progress["reading_statistics"]["completion_rate"],
                "average_session_time": progress["reading_statistics"]["average_session_time"],
                "reading_streak": await self._calculate_reading_streak(user_id),
                "most_read_content_type": self._get_most_read_content_type(history),
                "reading_patterns": self._analyze_reading_patterns(history)
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting reading statistics: {str(e)}")
            return {"error": str(e)}
    
    async def _calculate_reading_streak(self, user_id: str) -> int:
        """
        Calculate current reading streak for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            int: Reading streak in days
        """
        try:
            # This is a simplified implementation
            # In a real system, you'd analyze daily reading patterns
            history = await self.get_reading_history(user_id, 30)
            
            if not history:
                return 0
            
            # Count unique dates in the last 30 days
            unique_dates = set()
            for record in history:
                date_str = record["last_read_at"][:10]  # Extract date part
                unique_dates.add(date_str)
            
            return len(unique_dates)
            
        except Exception as e:
            self.logger.error(f"Error calculating reading streak: {str(e)}")
            return 0
    
    def _get_most_read_content_type(self, history: List[Dict]) -> Optional[str]:
        """
        Get the most read content type.
        
        Args:
            history: Reading history
            
        Returns:
            Optional[str]: Most read content type
        """
        try:
            if not history:
                return None
            
            type_counts = {}
            for record in history:
                item_type = record["item_type"]
                type_counts[item_type] = type_counts.get(item_type, 0) + 1
            
            return max(type_counts, key=type_counts.get)
            
        except Exception as e:
            self.logger.error(f"Error getting most read content type: {str(e)}")
            return None
    
    def _analyze_reading_patterns(self, history: List[Dict]) -> Dict:
        """
        Analyze reading patterns from history.
        
        Args:
            history: Reading history
            
        Returns:
            Dict: Reading patterns analysis
        """
        try:
            if not history:
                return {"peak_hours": [], "average_session_length": 0}
            
            # Simple analysis - in a real system, you'd do more sophisticated analysis
            total_time = sum(record["read_time_minutes"] for record in history)
            average_session = total_time / len(history) if history else 0
            
            return {
                "peak_hours": [],  # Would analyze timestamps to find peak reading hours
                "average_session_length": round(average_session, 2),
                "total_sessions": len(history)
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing reading patterns: {str(e)}")
            return {"peak_hours": [], "average_session_length": 0}
    
    async def reset_progress(self, user_id: str, item_type: Optional[str] = None,
                           reference: Optional[str] = None) -> Dict:
        """
        Reset reading progress for a user.
        
        Args:
            user_id: User ID
            item_type: Optional specific item type to reset
            reference: Optional specific reference to reset
            
        Returns:
            Dict: Operation result
        """
        try:
            # Validate user ID
            user_id = self.validator.validate_user_id(user_id)
            
            if not self.db_session:
                return {"success": False, "message": "Database session not available"}
            
            user_uuid = uuid.UUID(user_id)
            
            # Build query
            query = select(UserReadingProgress).where(UserReadingProgress.user_id == user_uuid)
            
            if item_type:
                query = query.where(UserReadingProgress.item_type == item_type)
            if reference:
                query = query.where(UserReadingProgress.reference == reference)
            
            # Get records to delete
            result = await self.db_session.execute(query)
            records = result.scalars().all()
            
            # Delete records
            deleted_count = len(records)
            for record in records:
                await self.db_session.delete(record)
            
            await self.db_session.commit()
            
            # Clear cache
            await self.cache.clear_user_progress(user_id)
            
            return {
                "success": True,
                "message": f"Reset {deleted_count} progress records",
                "deleted_count": deleted_count
            }
            
        except Exception as e:
            if self.db_session:
                await self.db_session.rollback()
            self.logger.error(f"Error resetting progress: {str(e)}")
            return {"success": False, "message": str(e)}