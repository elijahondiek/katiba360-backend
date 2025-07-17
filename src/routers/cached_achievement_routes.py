"""
Enhanced Achievement Routes with Redis caching and proper cache invalidation.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
import uuid

from src.database import get_db
from src.services.cached_achievement_service import CachedAchievementService, get_cached_achievement_service
from src.schemas.user_schemas import BadgeType, UserAchievementCreate
from src.utils.custom_utils import generate_response

router = APIRouter(prefix="/achievements", tags=["Achievements - Cached"])


@router.get("/", response_model=Dict[str, Any])
async def get_user_achievements_cached(
    request: Request,
    background_tasks: BackgroundTasks,
    achievement_service: CachedAchievementService = Depends(get_cached_achievement_service)
):
    """
    Get user achievements with caching
    
    This endpoint returns all achievements for the current user.
    Results are cached for 30 minutes.
    """
    try:
        user = request.state.user
        achievements = await achievement_service.get_user_achievements_cached(user.id, background_tasks)
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="User achievements retrieved successfully",
            customer_message="Your achievements have been retrieved",
            body={
                "achievements": [
                    {
                        "id": str(achievement.id),
                        "badge_type": achievement.badge_type,
                        "badge_name": achievement.badge_name,
                        "badge_description": achievement.badge_description,
                        "badge_icon": achievement.badge_icon,
                        "earned_at": achievement.earned_at.isoformat() if achievement.earned_at else None,
                        "achievement_data": achievement.achievement_data,
                    }
                    for achievement in achievements
                ],
                "total_achievements": len(achievements),
                "cache_info": {
                    "cached": True,
                    "cache_key": f"achievements:{user.id}:achievements",
                    "cache_duration": "30 minutes"
                }
            }
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=f"Internal server error: {str(e)}",
            customer_message="An error occurred while retrieving your achievements",
            body=None
        )


@router.get("/summary", response_model=Dict[str, Any])
async def get_user_achievement_summary_cached(
    request: Request,
    background_tasks: BackgroundTasks,
    achievement_service: CachedAchievementService = Depends(get_cached_achievement_service)
):
    """
    Get user achievement summary with caching
    
    This endpoint returns a summary of user achievements including statistics,
    recent achievements, and completion percentage.
    Results are cached for 30 minutes.
    """
    try:
        user = request.state.user
        summary = await achievement_service.get_user_achievement_summary_cached(user.id, background_tasks)
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="User achievement summary retrieved successfully",
            customer_message="Your achievement summary has been retrieved",
            body={
                "summary": summary,
                "cache_info": {
                    "cached": True,
                    "cache_key": f"achievements:{user.id}:summary",
                    "cache_duration": "30 minutes"
                }
            }
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=f"Internal server error: {str(e)}",
            customer_message="An error occurred while retrieving your achievement summary",
            body=None
        )


@router.get("/stats", response_model=Dict[str, Any])
async def get_user_achievement_stats_cached(
    request: Request,
    background_tasks: BackgroundTasks,
    achievement_service: CachedAchievementService = Depends(get_cached_achievement_service)
):
    """
    Get detailed user achievement statistics with caching
    
    This endpoint returns comprehensive achievement statistics including
    timeline, streaks, rankings, and detailed breakdowns.
    Results are cached for 30 minutes.
    """
    try:
        user = request.state.user
        stats = await achievement_service.get_user_achievement_stats_cached(user.id, background_tasks)
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="User achievement statistics retrieved successfully",
            customer_message="Your achievement statistics have been retrieved",
            body={
                "stats": stats,
                "cache_info": {
                    "cached": True,
                    "cache_key": f"achievements:{user.id}:stats",
                    "cache_duration": "30 minutes"
                }
            }
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=f"Internal server error: {str(e)}",
            customer_message="An error occurred while retrieving your achievement statistics",
            body=None
        )


@router.post("/award", response_model=Dict[str, Any])
async def award_achievement_cached(
    request: Request,
    background_tasks: BackgroundTasks,
    badge_type: BadgeType,
    achievement_data: Optional[Dict[str, Any]] = None,
    achievement_service: CachedAchievementService = Depends(get_cached_achievement_service)
):
    """
    Award achievement to user with cache invalidation
    
    This endpoint awards a new achievement to the user and invalidates
    all related cache entries.
    """
    try:
        user = request.state.user
        achievement = await achievement_service.award_achievement_cached(
            user.id, badge_type, achievement_data, background_tasks
        )
        
        return generate_response(
            status_code=status.HTTP_201_CREATED,
            response_message="Achievement awarded successfully",
            customer_message="Congratulations! You've earned a new achievement",
            body={
                "achievement": {
                    "id": str(achievement.id),
                    "badge_type": achievement.badge_type,
                    "badge_name": achievement.badge_name,
                    "badge_description": achievement.badge_description,
                    "badge_icon": achievement.badge_icon,
                    "earned_at": achievement.earned_at.isoformat() if achievement.earned_at else None,
                    "achievement_data": achievement.achievement_data,
                },
                "cache_info": {
                    "invalidated": True,
                    "invalidated_patterns": [
                        f"achievements:{user.id}:achievements",
                        f"achievements:{user.id}:summary",
                        f"achievements:{user.id}:stats",
                        "achievements:global:leaderboard",
                        "achievements:global:recent_achievements"
                    ]
                }
            }
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=f"Internal server error: {str(e)}",
            customer_message="An error occurred while awarding the achievement",
            body=None
        )


@router.get("/leaderboard", response_model=Dict[str, Any])
async def get_achievement_leaderboard_cached(
    background_tasks: BackgroundTasks,
    limit: int = Query(10, ge=1, le=100, description="Number of users to return"),
    offset: int = Query(0, ge=0, description="Number of users to skip"),
    achievement_service: CachedAchievementService = Depends(get_cached_achievement_service)
):
    """
    Get achievement leaderboard with caching
    
    This endpoint returns the global achievement leaderboard.
    Results are cached for 15 minutes.
    """
    try:
        leaderboard = await achievement_service.get_leaderboard_cached(
            limit, offset, background_tasks
        )
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="Achievement leaderboard retrieved successfully",
            customer_message="The achievement leaderboard has been retrieved",
            body={
                "leaderboard": leaderboard,
                "cache_info": {
                    "cached": True,
                    "cache_key": f"achievements:global:leaderboard:{limit}:{offset}",
                    "cache_duration": "15 minutes"
                }
            }
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=f"Internal server error: {str(e)}",
            customer_message="An error occurred while retrieving the leaderboard",
            body=None
        )


@router.get("/recent", response_model=Dict[str, Any])
async def get_recent_achievements_cached(
    background_tasks: BackgroundTasks,
    limit: int = Query(20, ge=1, le=50, description="Number of recent achievements to return"),
    achievement_service: CachedAchievementService = Depends(get_cached_achievement_service)
):
    """
    Get recent achievements across all users with caching
    
    This endpoint returns recent achievements from all users.
    Results are cached for 5 minutes.
    """
    try:
        recent_achievements = await achievement_service.get_recent_achievements_cached(
            limit, background_tasks
        )
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="Recent achievements retrieved successfully",
            customer_message="Recent achievements have been retrieved",
            body={
                "recent_achievements": recent_achievements,
                "total_shown": len(recent_achievements),
                "cache_info": {
                    "cached": True,
                    "cache_key": f"achievements:global:recent_achievements:{limit}",
                    "cache_duration": "5 minutes"
                }
            }
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=f"Internal server error: {str(e)}",
            customer_message="An error occurred while retrieving recent achievements",
            body=None
        )


@router.get("/badges/{badge_type}", response_model=Dict[str, Any])
async def get_user_badges_by_type_cached(
    request: Request,
    background_tasks: BackgroundTasks,
    badge_type: str,
    achievement_service: CachedAchievementService = Depends(get_cached_achievement_service)
):
    """
    Get user badges by type with caching
    
    This endpoint returns all badges of a specific type for the current user.
    Results are cached for 30 minutes.
    """
    try:
        user = request.state.user
        achievements = await achievement_service.get_user_achievements_cached(user.id, background_tasks)
        
        # Filter by badge type
        filtered_achievements = [
            achievement for achievement in achievements
            if achievement.badge_type == badge_type
        ]
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message=f"User {badge_type} badges retrieved successfully",
            customer_message=f"Your {badge_type} badges have been retrieved",
            body={
                "badges": [
                    {
                        "id": str(achievement.id),
                        "badge_name": achievement.badge_name,
                        "badge_description": achievement.badge_description,
                        "badge_icon": achievement.badge_icon,
                        "earned_at": achievement.earned_at.isoformat() if achievement.earned_at else None,
                        "achievement_data": achievement.achievement_data,
                    }
                    for achievement in filtered_achievements
                ],
                "badge_type": badge_type,
                "total_badges": len(filtered_achievements),
                "cache_info": {
                    "cached": True,
                    "cache_key": f"achievements:{user.id}:achievements",
                    "filtered_by": badge_type
                }
            }
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=f"Internal server error: {str(e)}",
            customer_message="An error occurred while retrieving your badges",
            body=None
        )


@router.post("/cache/invalidate", response_model=Dict[str, Any])
async def invalidate_achievement_cache(
    request: Request,
    background_tasks: BackgroundTasks,
    achievement_service: CachedAchievementService = Depends(get_cached_achievement_service)
):
    """
    Manually invalidate achievement cache
    
    This endpoint allows manual cache invalidation for debugging or maintenance.
    """
    try:
        user = request.state.user
        await achievement_service._invalidate_user_achievements_cache(str(user.id), background_tasks)
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="Achievement cache invalidated successfully",
            customer_message="Your achievement cache has been cleared",
            body={
                "cache_info": {
                    "invalidated": True,
                    "user_id": str(user.id),
                    "timestamp": "now",
                    "invalidated_patterns": [
                        f"achievements:{user.id}:achievements",
                        f"achievements:{user.id}:summary",
                        f"achievements:{user.id}:stats",
                        "achievements:global:leaderboard",
                        "achievements:global:recent_achievements"
                    ]
                }
            }
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=f"Internal server error: {str(e)}",
            customer_message="An error occurred while clearing your cache",
            body=None
        )


@router.post("/cache/invalidate/global", response_model=Dict[str, Any])
async def invalidate_global_achievement_cache(
    background_tasks: BackgroundTasks,
    achievement_service: CachedAchievementService = Depends(get_cached_achievement_service)
):
    """
    Manually invalidate global achievement cache
    
    This endpoint allows manual invalidation of global cache (leaderboards, recent achievements).
    Typically used for maintenance or when global data needs refresh.
    """
    try:
        await achievement_service._invalidate_global_cache(background_tasks)
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="Global achievement cache invalidated successfully",
            customer_message="Global achievement cache has been cleared",
            body={
                "cache_info": {
                    "invalidated": True,
                    "scope": "global",
                    "timestamp": "now",
                    "invalidated_patterns": [
                        "achievements:global:leaderboard",
                        "achievements:global:top_achievers",
                        "achievements:global:stats",
                        "achievements:global:recent_achievements"
                    ]
                }
            }
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=f"Internal server error: {str(e)}",
            customer_message="An error occurred while clearing the global cache",
            body=None
        )