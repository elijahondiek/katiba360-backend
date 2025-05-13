from typing import Optional, List, Dict, Any, Union
import uuid
from datetime import datetime
from fastapi import HTTPException, status, Depends
from sqlalchemy import select, func, update, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from src.database import get_db
from src.models.user_models import User, UserNotification, UserPreference
from src.schemas.user_schemas import UserNotificationCreate, UserNotificationUpdate, NotificationType
from src.utils.logging.activity_logger import ActivityLogger


class NotificationService:
    """
    Service for handling notification-related operations
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.activity_logger = ActivityLogger()
    
    async def get_user_notifications(
        self, user_id: uuid.UUID, unread_only: bool = False, limit: int = 50, offset: int = 0
    ) -> List[UserNotification]:
        """
        Get notifications for a user
        
        Args:
            user_id: User ID
            unread_only: Only return unread notifications
            limit: Maximum number of notifications to return
            offset: Offset for pagination
            
        Returns:
            List of user notifications
        """
        query = (
            select(UserNotification)
            .where(UserNotification.user_id == user_id)
        )
        
        if unread_only:
            query = query.where(UserNotification.is_read == False)
        
        query = (
            query
            .order_by(UserNotification.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_notification_by_id(
        self, notification_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[UserNotification]:
        """
        Get notification by ID
        
        Args:
            notification_id: Notification ID
            user_id: User ID for verification
            
        Returns:
            User notification if found, None otherwise
        """
        query = (
            select(UserNotification)
            .where(
                UserNotification.id == notification_id,
                UserNotification.user_id == user_id
            )
        )
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def create_notification(
        self, user_id: uuid.UUID, notification_data: UserNotificationCreate
    ) -> UserNotification:
        """
        Create a notification for a user
        
        Args:
            user_id: User ID
            notification_data: Notification data
            
        Returns:
            Created user notification
        """
        # Check if user exists and get preferences
        query = (
            select(User)
            .options(selectinload(User.preferences))
            .where(User.id == user_id)
        )
        result = await self.db.execute(query)
        user = result.scalars().first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Create notification
        notification = UserNotification(
            user_id=user_id,
            **notification_data.dict()
        )
        
        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)
        
        # Log activity
        await self.activity_logger.log_activity(
            f"Notification created for user: {notification.title}",
            user_id=str(user_id),
            activity_type="notification_created",
            metadata={
                "notification_id": str(notification.id),
                "notification_type": notification.notification_type,
                "title": notification.title
            }
        )
        
        return notification
    
    async def mark_notification_as_read(
        self, notification_id: uuid.UUID, user_id: uuid.UUID
    ) -> UserNotification:
        """
        Mark a notification as read
        
        Args:
            notification_id: Notification ID
            user_id: User ID for verification
            
        Returns:
            Updated user notification
            
        Raises:
            HTTPException: If notification not found
        """
        # Get notification
        notification = await self.get_notification_by_id(notification_id, user_id)
        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found"
            )
        
        # Mark as read if not already
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = datetime.now()
            await self.db.commit()
            await self.db.refresh(notification)
            
            # Log activity
            await self.activity_logger.log_activity(
                f"User read notification: {notification.title}",
                user_id=str(user_id),
                activity_type="notification_read",
                metadata={
                    "notification_id": str(notification_id),
                    "notification_type": notification.notification_type
                }
            )
        
        return notification
    
    async def mark_all_notifications_as_read(self, user_id: uuid.UUID) -> int:
        """
        Mark all notifications as read for a user
        
        Args:
            user_id: User ID
            
        Returns:
            Number of notifications marked as read
        """
        # Get unread notifications
        query = (
            select(UserNotification)
            .where(
                UserNotification.user_id == user_id,
                UserNotification.is_read == False
            )
        )
        result = await self.db.execute(query)
        notifications = result.scalars().all()
        
        # Mark all as read
        now = datetime.now()
        for notification in notifications:
            notification.is_read = True
            notification.read_at = now
        
        await self.db.commit()
        
        # Log activity
        if notifications:
            await self.activity_logger.log_activity(
                f"User marked all notifications as read ({len(notifications)} notifications)",
                user_id=str(user_id),
                activity_type="all_notifications_read",
                metadata={
                    "count": len(notifications)
                }
            )
        
        return len(notifications)
    
    async def delete_notification(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """
        Delete a notification
        
        Args:
            notification_id: Notification ID
            user_id: User ID for verification
            
        Returns:
            True if successful
            
        Raises:
            HTTPException: If notification not found
        """
        # Get notification
        notification = await self.get_notification_by_id(notification_id, user_id)
        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found"
            )
        
        # Delete notification
        await self.db.delete(notification)
        await self.db.commit()
        
        # Log activity
        await self.activity_logger.log_activity(
            f"User deleted notification: {notification.title}",
            user_id=str(user_id),
            activity_type="notification_deleted",
            metadata={
                "notification_id": str(notification_id),
                "notification_type": notification.notification_type
            }
        )
        
        return True
    
    async def delete_all_read_notifications(self, user_id: uuid.UUID) -> int:
        """
        Delete all read notifications for a user
        
        Args:
            user_id: User ID
            
        Returns:
            Number of notifications deleted
        """
        # Get read notifications
        query = (
            select(UserNotification)
            .where(
                UserNotification.user_id == user_id,
                UserNotification.is_read == True
            )
        )
        result = await self.db.execute(query)
        notifications = result.scalars().all()
        
        # Delete all read notifications
        for notification in notifications:
            await self.db.delete(notification)
        
        await self.db.commit()
        
        # Log activity
        if notifications:
            await self.activity_logger.log_activity(
                f"User deleted all read notifications ({len(notifications)} notifications)",
                user_id=str(user_id),
                activity_type="all_read_notifications_deleted",
                metadata={
                    "count": len(notifications)
                }
            )
        
        return len(notifications)
    
    async def get_unread_notification_count(self, user_id: uuid.UUID) -> int:
        """
        Get count of unread notifications for a user
        
        Args:
            user_id: User ID
            
        Returns:
            Number of unread notifications
        """
        query = (
            select(func.count())
            .select_from(UserNotification)
            .where(
                UserNotification.user_id == user_id,
                UserNotification.is_read == False
            )
        )
        result = await self.db.execute(query)
        return result.scalar() or 0
    
    async def create_achievement_notification(
        self, user_id: uuid.UUID, achievement_title: str, badge_type: str, points: int
    ) -> UserNotification:
        """
        Create a notification for an achievement
        
        Args:
            user_id: User ID
            achievement_title: Achievement title
            badge_type: Badge type
            points: Points earned
            
        Returns:
            Created user notification
        """
        notification_data = UserNotificationCreate(
            title="New Achievement Unlocked!",
            message=f"Congratulations! You've earned the '{achievement_title}' achievement and {points} points.",
            notification_type=NotificationType.ACHIEVEMENT,
            action_url="/profile/achievements",
            priority=2
        )
        
        return await self.create_notification(user_id, notification_data)
    
    async def create_streak_notification(
        self, user_id: uuid.UUID, streak_days: int
    ) -> UserNotification:
        """
        Create a notification for a streak milestone
        
        Args:
            user_id: User ID
            streak_days: Number of streak days
            
        Returns:
            Created user notification
        """
        notification_data = UserNotificationCreate(
            title="Reading Streak Milestone!",
            message=f"Amazing! You've maintained a reading streak for {streak_days} days. Keep it up!",
            notification_type=NotificationType.ACHIEVEMENT,
            action_url="/profile/stats",
            priority=1
        )
        
        return await self.create_notification(user_id, notification_data)
    
    async def create_content_update_notification(
        self, user_id: uuid.UUID, content_type: str, content_title: str
    ) -> UserNotification:
        """
        Create a notification for content updates
        
        Args:
            user_id: User ID
            content_type: Type of content
            content_title: Title of content
            
        Returns:
            Created user notification
        """
        notification_data = UserNotificationCreate(
            title="New Content Available",
            message=f"New {content_type} has been added: {content_title}",
            notification_type=NotificationType.UPDATE,
            action_url=f"/content/{content_type.lower()}",
            priority=0
        )
        
        return await self.create_notification(user_id, notification_data)
    
    async def create_reminder_notification(
        self, user_id: uuid.UUID, days_since_last_read: int
    ) -> UserNotification:
        """
        Create a reminder notification for inactive users
        
        Args:
            user_id: User ID
            days_since_last_read: Days since last read
            
        Returns:
            Created user notification
        """
        notification_data = UserNotificationCreate(
            title="We Miss You!",
            message=f"It's been {days_since_last_read} days since you last read something. Come back and continue learning about the constitution!",
            notification_type=NotificationType.REMINDER,
            action_url="/home",
            priority=1
        )
        
        return await self.create_notification(user_id, notification_data)


# Dependency to get NotificationService
async def get_notification_service(db: AsyncSession = Depends(get_db)) -> NotificationService:
    """
    Dependency to get NotificationService instance
    
    Args:
        db: Database session
        
    Returns:
        NotificationService instance
    """
    return NotificationService(db)
