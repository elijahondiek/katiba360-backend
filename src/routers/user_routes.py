from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
import uuid

from src.database import get_db
from src.services.user_service import UserService, get_user_service
from src.schemas.user_schemas import (
    UserUpdateRequest, 
    UserResponse, 
    UserPreferenceCreate, 
    UserPreferenceResponse,
    UserLanguageCreate,
    UserLanguageResponse,
    UserInterestCreate,
    UserInterestResponse,
    UserAccessibilityCreate,
    UserAccessibilityResponse
)
from src.utils.custom_utils import generate_response

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/profile", response_model=Dict[str, Any])
async def get_user_profile(
    request: Request,
    user_service: UserService = Depends(get_user_service)
):
    """
    Get the current user's profile
    
    This endpoint returns the profile of the currently authenticated user.
    """
    try:
        user = request.state.user
        user_with_preferences = await user_service.get_user_with_preferences(user.id)
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="User profile retrieved successfully",
            customer_message="Your profile has been retrieved",
            body=UserResponse.from_orm(user_with_preferences).dict()
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
            response_message=str(e),
            customer_message="An unexpected error occurred",
            body=None
        )

@router.put("/profile", response_model=Dict[str, Any])
async def update_user_profile(
    profile_data: UserUpdateRequest,
    request: Request,
    user_service: UserService = Depends(get_user_service)
):
    """
    Update the current user's profile
    
    This endpoint updates the profile of the currently authenticated user.
    """
    try:
        user = request.state.user
        updated_user = await user_service.update_user_profile(user.id, profile_data)
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="User profile updated successfully",
            customer_message="Your profile has been updated",
            body=UserResponse.from_orm(updated_user).dict()
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
            response_message=str(e),
            customer_message="An unexpected error occurred",
            body=None
        )

@router.get("/preferences", response_model=Dict[str, Any])
async def get_user_preferences(
    request: Request,
    user_service: UserService = Depends(get_user_service)
):
    """
    Get the current user's preferences
    
    This endpoint returns the preferences of the currently authenticated user.
    """
    try:
        user = request.state.user
        preferences = await user_service.get_user_preferences(user.id)
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="User preferences retrieved successfully",
            customer_message="Your preferences have been retrieved",
            body=UserPreferenceResponse.from_orm(preferences).dict() if preferences else None
        )
    except HTTPException as e:
        return generate_response(
            status_code=e.status_code,
            response_message=e.detail,
            customer_message="Failed to retrieve preferences",
            body=None
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=str(e),
            customer_message="An unexpected error occurred",
            body=None
        )

@router.post("/preferences", response_model=Dict[str, Any])
async def create_user_preferences(
    preference_data: UserPreferenceCreate,
    request: Request,
    user_service: UserService = Depends(get_user_service)
):
    """
    Create or update the current user's preferences
    
    This endpoint creates or updates the preferences of the currently authenticated user.
    """
    try:
        user = request.state.user
        preferences = await user_service.create_or_update_preferences(user.id, preference_data)
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="User preferences created successfully",
            customer_message="Your preferences have been saved",
            body=UserPreferenceResponse.from_orm(preferences).dict()
        )
    except HTTPException as e:
        return generate_response(
            status_code=e.status_code,
            response_message=e.detail,
            customer_message="Failed to save preferences",
            body=None
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=str(e),
            customer_message="An unexpected error occurred",
            body=None
        )

@router.get("/languages", response_model=Dict[str, Any])
async def get_user_languages(
    request: Request,
    user_service: UserService = Depends(get_user_service)
):
    """
    Get the current user's languages
    
    This endpoint returns the languages of the currently authenticated user.
    """
    try:
        user = request.state.user
        languages = await user_service.get_user_languages(user.id)
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="User languages retrieved successfully",
            customer_message="Your languages have been retrieved",
            body=[UserLanguageResponse.from_orm(lang).dict() for lang in languages]
        )
    except HTTPException as e:
        return generate_response(
            status_code=e.status_code,
            response_message=e.detail,
            customer_message="Failed to retrieve languages",
            body=None
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=str(e),
            customer_message="An unexpected error occurred",
            body=None
        )

@router.post("/languages", response_model=Dict[str, Any])
async def add_user_language(
    language_data: UserLanguageCreate,
    request: Request,
    user_service: UserService = Depends(get_user_service)
):
    """
    Add a language to the current user's languages
    
    This endpoint adds a language to the currently authenticated user's languages.
    """
    try:
        user = request.state.user
        language = await user_service.add_user_language(user.id, language_data)
        
        return generate_response(
            status_code=status.HTTP_201_CREATED,
            response_message="User language added successfully",
            customer_message="Your language has been added",
            body=UserLanguageResponse.from_orm(language).dict()
        )
    except HTTPException as e:
        return generate_response(
            status_code=e.status_code,
            response_message=e.detail,
            customer_message="Failed to add language",
            body=None
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=str(e),
            customer_message="An unexpected error occurred",
            body=None
        )

