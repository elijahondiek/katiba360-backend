"""
Cached Achievement Service with Redis caching and proper revoke mechanisms.
Extends the base AchievementService with caching capabilities.
"""

from typing import Optional, List, Dict, Any, Union
import uuid
import json
from datetime import datetime, date, timedelta
from fastapi import HTTPException, status, Depends, BackgroundTasks
from sqlalchemy import select, func, update, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database import get_db
from src.models.user_models import User, UserAchievement, ReadingHistory
from src.schemas.user_schemas import UserAchievementCreate, BadgeType
from src.utils.logging.activity_logger import ActivityLogger
from src.utils.cache import CacheManager, HOUR, MINUTE, DAY
from src.services.achievement_service import AchievementService

# Fix import for typing
from typing import Optional


class CachedAchievementService(AchievementService):
    """
    Enhanced Achievement Service with Redis caching and proper cache invalidation.
    Extends the base AchievementService with caching capabilities.
    """
    
    def __init__(self, db: AsyncSession, cache_manager: CacheManager):
        super().__init__(db)
        self.cache = cache_manager
        self.cache_prefix = "achievements"
        
    def _get_cache_key(self, key_type: str, user_id: str, additional: str = "") -> str:
        """Generate cache key for achievement data"""
        base_key = f"{self.cache_prefix}:{user_id}:{key_type}"
        return f"{base_key}:{additional}" if additional else base_key
    
    def _get_global_cache_key(self, key_type: str, additional: str = "") -> str:
        """Generate cache key for global achievement data"""
        base_key = f"{self.cache_prefix}:global:{key_type}"
        return f"{base_key}:{additional}" if additional else base_key
    
    async def _invalidate_user_achievements_cache(self, user_id: str, background_tasks: Optional[BackgroundTasks] = None):
        """Invalidate all cached achievement data for a user"""
        cache_patterns = [
            f"{self.cache_prefix}:{user_id}:achievements",
            f"{self.cache_prefix}:{user_id}:summary",
            f"{self.cache_prefix}:{user_id}:stats",
            f"{self.cache_prefix}:{user_id}:badges",
            f"{self.cache_prefix}:{user_id}:recent",
            f"{self.cache_prefix}:{user_id}:progress",
        ]
        
        for pattern in cache_patterns:
            await self.cache.delete(pattern)
        
        # Also invalidate global leaderboard cache since user achievements changed
        await self._invalidate_global_cache(background_tasks)
        
        # Log cache invalidation
        await self.activity_logger.log_activity(
            user_id=user_id,
            action="achievement_cache_invalidation",
            details={"cache_patterns": cache_patterns}
        )
    
    async def _invalidate_global_cache(self, background_tasks: Optional[BackgroundTasks] = None):
        """Invalidate global achievement cache (leaderboards, etc.)"""
        global_cache_patterns = [
            f"{self.cache_prefix}:global:leaderboard",
            f"{self.cache_prefix}:global:top_achievers",
            f"{self.cache_prefix}:global:stats",
            f"{self.cache_prefix}:global:recent_achievements",
        ]
        
        for pattern in global_cache_patterns:
            await self.cache.delete(pattern)
    
    async def get_user_achievements_cached(self, user_id: uuid.UUID,
                                         background_tasks: Optional[BackgroundTasks] = None) -> List[UserAchievement]:
        """
        Get user achievements with caching
        
        Args:
            user_id: User ID
            background_tasks: Optional background tasks
            
        Returns:
            List of user achievements
        """
        user_id_str = str(user_id)
        cache_key = self._get_cache_key("achievements", user_id_str)
        
        # Try cache first
        cached_achievements = await self.cache.get(cache_key)
        if cached_achievements:
            achievements_data = json.loads(cached_achievements)
            return [UserAchievement(**achievement) for achievement in achievements_data]
        
        # Get from database
        achievements = await self.get_user_achievements(user_id)
        
        # Cache the result
        if achievements:
            achievements_dict = [
                {
                    "id": str(achievement.id),
                    "user_id": str(achievement.user_id),
                    "badge_type": achievement.badge_type,
                    "badge_name": achievement.badge_name,
                    "badge_description": achievement.badge_description,
                    "badge_icon": achievement.badge_icon,
                    "earned_at": achievement.earned_at.isoformat() if achievement.earned_at else None,
                    "achievement_data": achievement.achievement_data,
                }
                for achievement in achievements
            ]
            # Cache for 30 minutes (achievements don't change frequently)
            await self.cache.set(cache_key, json.dumps(achievements_dict), expire=30 * MINUTE)
        
        return achievements
    
    async def get_user_achievement_summary_cached(self, user_id: uuid.UUID,
                                                background_tasks: Optional[BackgroundTasks] = None) -> Dict[str, Any]:
        """
        Get user achievement summary with caching
        
        Args:
            user_id: User ID
            background_tasks: Optional background tasks
            
        Returns:
            Achievement summary dictionary
        """
        user_id_str = str(user_id)
        cache_key = self._get_cache_key("summary", user_id_str)
        
        # Try cache first
        cached_summary = await self.cache.get(cache_key)
        if cached_summary:
            return json.loads(cached_summary)
        
        # Get achievements and calculate summary
        achievements = await self.get_user_achievements_cached(user_id, background_tasks)
        
        # Calculate summary statistics
        summary = {
            "total_achievements": len(achievements),
            "badges_by_type": {},
            "recent_achievements": [],
            "next_achievements": [],
            "completion_percentage": 0,
            "last_earned": None,
        }
        
        # Group by badge type
        for achievement in achievements:
            badge_type = achievement.badge_type
            if badge_type not in summary["badges_by_type"]:
                summary["badges_by_type"][badge_type] = 0
            summary["badges_by_type"][badge_type] += 1
        
        # Recent achievements (last 5)
        recent_achievements = sorted(achievements, key=lambda x: x.earned_at, reverse=True)[:5]
        summary["recent_achievements"] = [
            {
                "badge_name": achievement.badge_name,
                "badge_description": achievement.badge_description,
                "badge_icon": achievement.badge_icon,
                "earned_at": achievement.earned_at.isoformat() if achievement.earned_at else None,
            }
            for achievement in recent_achievements
        ]
        
        # Last earned achievement
        if recent_achievements:
            summary["last_earned"] = recent_achievements[0].earned_at.isoformat()
        
        # Calculate completion percentage (this would need total possible achievements)
        # For now, using a simple calculation
        total_possible = await self._get_total_possible_achievements()
        summary["completion_percentage"] = int((len(achievements) / total_possible) * 100) if total_possible > 0 else 0
        
        # Cache summary for 30 minutes
        await self.cache.set(cache_key, json.dumps(summary), expire=30 * MINUTE)
        
        return summary
    
    async def get_user_achievement_stats_cached(self, user_id: uuid.UUID,
                                              background_tasks: Optional[BackgroundTasks] = None) -> Dict[str, Any]:
        """
        Get detailed user achievement statistics with caching
        
        Args:
            user_id: User ID
            background_tasks: Optional background tasks
            
        Returns:
            Achievement statistics dictionary
        """
        user_id_str = str(user_id)
        cache_key = self._get_cache_key("stats", user_id_str)
        
        # Try cache first
        cached_stats = await self.cache.get(cache_key)
        if cached_stats:
            return json.loads(cached_stats)
        
        # Get achievements and calculate detailed stats
        achievements = await self.get_user_achievements_cached(user_id, background_tasks)
        
        # Calculate detailed statistics
        now = datetime.utcnow()
        thirty_days_ago = now - timedelta(days=30)
        seven_days_ago = now - timedelta(days=7)
        
        stats = {
            "total_achievements": len(achievements),
            "achievements_this_month": len([a for a in achievements if a.earned_at >= thirty_days_ago]),
            "achievements_this_week": len([a for a in achievements if a.earned_at >= seven_days_ago]),
            "achievements_today": len([a for a in achievements if a.earned_at.date() == now.date()]),
            "badge_types": {},
            "achievement_timeline": [],
            "streaks": self._calculate_achievement_streaks(achievements),
            "rank_info": await self._get_user_rank_info(user_id, len(achievements)),
        }
        
        # Badge type breakdown
        for achievement in achievements:
            badge_type = achievement.badge_type
            if badge_type not in stats["badge_types"]:
                stats["badge_types"][badge_type] = {
                    "count": 0,
                    "latest": None,
                    "badges": []
                }
            
            stats["badge_types"][badge_type]["count"] += 1
            stats["badge_types"][badge_type]["badges"].append({
                "name": achievement.badge_name,
                "earned_at": achievement.earned_at.isoformat() if achievement.earned_at else None,
            })
            
            # Track latest achievement for each type
            if (stats["badge_types"][badge_type]["latest"] is None or 
                achievement.earned_at > datetime.fromisoformat(stats["badge_types"][badge_type]["latest"])):
                stats["badge_types"][badge_type]["latest"] = achievement.earned_at.isoformat()
        
        # Achievement timeline (monthly breakdown)
        stats["achievement_timeline"] = self._create_achievement_timeline(achievements)
        
        # Cache stats for 30 minutes
        await self.cache.set(cache_key, json.dumps(stats), expire=30 * MINUTE)
        
        return stats
    
    async def award_achievement_cached(self, user_id: uuid.UUID, badge_type: BadgeType,
                                     achievement_data: Dict[str, Any] = None,
                                     background_tasks: Optional[BackgroundTasks] = None) -> UserAchievement:
        """
        Award achievement to user and invalidate cache
        
        Args:
            user_id: User ID
            badge_type: Type of badge to award
            achievement_data: Additional achievement data
            background_tasks: Optional background tasks
            
        Returns:
            Awarded achievement
        """
        # Award achievement using parent method
        achievement = await self.award_achievement(user_id, badge_type, achievement_data)
        
        # Invalidate cache
        await self._invalidate_user_achievements_cache(str(user_id), background_tasks)
        
        return achievement
    
    async def get_leaderboard_cached(self, limit: int = 10, offset: int = 0,
                                   background_tasks: Optional[BackgroundTasks] = None) -> Dict[str, Any]:
        """
        Get achievement leaderboard with caching
        
        Args:
            limit: Number of users to return
            offset: Number of users to skip
            background_tasks: Optional background tasks
            
        Returns:
            Leaderboard data
        """
        cache_key = self._get_global_cache_key("leaderboard", f"{limit}:{offset}")
        
        # Try cache first
        cached_leaderboard = await self.cache.get(cache_key)
        if cached_leaderboard:
            return json.loads(cached_leaderboard)
        
        # Calculate leaderboard from database
        query = (
            select(
                UserAchievement.user_id,
                func.count(UserAchievement.id).label("achievement_count"),
                func.max(UserAchievement.earned_at).label("latest_achievement")
            )
            .group_by(UserAchievement.user_id)
            .order_by(func.count(UserAchievement.id).desc())
            .limit(limit)
            .offset(offset)
        )
        
        result = await self.db.execute(query)
        leaderboard_data = result.fetchall()
        
        # Get user details for leaderboard
        leaderboard = []
        for row in leaderboard_data:
            user_query = select(User).where(User.id == row.user_id)
            user_result = await self.db.execute(user_query)
            user = user_result.scalars().first()
            
            if user:
                leaderboard.append({
                    "user_id": str(user.id),
                    "user_name": user.name,
                    "profile_picture": user.profile_picture,
                    "achievement_count": row.achievement_count,
                    "latest_achievement": row.latest_achievement.isoformat() if row.latest_achievement else None,
                })
        
        leaderboard_response = {
            "leaderboard": leaderboard,
            "total_users": len(leaderboard),
            "limit": limit,
            "offset": offset,
        }
        
        # Cache leaderboard for 15 minutes
        await self.cache.set(cache_key, json.dumps(leaderboard_response), expire=15 * MINUTE)
        
        return leaderboard_response
    
    async def get_recent_achievements_cached(self, limit: int = 20,
                                           background_tasks: Optional[BackgroundTasks] = None) -> List[Dict[str, Any]]:
        """
        Get recent achievements across all users with caching
        
        Args:
            limit: Number of recent achievements to return
            background_tasks: Optional background tasks
            
        Returns:
            List of recent achievements
        """
        cache_key = self._get_global_cache_key("recent_achievements", str(limit))
        
        # Try cache first
        cached_recent = await self.cache.get(cache_key)
        if cached_recent:
            return json.loads(cached_recent)
        
        # Get recent achievements from database
        query = (
            select(UserAchievement, User)
            .join(User, UserAchievement.user_id == User.id)
            .order_by(UserAchievement.earned_at.desc())
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        recent_achievements = result.fetchall()
        
        # Format recent achievements
        recent_list = []
        for achievement, user in recent_achievements:
            recent_list.append({
                "achievement_id": str(achievement.id),
                "user_id": str(user.id),
                "user_name": user.name,
                "profile_picture": user.profile_picture,
                "badge_name": achievement.badge_name,
                "badge_description": achievement.badge_description,
                "badge_icon": achievement.badge_icon,
                "badge_type": achievement.badge_type,
                "earned_at": achievement.earned_at.isoformat() if achievement.earned_at else None,
            })
        
        # Cache recent achievements for 5 minutes
        await self.cache.set(cache_key, json.dumps(recent_list), expire=5 * MINUTE)
        
        return recent_list
    
    async def _get_total_possible_achievements(self) -> int:
        """Get total number of possible achievements"""
        # This would typically come from a configuration or database
        # For now, return a reasonable estimate
        return 50  # Adjust based on your achievement system
    
    async def _get_user_rank_info(self, user_id: uuid.UUID, user_achievement_count: int) -> Dict[str, Any]:
        """Get user's rank information"""
        # Count users with more achievements
        query = (
            select(func.count(func.distinct(UserAchievement.user_id)))
            .select_from(UserAchievement)
            .group_by(UserAchievement.user_id)
            .having(func.count(UserAchievement.id) > user_achievement_count)
        )
        
        result = await self.db.execute(query)
        users_ahead = len(result.fetchall())
        
        return {
            "rank": users_ahead + 1,
            "total_users": users_ahead + 1,  # This would need a proper count
            "percentile": max(0, 100 - int((users_ahead / (users_ahead + 1)) * 100)),
        }
    
    def _calculate_achievement_streaks(self, achievements: List[UserAchievement]) -> Dict[str, Any]:
        """Calculate achievement streaks"""
        if not achievements:
            return {"current_streak": 0, "longest_streak": 0, "last_achievement": None}
        
        # Sort by earned date
        sorted_achievements = sorted(achievements, key=lambda x: x.earned_at)
        
        # Calculate streaks (simplified - daily streaks)
        streaks = {"current_streak": 0, "longest_streak": 0, "last_achievement": None}
        
        if sorted_achievements:
            streaks["last_achievement"] = sorted_achievements[-1].earned_at.isoformat()
            
            # Simple streak calculation - consecutive days with achievements
            current_streak = 1
            longest_streak = 1
            
            for i in range(1, len(sorted_achievements)):
                prev_date = sorted_achievements[i-1].earned_at.date()
                curr_date = sorted_achievements[i].earned_at.date()
                
                if (curr_date - prev_date).days == 1:
                    current_streak += 1
                    longest_streak = max(longest_streak, current_streak)
                else:
                    current_streak = 1
            
            streaks["current_streak"] = current_streak
            streaks["longest_streak"] = longest_streak
        
        return streaks
    
    def _create_achievement_timeline(self, achievements: List[UserAchievement]) -> List[Dict[str, Any]]:
        """Create monthly achievement timeline"""
        timeline = {}
        
        for achievement in achievements:
            month_key = achievement.earned_at.strftime("%Y-%m")
            if month_key not in timeline:
                timeline[month_key] = {
                    "month": month_key,
                    "count": 0,
                    "achievements": []
                }
            
            timeline[month_key]["count"] += 1
            timeline[month_key]["achievements"].append({
                "name": achievement.badge_name,
                "type": achievement.badge_type,
                "earned_at": achievement.earned_at.isoformat(),
            })
        
        # Sort by month and return as list
        return sorted(timeline.values(), key=lambda x: x["month"])


# Note: Dependency function is defined in the routes file