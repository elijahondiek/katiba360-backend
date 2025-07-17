from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
import uuid

from src.database import get_db
from src.services.achievement_service import AchievementService, get_achievement_service
from src.services.cached_achievement_service import CachedAchievementService
from src.utils.cache import CacheManager
from src.schemas.user_schemas import (
    UserAchievementCreate,
    UserAchievementResponse
)
from src.utils.custom_utils import generate_response

router = APIRouter(prefix="/achievements", tags=["Achievements"])

# Cache manager dependency
async def get_cache_manager():
    from redis.asyncio import Redis
    from src.core.config import settings
    
    redis_client = Redis.from_url(settings.redis_url)
    cache_manager = CacheManager(redis_client, prefix="katiba360")
    
    try:
        yield cache_manager
    finally:
        await redis_client.close()

# Cached achievement service dependency
async def get_cached_achievement_service(
    db: AsyncSession = Depends(get_db),
    cache_manager: CacheManager = Depends(get_cache_manager)
) -> CachedAchievementService:
    return CachedAchievementService(db, cache_manager)

@router.get("", response_model=Dict[str, Any])
async def get_user_achievements(
    request: Request,
    background_tasks: BackgroundTasks,
    achievement_service: CachedAchievementService = Depends(get_cached_achievement_service)
):
    """
    Get the current user's achievements with caching
    
    This endpoint returns all achievements of the currently authenticated user.
    Results are cached for 30 minutes.
    """
    try:
        user = request.state.user
        achievements = await achievement_service.get_user_achievements_cached(user.id, background_tasks)
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="User achievements retrieved successfully",
            customer_message="Your achievements have been retrieved",
            body=[
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
            ]
        )
    except HTTPException as e:
        return generate_response(
            status_code=e.status_code,
            response_message=e.detail,
            customer_message="Failed to retrieve achievements",
            body=None
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=str(e),
            customer_message="An unexpected error occurred",
            body=None
        )

@router.get("/types", response_model=Dict[str, Any])
async def get_achievement_types(
    request: Request,
    achievement_service: AchievementService = Depends(get_achievement_service)
):
    """
    Get all available achievement types
    
    This endpoint returns all available achievement types.
    """
    try:
        achievement_types = await achievement_service.get_achievement_types()
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="Achievement types retrieved successfully",
            customer_message="Achievement types have been retrieved",
            body=achievement_types
        )
    except HTTPException as e:
        return generate_response(
            status_code=e.status_code,
            response_message=e.detail,
            customer_message="Failed to retrieve achievement types",
            body=None
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=str(e),
            customer_message="An unexpected error occurred",
            body=None
        )

@router.get("/summary", response_model=Dict[str, Any])
async def get_achievement_summary(
    request: Request,
    achievement_service: AchievementService = Depends(get_achievement_service)
):
    """
    Get the current user's achievement summary
    
    This endpoint returns a summary of achievements for the currently authenticated user,
    including total points and completion percentage.
    """
    try:
        user = request.state.user
        summary = await achievement_service.get_achievement_summary(user.id)
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="Achievement summary retrieved successfully",
            customer_message="Your achievement summary has been retrieved",
            body=summary
        )
    except HTTPException as e:
        return generate_response(
            status_code=e.status_code,
            response_message=e.detail,
            customer_message="Failed to retrieve achievement summary",
            body=None
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=str(e),
            customer_message="An unexpected error occurred",
            body=None
        )

@router.get("/{achievement_id}", response_model=Dict[str, Any])
async def get_achievement(
    achievement_id: uuid.UUID,
    request: Request,
    achievement_service: AchievementService = Depends(get_achievement_service)
):
    """
    Get a specific achievement
    
    This endpoint returns a specific achievement of the currently authenticated user.
    """
    try:
        user = request.state.user
        achievement = await achievement_service.get_achievement(achievement_id, user.id)
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="Achievement retrieved successfully",
            customer_message="Your achievement has been retrieved",
            body=UserAchievementResponse.from_orm(achievement).dict()
        )
    except HTTPException as e:
        return generate_response(
            status_code=e.status_code,
            response_message=e.detail,
            customer_message="Failed to retrieve achievement",
            body=None
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=str(e),
            customer_message="An unexpected error occurred",
            body=None
        )

@router.get("/type/{achievement_type}", response_model=Dict[str, Any])
async def get_achievement_by_type(
    achievement_type: str,
    request: Request,
    achievement_service: AchievementService = Depends(get_achievement_service)
):
    """
    Get an achievement by type
    
    This endpoint returns an achievement of a specific type for the currently authenticated user.
    """
    try:
        user = request.state.user
        achievement = await achievement_service.get_achievement_by_type(achievement_type, user.id)
        
        if not achievement:
            return generate_response(
                status_code=status.HTTP_404_NOT_FOUND,
                response_message=f"Achievement of type {achievement_type} not found",
                customer_message="Achievement not found",
                body=None
            )
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="Achievement retrieved successfully",
            customer_message="Your achievement has been retrieved",
            body=UserAchievementResponse.from_orm(achievement).dict()
        )
    except HTTPException as e:
        return generate_response(
            status_code=e.status_code,
            response_message=e.detail,
            customer_message="Failed to retrieve achievement",
            body=None
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=str(e),
            customer_message="An unexpected error occurred",
            body=None
        )

# This endpoint would typically be called by an internal service, not directly by users
@router.post("", response_model=Dict[str, Any])
async def award_achievement(
    achievement_data: UserAchievementCreate,
    request: Request,
    achievement_service: AchievementService = Depends(get_achievement_service)
):
    """
    Award an achievement to the current user
    
    This endpoint awards an achievement to the currently authenticated user.
    """
    try:
        user = request.state.user
        achievement = await achievement_service.award_achievement(user.id, achievement_data)
        
        return generate_response(
            status_code=status.HTTP_201_CREATED,
            response_message="Achievement awarded successfully",
            customer_message="Congratulations! You've earned a new achievement",
            body=UserAchievementResponse.from_orm(achievement).dict()
        )
    except HTTPException as e:
        return generate_response(
            status_code=e.status_code,
            response_message=e.detail,
            customer_message="Failed to award achievement",
            body=None
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=str(e),
            customer_message="An unexpected error occurred",
            body=None
        )
