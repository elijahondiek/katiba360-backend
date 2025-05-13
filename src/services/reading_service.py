from typing import Optional, List, Dict, Any, Union
import uuid
from datetime import datetime, date, timedelta
from fastapi import HTTPException, status, Depends
from sqlalchemy import select, func, update, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from src.database import get_db
from src.models.user_models import User, ReadingHistory
from src.schemas.user_schemas import ReadingHistoryCreate, ReadingHistoryUpdate
from src.utils.logging.activity_logger import ActivityLogger


class ReadingService:
    """
    Service for handling reading-related operations including history,
    progress tracking, and streak calculations
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.activity_logger = ActivityLogger()
    
    async def get_reading_history(self, user_id: uuid.UUID) -> List[ReadingHistory]:
        """
        Get reading history for a user
        
        Args:
            user_id: User ID
            
        Returns:
            List of reading history entries
        """
        query = (
            select(ReadingHistory)
            .where(ReadingHistory.user_id == user_id)
            .order_by(ReadingHistory.started_at.desc())
        )
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_reading_history_by_id(
        self, history_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[ReadingHistory]:
        """
        Get reading history entry by ID
        
        Args:
            history_id: Reading history ID
            user_id: User ID for verification
            
        Returns:
            Reading history entry if found, None otherwise
        """
        query = (
            select(ReadingHistory)
            .where(
                ReadingHistory.id == history_id,
                ReadingHistory.user_id == user_id
            )
        )
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def get_reading_history_by_content(
        self, content_id: uuid.UUID, content_type: str, user_id: uuid.UUID
    ) -> Optional[ReadingHistory]:
        """
        Get reading history entry by content ID and type
        
        Args:
            content_id: Content ID
            content_type: Content type
            user_id: User ID for verification
            
        Returns:
            Reading history entry if found, None otherwise
        """
        query = (
            select(ReadingHistory)
            .where(
                ReadingHistory.content_id == content_id,
                ReadingHistory.content_type == content_type,
                ReadingHistory.user_id == user_id
            )
            .order_by(ReadingHistory.started_at.desc())
        )
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def create_reading_history(
        self, user_id: uuid.UUID, history_data: ReadingHistoryCreate
    ) -> ReadingHistory:
        """
        Create a reading history entry
        
        Args:
            user_id: User ID
            history_data: Reading history data
            
        Returns:
            Created reading history entry
        """
        # Create reading history entry
        reading_history = ReadingHistory(
            user_id=user_id,
            **history_data.dict()
        )
        
        self.db.add(reading_history)
        await self.db.commit()
        await self.db.refresh(reading_history)
        
        # Log activity
        await self.activity_logger.log_activity(
            f"User started reading content of type '{history_data.content_type}'",
            user_id=str(user_id),
            activity_type="reading_started",
            metadata={
                "reading_history_id": str(reading_history.id),
                "content_id": str(history_data.content_id),
                "content_type": history_data.content_type,
                "device_type": history_data.device_type,
                "reading_mode": history_data.reading_mode
            }
        )
        
        return reading_history
    
    async def update_reading_history(
        self, history_id: uuid.UUID, user_id: uuid.UUID, history_data: ReadingHistoryUpdate
    ) -> ReadingHistory:
        """
        Update a reading history entry
        
        Args:
            history_id: Reading history ID
            user_id: User ID for verification
            history_data: Reading history update data
            
        Returns:
            Updated reading history entry
            
        Raises:
            HTTPException: If reading history entry not found
        """
        # Get reading history entry
        reading_history = await self.get_reading_history_by_id(history_id, user_id)
        if not reading_history:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reading history entry not found"
            )
        
        # Update fields if provided
        update_data = history_data.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(reading_history, key, value)
        
        # If completed_at is provided, update user stats
        if history_data.completed_at and not reading_history.completed_at:
            await self._update_user_reading_stats(
                user_id, 
                reading_time_seconds=history_data.reading_time_seconds
            )
        
        await self.db.commit()
        await self.db.refresh(reading_history)
        
        # Log activity
        activity_type = "reading_updated"
        if history_data.completed_at and not reading_history.completed_at:
            activity_type = "reading_completed"
        
        await self.activity_logger.log_activity(
            f"User updated reading progress to {reading_history.progress_percentage}%",
            user_id=str(user_id),
            activity_type=activity_type,
            metadata={
                "reading_history_id": str(history_id),
                "updated_fields": list(update_data.keys()),
                "progress_percentage": reading_history.progress_percentage,
                "completed": reading_history.completed_at is not None
            }
        )
        
        return reading_history
    
    async def _update_user_reading_stats(
        self, user_id: uuid.UUID, reading_time_seconds: Optional[int] = None
    ) -> None:
        """
        Update user reading stats when a reading session is completed
        
        Args:
            user_id: User ID
            reading_time_seconds: Reading time in seconds
        """
        # Get user
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        user = result.scalars().first()
        
        if not user:
            return
        
        # Update total content read
        user.total_content_read += 1
        
        # Update total reading time
        if reading_time_seconds:
            user.total_reading_time_minutes += reading_time_seconds // 60
        
        # Update last read date
        today = date.today()
        user.last_read_date = today
        
        # Update streak
        if user.last_read_date:
            yesterday = today - timedelta(days=1)
            if user.last_read_date == yesterday:
                # Continuing streak
                user.streak_days += 1
            elif user.last_read_date < yesterday:
                # Streak broken, start new streak
                user.streak_days = 1
            # If same day, streak stays the same
        else:
            # First reading, start streak
            user.streak_days = 1
        
        await self.db.commit()
    
    async def get_reading_stats(self, user_id: uuid.UUID) -> Dict[str, Any]:
        """
        Get reading statistics for a user
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary of reading statistics
        """
        # Get user
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        user = result.scalars().first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get reading history counts
        query = (
            select(func.count())
            .select_from(ReadingHistory)
            .where(ReadingHistory.user_id == user_id)
        )
        result = await self.db.execute(query)
        total_sessions = result.scalar() or 0
        
        # Get completed reading history counts
        query = (
            select(func.count())
            .select_from(ReadingHistory)
            .where(
                ReadingHistory.user_id == user_id,
                ReadingHistory.completed_at.isnot(None)
            )
        )
        result = await self.db.execute(query)
        completed_sessions = result.scalar() or 0
        
        # Get average reading time
        query = (
            select(func.avg(ReadingHistory.reading_time_seconds))
            .select_from(ReadingHistory)
            .where(
                ReadingHistory.user_id == user_id,
                ReadingHistory.reading_time_seconds.isnot(None)
            )
        )
        result = await self.db.execute(query)
        avg_reading_time = result.scalar() or 0
        
        # Get reading by content type
        query = (
            select(
                ReadingHistory.content_type,
                func.count().label("count")
            )
            .where(ReadingHistory.user_id == user_id)
            .group_by(ReadingHistory.content_type)
        )
        result = await self.db.execute(query)
        content_type_counts = {row[0]: row[1] for row in result.all()}
        
        # Get reading by device type
        query = (
            select(
                ReadingHistory.device_type,
                func.count().label("count")
            )
            .where(
                ReadingHistory.user_id == user_id,
                ReadingHistory.device_type.isnot(None)
            )
            .group_by(ReadingHistory.device_type)
        )
        result = await self.db.execute(query)
        device_type_counts = {row[0]: row[1] for row in result.all()}
        
        # Get reading by mode
        query = (
            select(
                ReadingHistory.reading_mode,
                func.count().label("count")
            )
            .where(
                ReadingHistory.user_id == user_id,
                ReadingHistory.reading_mode.isnot(None)
            )
            .group_by(ReadingHistory.reading_mode)
        )
        result = await self.db.execute(query)
        reading_mode_counts = {row[0]: row[1] for row in result.all()}
        
        # Calculate completion rate
        completion_rate = 0
        if total_sessions > 0:
            completion_rate = (completed_sessions / total_sessions) * 100
        
        return {
            "total_content_read": user.total_content_read,
            "total_reading_time_minutes": user.total_reading_time_minutes,
            "streak_days": user.streak_days,
            "last_read_date": user.last_read_date,
            "total_sessions": total_sessions,
            "completed_sessions": completed_sessions,
            "completion_rate": completion_rate,
            "avg_reading_time_seconds": avg_reading_time,
            "content_type_breakdown": content_type_counts,
            "device_type_breakdown": device_type_counts,
            "reading_mode_breakdown": reading_mode_counts
        }
    
    async def get_reading_streak_calendar(
        self, user_id: uuid.UUID, year: int, month: int
    ) -> Dict[str, Any]:
        """
        Get reading streak calendar for a specific month
        
        Args:
            user_id: User ID
            year: Year
            month: Month (1-12)
            
        Returns:
            Dictionary with calendar data
        """
        # Validate month
        if month < 1 or month > 12:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Month must be between 1 and 12"
            )
        
        # Get first and last day of month
        first_day = date(year, month, 1)
        if month == 12:
            last_day = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = date(year, month + 1, 1) - timedelta(days=1)
        
        # Get all reading history entries for the month
        query = (
            select(
                func.date(ReadingHistory.started_at).label("reading_date"),
                func.count().label("count")
            )
            .where(
                ReadingHistory.user_id == user_id,
                func.date(ReadingHistory.started_at) >= first_day,
                func.date(ReadingHistory.started_at) <= last_day
            )
            .group_by("reading_date")
        )
        result = await self.db.execute(query)
        reading_dates = {row[0]: row[1] for row in result.all()}
        
        # Create calendar data
        calendar_data = {}
        current_date = first_day
        while current_date <= last_day:
            day_str = current_date.isoformat()
            calendar_data[day_str] = reading_dates.get(current_date, 0)
            current_date += timedelta(days=1)
        
        # Get user streak info
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        user = result.scalars().first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return {
            "year": year,
            "month": month,
            "calendar_data": calendar_data,
            "current_streak": user.streak_days,
            "last_read_date": user.last_read_date.isoformat() if user.last_read_date else None
        }


# Dependency to get ReadingService
async def get_reading_service(db: AsyncSession = Depends(get_db)) -> ReadingService:
    """
    Dependency to get ReadingService instance
    
    Args:
        db: Database session
        
    Returns:
        ReadingService instance
    """
    return ReadingService(db)
