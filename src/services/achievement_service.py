from typing import Optional, List, Dict, Any, Union
import uuid
from datetime import datetime, date, timedelta
from fastapi import HTTPException, status, Depends
from sqlalchemy import select, func, update, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from src.database import get_db
from src.models.user_models import User, UserAchievement, ReadingHistory
from src.schemas.user_schemas import UserAchievementCreate, BadgeType
from src.utils.logging.activity_logger import ActivityLogger


class AchievementService:
    """
    Service for handling achievement-related operations including
    achievement tracking and badge awarding
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.activity_logger = ActivityLogger()
    
    async def get_user_achievements(self, user_id: uuid.UUID) -> List[UserAchievement]:
        """
        Get all achievements for a user
        
        Args:
            user_id: User ID
            
        Returns:
            List of user achievements
        """
        query = (
            select(UserAchievement)
            .where(UserAchievement.user_id == user_id)
            .order_by(UserAchievement.earned_at.desc())
        )
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_achievement_by_id(
        self, achievement_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[UserAchievement]:
        """
        Get achievement by ID
        
        Args:
            achievement_id: Achievement ID
            user_id: User ID for verification
            
        Returns:
            User achievement if found, None otherwise
        """
        query = (
            select(UserAchievement)
            .where(
                UserAchievement.id == achievement_id,
                UserAchievement.user_id == user_id
            )
        )
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def get_achievement_by_type(
        self, achievement_type: str, user_id: uuid.UUID
    ) -> Optional[UserAchievement]:
        """
        Get achievement by type
        
        Args:
            achievement_type: Achievement type
            user_id: User ID for verification
            
        Returns:
            User achievement if found, None otherwise
        """
        query = (
            select(UserAchievement)
            .where(
                UserAchievement.achievement_type == achievement_type,
                UserAchievement.user_id == user_id
            )
        )
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def award_achievement(
        self, user_id: uuid.UUID, achievement_data: UserAchievementCreate
    ) -> UserAchievement:
        """
        Award an achievement to a user
        
        Args:
            user_id: User ID
            achievement_data: Achievement data
            
        Returns:
            Created user achievement
            
        Raises:
            HTTPException: If achievement already awarded
        """
        # Check if achievement already awarded
        existing_achievement = await self.get_achievement_by_type(
            achievement_data.achievement_type, user_id
        )
        
        if existing_achievement:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Achievement '{achievement_data.achievement_type}' already awarded"
            )
        
        # Create achievement
        achievement = UserAchievement(
            user_id=user_id,
            **achievement_data.dict()
        )
        
        self.db.add(achievement)
        
        # Update user achievement points
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        user = result.scalars().first()
        
        if user:
            user.achievement_points += achievement_data.points_earned
        
        await self.db.commit()
        await self.db.refresh(achievement)
        
        # Log activity
        await self.activity_logger.log_activity(
            f"User earned achievement '{achievement.title}' ({achievement.achievement_type})",
            user_id=str(user_id),
            activity_type="achievement_earned",
            metadata={
                "achievement_id": str(achievement.id),
                "achievement_type": achievement.achievement_type,
                "badge_type": achievement.badge_type,
                "points_earned": achievement.points_earned
            }
        )
        
        return achievement
    
    async def check_and_award_achievements(self, user_id: uuid.UUID) -> List[UserAchievement]:
        """
        Check and award any achievements a user has earned
        
        Args:
            user_id: User ID
            
        Returns:
            List of newly awarded achievements
        """
        # Get user with reading stats
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        user = result.scalars().first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get existing achievements
        existing_achievements = await self.get_user_achievements(user_id)
        existing_types = {a.achievement_type for a in existing_achievements}
        
        # List to store new achievements
        new_achievements = []
        
        # Check for first login achievement
        if "first_login" not in existing_types and user.last_login_at:
            achievement = await self.award_achievement(
                user_id,
                UserAchievementCreate(
                    achievement_type="first_login",
                    title="Welcome to Katiba360",
                    description="Logged in to Katiba360 for the first time",
                    badge_type=BadgeType.BRONZE,
                    points_earned=10,
                    icon_url="/assets/badges/first_login.png"
                )
            )
            new_achievements.append(achievement)
        
        # Check for reading achievements
        if user.total_content_read >= 1 and "first_read" not in existing_types:
            achievement = await self.award_achievement(
                user_id,
                UserAchievementCreate(
                    achievement_type="first_read",
                    title="First Steps",
                    description="Read your first content in Katiba360",
                    badge_type=BadgeType.BRONZE,
                    points_earned=10,
                    icon_url="/assets/badges/first_read.png"
                )
            )
            new_achievements.append(achievement)
        
        if user.total_content_read >= 10 and "reader_10" not in existing_types:
            achievement = await self.award_achievement(
                user_id,
                UserAchievementCreate(
                    achievement_type="reader_10",
                    title="Dedicated Reader",
                    description="Read 10 pieces of content",
                    badge_type=BadgeType.SILVER,
                    points_earned=25,
                    icon_url="/assets/badges/reader_10.png"
                )
            )
            new_achievements.append(achievement)
        
        if user.total_content_read >= 50 and "reader_50" not in existing_types:
            achievement = await self.award_achievement(
                user_id,
                UserAchievementCreate(
                    achievement_type="reader_50",
                    title="Knowledge Seeker",
                    description="Read 50 pieces of content",
                    badge_type=BadgeType.GOLD,
                    points_earned=50,
                    icon_url="/assets/badges/reader_50.png"
                )
            )
            new_achievements.append(achievement)
        
        if user.total_content_read >= 100 and "reader_100" not in existing_types:
            achievement = await self.award_achievement(
                user_id,
                UserAchievementCreate(
                    achievement_type="reader_100",
                    title="Constitution Master",
                    description="Read 100 pieces of content",
                    badge_type=BadgeType.PLATINUM,
                    points_earned=100,
                    icon_url="/assets/badges/reader_100.png"
                )
            )
            new_achievements.append(achievement)
        
        # Check for streak achievements
        if user.streak_days >= 3 and "streak_3" not in existing_types:
            achievement = await self.award_achievement(
                user_id,
                UserAchievementCreate(
                    achievement_type="streak_3",
                    title="Consistent Reader",
                    description="Maintained a 3-day reading streak",
                    badge_type=BadgeType.BRONZE,
                    points_earned=15,
                    icon_url="/assets/badges/streak_3.png"
                )
            )
            new_achievements.append(achievement)
        
        if user.streak_days >= 7 and "streak_7" not in existing_types:
            achievement = await self.award_achievement(
                user_id,
                UserAchievementCreate(
                    achievement_type="streak_7",
                    title="Weekly Dedication",
                    description="Maintained a 7-day reading streak",
                    badge_type=BadgeType.SILVER,
                    points_earned=30,
                    icon_url="/assets/badges/streak_7.png"
                )
            )
            new_achievements.append(achievement)
        
        if user.streak_days >= 30 and "streak_30" not in existing_types:
            achievement = await self.award_achievement(
                user_id,
                UserAchievementCreate(
                    achievement_type="streak_30",
                    title="Monthly Mastery",
                    description="Maintained a 30-day reading streak",
                    badge_type=BadgeType.GOLD,
                    points_earned=75,
                    icon_url="/assets/badges/streak_30.png"
                )
            )
            new_achievements.append(achievement)
        
        # Check for time spent achievements
        if user.total_reading_time_minutes >= 60 and "time_1h" not in existing_types:
            achievement = await self.award_achievement(
                user_id,
                UserAchievementCreate(
                    achievement_type="time_1h",
                    title="One Hour Wonder",
                    description="Spent 1 hour reading the constitution",
                    badge_type=BadgeType.BRONZE,
                    points_earned=20,
                    icon_url="/assets/badges/time_1h.png"
                )
            )
            new_achievements.append(achievement)
        
        if user.total_reading_time_minutes >= 300 and "time_5h" not in existing_types:
            achievement = await self.award_achievement(
                user_id,
                UserAchievementCreate(
                    achievement_type="time_5h",
                    title="Deep Diver",
                    description="Spent 5 hours reading the constitution",
                    badge_type=BadgeType.SILVER,
                    points_earned=40,
                    icon_url="/assets/badges/time_5h.png"
                )
            )
            new_achievements.append(achievement)
        
        if user.total_reading_time_minutes >= 1000 and "time_16h" not in existing_types:
            achievement = await self.award_achievement(
                user_id,
                UserAchievementCreate(
                    achievement_type="time_16h",
                    title="Constitutional Scholar",
                    description="Spent 16+ hours reading the constitution",
                    badge_type=BadgeType.GOLD,
                    points_earned=80,
                    icon_url="/assets/badges/time_16h.png"
                )
            )
            new_achievements.append(achievement)
        
        # Check for onboarding completion
        if user.onboarding_completed and "onboarding_complete" not in existing_types:
            achievement = await self.award_achievement(
                user_id,
                UserAchievementCreate(
                    achievement_type="onboarding_complete",
                    title="Ready to Explore",
                    description="Completed the onboarding process",
                    badge_type=BadgeType.BRONZE,
                    points_earned=15,
                    icon_url="/assets/badges/onboarding_complete.png"
                )
            )
            new_achievements.append(achievement)
        
        # Check for multiple device usage
        query = (
            select(func.count(func.distinct(ReadingHistory.device_type)))
            .where(
                ReadingHistory.user_id == user_id,
                ReadingHistory.device_type.isnot(None)
            )
        )
        result = await self.db.execute(query)
        device_count = result.scalar() or 0
        
        if device_count >= 2 and "multi_device" not in existing_types:
            achievement = await self.award_achievement(
                user_id,
                UserAchievementCreate(
                    achievement_type="multi_device",
                    title="Cross-Platform Reader",
                    description="Used Katiba360 on multiple devices",
                    badge_type=BadgeType.SILVER,
                    points_earned=20,
                    icon_url="/assets/badges/multi_device.png"
                )
            )
            new_achievements.append(achievement)
        
        # Check for offline reading
        query = (
            select(func.count())
            .select_from(ReadingHistory)
            .where(
                ReadingHistory.user_id == user_id,
                ReadingHistory.reading_mode == "offline"
            )
        )
        result = await self.db.execute(query)
        offline_count = result.scalar() or 0
        
        if offline_count >= 1 and "offline_reader" not in existing_types:
            achievement = await self.award_achievement(
                user_id,
                UserAchievementCreate(
                    achievement_type="offline_reader",
                    title="Always Available",
                    description="Read content offline",
                    badge_type=BadgeType.BRONZE,
                    points_earned=15,
                    icon_url="/assets/badges/offline_reader.png"
                )
            )
            new_achievements.append(achievement)
        
        return new_achievements
    
    async def get_achievement_leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get achievement leaderboard
        
        Args:
            limit: Maximum number of users to return
            
        Returns:
            List of users with their achievement points
        """
        query = (
            select(
                User.id,
                User.display_name,
                User.avatar_url,
                User.achievement_points,
                func.count(UserAchievement.id).label("achievement_count")
            )
            .outerjoin(UserAchievement, User.id == UserAchievement.user_id)
            .group_by(User.id, User.display_name, User.avatar_url, User.achievement_points)
            .order_by(User.achievement_points.desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        
        leaderboard = []
        for row in result.all():
            leaderboard.append({
                "user_id": row[0],
                "display_name": row[1] or "Anonymous User",
                "avatar_url": row[2],
                "achievement_points": row[3],
                "achievement_count": row[4]
            })
        
        return leaderboard
    
    async def get_user_rank(self, user_id: uuid.UUID) -> Dict[str, Any]:
        """
        Get a user's rank on the achievement leaderboard
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with user's rank and total users
            
        Raises:
            HTTPException: If user not found
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
        
        # Get user's rank
        query = (
            select(func.count())
            .select_from(User)
            .where(User.achievement_points > user.achievement_points)
        )
        result = await self.db.execute(query)
        rank = result.scalar() or 0
        rank += 1  # Add 1 because rank is 1-indexed
        
        # Get total users
        query = select(func.count()).select_from(User)
        result = await self.db.execute(query)
        total_users = result.scalar() or 0
        
        # Get user's achievement count
        query = (
            select(func.count())
            .select_from(UserAchievement)
            .where(UserAchievement.user_id == user_id)
        )
        result = await self.db.execute(query)
        achievement_count = result.scalar() or 0
        
        return {
            "user_id": user_id,
            "display_name": user.display_name or "Anonymous User",
            "avatar_url": user.avatar_url,
            "achievement_points": user.achievement_points,
            "achievement_count": achievement_count,
            "rank": rank,
            "total_users": total_users,
            "percentile": round((1 - (rank / total_users)) * 100) if total_users > 0 else 0
        }


# Dependency to get AchievementService
async def get_achievement_service(db: AsyncSession = Depends(get_db)) -> AchievementService:
    """
    Dependency to get AchievementService instance
    
    Args:
        db: Database session
        
    Returns:
        AchievementService instance
    """
    return AchievementService(db)
