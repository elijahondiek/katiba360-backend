"""
Enhanced User Routes with Redis caching and proper cache invalidation.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
import uuid

from src.database import get_db
from src.services.cached_user_service import CachedUserService, get_cached_user_service
from src.schemas.user_schemas import (
    UserUpdateRequest, 
    UserResponse, 
    UserPreferenceCreate, 
    UserPreferenceResponse,
    UserPreferenceUpdate,
    UserLanguageCreate,
    UserLanguageResponse,
    UserInterestCreate,
    UserInterestResponse,
    UserAccessibilityCreate,
    UserAccessibilityResponse,
    UserAccessibilityUpdate
)
from src.utils.custom_utils import generate_response
from src.utils.cache import CacheManager

router = APIRouter(prefix="/users", tags=["Users - Cached"])

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


@router.get("/profile", response_model=Dict[str, Any])
async def get_user_profile_cached(
    request: Request,
    background_tasks: BackgroundTasks,
    user_service: CachedUserService = Depends(get_cached_user_service)
):
    """
    Get the current user's profile with caching
    
    This endpoint returns the profile of the currently authenticated user.
    Results are cached for 1 hour and automatically invalidated on profile updates.
    """
    try:
        user = request.state.user
        user_profile = await user_service.get_user_by_id_cached(user.id, background_tasks)
        
        if not user_profile:
            return generate_response(
                status_code=status.HTTP_404_NOT_FOUND,
                response_message="User not found",
                customer_message="User profile not found",
                body=None
            )
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="User profile retrieved successfully",
            customer_message="Your profile has been retrieved",
            body={
                "user": {
                    "id": str(user_profile.id),
                    "email": user_profile.email,
                    "name": user_profile.name,
                    "profile_picture": user_profile.profile_picture,
                    "created_at": user_profile.created_at.isoformat() if user_profile.created_at else None,
                    "updated_at": user_profile.updated_at.isoformat() if user_profile.updated_at else None,
                    "last_login": user_profile.last_login.isoformat() if user_profile.last_login else None,
                    "is_active": user_profile.is_active,
                    "privacy_settings": user_profile.privacy_settings,
                    "notification_settings": user_profile.notification_settings,
                },
                "cache_info": {
                    "cached": True,
                    "cache_key": f"user:{user.id}:profile"
                }
            }
        )
    except HTTPException as e:
        return generate_response(
            status_code=e.status_code,
            response_message=e.detail,
            customer_message="Failed to retrieve profile",
            body=None
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=f"Internal server error: {str(e)}",
            customer_message="An error occurred while retrieving your profile",
            body=None
        )


@router.get("/profile/full", response_model=Dict[str, Any])
async def get_full_user_profile_cached(
    request: Request,
    background_tasks: BackgroundTasks,
    user_service: CachedUserService = Depends(get_cached_user_service)
):
    """
    Get the current user's complete profile with all related data (cached)
    
    This endpoint returns the complete profile including preferences, languages,
    accessibility settings, and interests. Results are cached for 1 hour.
    """
    try:
        user = request.state.user
        full_profile = await user_service.get_full_user_profile_cached(user.id, background_tasks)
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="Full user profile retrieved successfully",
            customer_message="Your complete profile has been retrieved",
            body={
                "profile": full_profile,
                "cache_info": {
                    "cached": True,
                    "cache_key": f"user:{user.id}:full_profile"
                }
            }
        )
    except HTTPException as e:
        return generate_response(
            status_code=e.status_code,
            response_message=e.detail,
            customer_message="Failed to retrieve full profile",
            body=None
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=f"Internal server error: {str(e)}",
            customer_message="An error occurred while retrieving your profile",
            body=None
        )


@router.put("/profile", response_model=Dict[str, Any])
async def update_user_profile_cached(
    request: Request,
    background_tasks: BackgroundTasks,
    update_data: UserUpdateRequest,
    user_service: CachedUserService = Depends(get_cached_user_service)
):
    """
    Update the current user's profile with cache invalidation
    
    This endpoint updates the user's profile and automatically invalidates
    all related cache entries.
    """
    try:
        user = request.state.user
        updated_user = await user_service.update_user_profile_cached(
            user.id, update_data, background_tasks
        )
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="User profile updated successfully",
            customer_message="Your profile has been updated",
            body={
                "user": {
                    "id": str(updated_user.id),
                    "email": updated_user.email,
                    "name": updated_user.name,
                    "profile_picture": updated_user.profile_picture,
                    "updated_at": updated_user.updated_at.isoformat() if updated_user.updated_at else None,
                },
                "cache_info": {
                    "invalidated": True,
                    "invalidated_patterns": [
                        f"user:{user.id}:profile",
                        f"user:{user.id}:full_profile",
                        f"user:{user.id}:stats"
                    ]
                }
            }
        )
    except HTTPException as e:
        return generate_response(
            status_code=e.status_code,
            response_message=e.detail,
            customer_message="Failed to update profile",
            body=None
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=f"Internal server error: {str(e)}",
            customer_message="An error occurred while updating your profile",
            body=None
        )


@router.get("/preferences", response_model=Dict[str, Any])
async def get_user_preferences_cached(
    request: Request,
    background_tasks: BackgroundTasks,
    user_service: CachedUserService = Depends(get_cached_user_service)
):
    """
    Get user preferences with caching
    
    This endpoint returns the user's preferences.
    Results are cached for 1 hour.
    """
    try:
        user = request.state.user
        preferences = await user_service.get_user_preferences_cached(user.id, background_tasks)
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="User preferences retrieved successfully",
            customer_message="Your preferences have been retrieved",
            body={
                "preferences": [
                    {
                        "preference_key": pref.preference_key,
                        "preference_value": pref.preference_value,
                        "updated_at": pref.updated_at.isoformat() if pref.updated_at else None,
                    }
                    for pref in preferences
                ],
                "cache_info": {
                    "cached": True,
                    "cache_key": f"user:{user.id}:preferences"
                }
            }
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=f"Internal server error: {str(e)}",
            customer_message="An error occurred while retrieving your preferences",
            body=None
        )


@router.put("/preferences", response_model=Dict[str, Any])
async def update_user_preferences_cached(
    request: Request,
    background_tasks: BackgroundTasks,
    preferences: List[UserPreferenceUpdate],
    user_service: CachedUserService = Depends(get_cached_user_service)
):
    """
    Update user preferences with cache invalidation
    
    This endpoint updates user preferences and invalidates related cache.
    """
    try:
        user = request.state.user
        updated_preferences = await user_service.update_user_preferences_cached(
            user.id, preferences, background_tasks
        )
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="User preferences updated successfully",
            customer_message="Your preferences have been updated",
            body={
                "preferences": [
                    {
                        "preference_key": pref.preference_key,
                        "preference_value": pref.preference_value,
                        "updated_at": pref.updated_at.isoformat() if pref.updated_at else None,
                    }
                    for pref in updated_preferences
                ],
                "cache_info": {
                    "invalidated": True,
                    "invalidated_patterns": [
                        f"user:{user.id}:preferences",
                        f"user:{user.id}:full_profile",
                        f"user:{user.id}:stats"
                    ]
                }
            }
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=f"Internal server error: {str(e)}",
            customer_message="An error occurred while updating your preferences",
            body=None
        )


@router.get("/languages", response_model=Dict[str, Any])
async def get_user_languages_cached(
    request: Request,
    background_tasks: BackgroundTasks,
    user_service: CachedUserService = Depends(get_cached_user_service)
):
    """
    Get user languages with caching
    
    This endpoint returns the user's language preferences.
    Results are cached for 1 hour.
    """
    try:
        user = request.state.user
        languages = await user_service.get_user_languages_cached(user.id, background_tasks)
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="User languages retrieved successfully",
            customer_message="Your language preferences have been retrieved",
            body={
                "languages": [
                    {
                        "language_code": lang.language_code,
                        "is_primary": lang.is_primary,
                        "proficiency_level": lang.proficiency_level,
                        "created_at": lang.created_at.isoformat() if lang.created_at else None,
                    }
                    for lang in languages
                ],
                "cache_info": {
                    "cached": True,
                    "cache_key": f"user:{user.id}:languages"
                }
            }
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=f"Internal server error: {str(e)}",
            customer_message="An error occurred while retrieving your languages",
            body=None
        )


@router.get("/accessibility", response_model=Dict[str, Any])
async def get_user_accessibility_cached(
    request: Request,
    background_tasks: BackgroundTasks,
    user_service: CachedUserService = Depends(get_cached_user_service)
):
    """
    Get user accessibility settings with caching
    
    This endpoint returns the user's accessibility preferences.
    Results are cached for 1 hour.
    """
    try:
        user = request.state.user
        accessibility = await user_service.get_user_accessibility_cached(user.id, background_tasks)
        
        if not accessibility:
            return generate_response(
                status_code=status.HTTP_404_NOT_FOUND,
                response_message="Accessibility settings not found",
                customer_message="No accessibility settings found",
                body=None
            )
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="User accessibility settings retrieved successfully",
            customer_message="Your accessibility preferences have been retrieved",
            body={
                "accessibility": {
                    "high_contrast": accessibility.high_contrast,
                    "large_text": accessibility.large_text,
                    "screen_reader": accessibility.screen_reader,
                    "reduced_motion": accessibility.reduced_motion,
                    "keyboard_navigation": accessibility.keyboard_navigation,
                    "updated_at": accessibility.updated_at.isoformat() if accessibility.updated_at else None,
                },
                "cache_info": {
                    "cached": True,
                    "cache_key": f"user:{user.id}:accessibility"
                }
            }
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=f"Internal server error: {str(e)}",
            customer_message="An error occurred while retrieving your accessibility settings",
            body=None
        )


@router.put("/accessibility", response_model=Dict[str, Any])
async def update_user_accessibility_cached(
    request: Request,
    background_tasks: BackgroundTasks,
    accessibility_data: UserAccessibilityUpdate,
    user_service: CachedUserService = Depends(get_cached_user_service)
):
    """
    Update user accessibility settings with cache invalidation
    
    This endpoint updates user accessibility settings and invalidates related cache.
    """
    try:
        user = request.state.user
        updated_accessibility = await user_service.update_user_accessibility_cached(
            user.id, accessibility_data, background_tasks
        )
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="User accessibility settings updated successfully",
            customer_message="Your accessibility settings have been updated",
            body={
                "accessibility": {
                    "high_contrast": updated_accessibility.high_contrast,
                    "large_text": updated_accessibility.large_text,
                    "screen_reader": updated_accessibility.screen_reader,
                    "reduced_motion": updated_accessibility.reduced_motion,
                    "keyboard_navigation": updated_accessibility.keyboard_navigation,
                    "updated_at": updated_accessibility.updated_at.isoformat() if updated_accessibility.updated_at else None,
                },
                "cache_info": {
                    "invalidated": True,
                    "invalidated_patterns": [
                        f"user:{user.id}:accessibility",
                        f"user:{user.id}:full_profile",
                        f"user:{user.id}:stats"
                    ]
                }
            }
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=f"Internal server error: {str(e)}",
            customer_message="An error occurred while updating your accessibility settings",
            body=None
        )


@router.get("/interests", response_model=Dict[str, Any])
async def get_user_interests_cached(
    request: Request,
    background_tasks: BackgroundTasks,
    user_service: CachedUserService = Depends(get_cached_user_service)
):
    """
    Get user interests with caching
    
    This endpoint returns the user's interests.
    Results are cached for 1 hour.
    """
    try:
        user = request.state.user
        interests = await user_service.get_user_interests_cached(user.id, background_tasks)
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="User interests retrieved successfully",
            customer_message="Your interests have been retrieved",
            body={
                "interests": [
                    {
                        "category_name": interest.category.name if interest.category else None,
                        "interest_level": interest.interest_level,
                        "created_at": interest.created_at.isoformat() if interest.created_at else None,
                    }
                    for interest in interests
                ],
                "cache_info": {
                    "cached": True,
                    "cache_key": f"user:{user.id}:interests"
                }
            }
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=f"Internal server error: {str(e)}",
            customer_message="An error occurred while retrieving your interests",
            body=None
        )


@router.get("/stats", response_model=Dict[str, Any])
async def get_user_stats_cached(
    request: Request,
    background_tasks: BackgroundTasks,
    user_service: CachedUserService = Depends(get_cached_user_service)
):
    """
    Get user statistics with caching
    
    This endpoint returns comprehensive user statistics.
    Results are cached for 1 hour.
    """
    try:
        user = request.state.user
        stats = await user_service.get_user_stats_cached(user.id, background_tasks)
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="User statistics retrieved successfully",
            customer_message="Your statistics have been retrieved",
            body={
                "stats": stats,
                "cache_info": {
                    "cached": True,
                    "cache_key": f"user:{user.id}:stats"
                }
            }
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=f"Internal server error: {str(e)}",
            customer_message="An error occurred while retrieving your statistics",
            body=None
        )


@router.post("/cache/invalidate", response_model=Dict[str, Any])
async def invalidate_user_cache(
    request: Request,
    background_tasks: BackgroundTasks,
    user_service: CachedUserService = Depends(get_cached_user_service)
):
    """
    Manually invalidate user cache
    
    This endpoint allows manual cache invalidation for debugging or maintenance.
    """
    try:
        user = request.state.user
        await user_service._invalidate_user_cache(str(user.id), background_tasks)
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="User cache invalidated successfully",
            customer_message="Your cache has been cleared",
            body={
                "cache_info": {
                    "invalidated": True,
                    "user_id": str(user.id),
                    "timestamp": "now"
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