@router.delete("/languages/{language_id}", response_model=Dict[str, Any])
async def remove_user_language(
    language_id: uuid.UUID,
    request: Request,
    user_service: UserService = Depends(get_user_service)
):
    """
    Remove a language from the current user's languages
    
    This endpoint removes a language from the currently authenticated user's languages.
    """
    try:
        user = request.state.user
        await user_service.remove_user_language(user.id, language_id)
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="User language removed successfully",
            customer_message="Your language has been removed",
            body=None
        )
    except HTTPException as e:
        return generate_response(
            status_code=e.status_code,
            response_message=e.detail,
            customer_message="Failed to remove language",
            body=None
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=str(e),
            customer_message="An unexpected error occurred",
            body=None
        )

@router.get("/interests", response_model=Dict[str, Any])
async def get_user_interests(
    request: Request,
    user_service: UserService = Depends(get_user_service)
):
    """
    Get the current user's interests
    
    This endpoint returns the interests of the currently authenticated user.
    """
    try:
        user = request.state.user
        interests = await user_service.get_user_interests(user.id)
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="User interests retrieved successfully",
            customer_message="Your interests have been retrieved",
            body=[UserInterestResponse.from_orm(interest).dict() for interest in interests]
        )
    except HTTPException as e:
        return generate_response(
            status_code=e.status_code,
            response_message=e.detail,
            customer_message="Failed to retrieve interests",
            body=None
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=str(e),
            customer_message="An unexpected error occurred",
            body=None
        )

@router.post("/interests", response_model=Dict[str, Any])
async def add_user_interest(
    interest_data: UserInterestCreate,
    request: Request,
    user_service: UserService = Depends(get_user_service)
):
    """
    Add an interest to the current user's interests
    
    This endpoint adds an interest to the currently authenticated user's interests.
    """
    try:
        user = request.state.user
        interest = await user_service.add_user_interest(user.id, interest_data)
        
        return generate_response(
            status_code=status.HTTP_201_CREATED,
            response_message="User interest added successfully",
            customer_message="Your interest has been added",
            body=UserInterestResponse.from_orm(interest).dict()
        )
    except HTTPException as e:
        return generate_response(
            status_code=e.status_code,
            response_message=e.detail,
            customer_message="Failed to add interest",
            body=None
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=str(e),
            customer_message="An unexpected error occurred",
            body=None
        )

@router.delete("/interests/{interest_id}", response_model=Dict[str, Any])
async def remove_user_interest(
    interest_id: uuid.UUID,
    request: Request,
    user_service: UserService = Depends(get_user_service)
):
    """
    Remove an interest from the current user's interests
    
    This endpoint removes an interest from the currently authenticated user's interests.
    """
    try:
        user = request.state.user
        await user_service.remove_user_interest(user.id, interest_id)
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="User interest removed successfully",
            customer_message="Your interest has been removed",
            body=None
        )
    except HTTPException as e:
        return generate_response(
            status_code=e.status_code,
            response_message=e.detail,
            customer_message="Failed to remove interest",
            body=None
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=str(e),
            customer_message="An unexpected error occurred",
            body=None
        )

@router.get("/accessibility", response_model=Dict[str, Any])
async def get_user_accessibility(
    request: Request,
    user_service: UserService = Depends(get_user_service)
):
    """
    Get the current user's accessibility settings
    
    This endpoint returns the accessibility settings of the currently authenticated user.
    """
    try:
        user = request.state.user
        accessibility = await user_service.get_user_accessibility(user.id)
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="User accessibility settings retrieved successfully",
            customer_message="Your accessibility settings have been retrieved",
            body=UserAccessibilityResponse.from_orm(accessibility).dict() if accessibility else None
        )
    except HTTPException as e:
        return generate_response(
            status_code=e.status_code,
            response_message=e.detail,
            customer_message="Failed to retrieve accessibility settings",
            body=None
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=str(e),
            customer_message="An unexpected error occurred",
            body=None
        )

@router.post("/accessibility", response_model=Dict[str, Any])
async def create_user_accessibility(
    accessibility_data: UserAccessibilityCreate,
    request: Request,
    user_service: UserService = Depends(get_user_service)
):
    """
    Create or update the current user's accessibility settings
    
    This endpoint creates or updates the accessibility settings of the currently authenticated user.
    """
    try:
        user = request.state.user
        accessibility = await user_service.create_or_update_accessibility(user.id, accessibility_data)
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="User accessibility settings created successfully",
            customer_message="Your accessibility settings have been saved",
            body=UserAccessibilityResponse.from_orm(accessibility).dict()
        )
    except HTTPException as e:
        return generate_response(
            status_code=e.status_code,
            response_message=e.detail,
            customer_message="Failed to save accessibility settings",
            body=None
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=str(e),
            customer_message="An unexpected error occurred",
            body=None
        )
