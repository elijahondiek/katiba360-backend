from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
import uuid

from src.database import get_db
from src.services.onboarding_service import OnboardingService, get_onboarding_service
from src.schemas.user_schemas import (
    OnboardingProgressResponse,
    OnboardingProgressUpdate
)
from src.utils.custom_utils import generate_response

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])

@router.get("/progress", response_model=Dict[str, Any])
async def get_onboarding_progress(
    request: Request,
    onboarding_service: OnboardingService = Depends(get_onboarding_service)
):
    """
    Get the current user's onboarding progress
    
    This endpoint returns the onboarding progress of the currently authenticated user.
    """
    try:
        user = request.state.user
        progress = await onboarding_service.get_onboarding_progress(user.id)
        
        if not progress:
            # Initialize onboarding if it doesn't exist
            progress = await onboarding_service.initialize_onboarding(user.id)
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="Onboarding progress retrieved successfully",
            customer_message="Your onboarding progress has been retrieved",
            body=OnboardingProgressResponse.from_orm(progress).dict()
        )
    except HTTPException as e:
        return generate_response(
            status_code=e.status_code,
            response_message=e.detail,
            customer_message="Failed to retrieve onboarding progress",
            body=None
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=str(e),
            customer_message="An unexpected error occurred",
            body=None
        )

@router.put("/progress", response_model=Dict[str, Any])
async def update_onboarding_progress(
    progress_data: OnboardingProgressUpdate,
    request: Request,
    onboarding_service: OnboardingService = Depends(get_onboarding_service)
):
    """
    Update the current user's onboarding progress
    
    This endpoint updates the onboarding progress of the currently authenticated user.
    """
    try:
        user = request.state.user
        progress = await onboarding_service.update_onboarding_progress(user.id, progress_data)
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="Onboarding progress updated successfully",
            customer_message="Your onboarding progress has been updated",
            body=OnboardingProgressResponse.from_orm(progress).dict()
        )
    except HTTPException as e:
        return generate_response(
            status_code=e.status_code,
            response_message=e.detail,
            customer_message="Failed to update onboarding progress",
            body=None
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=str(e),
            customer_message="An unexpected error occurred",
            body=None
        )

@router.post("/complete", response_model=Dict[str, Any])
async def complete_onboarding(
    request: Request,
    onboarding_service: OnboardingService = Depends(get_onboarding_service)
):
    """
    Mark onboarding as complete
    
    This endpoint marks the onboarding as complete for the currently authenticated user.
    """
    try:
        user = request.state.user
        progress = await onboarding_service.complete_onboarding(user.id)
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="Onboarding completed successfully",
            customer_message="Congratulations! You've completed the onboarding process",
            body=OnboardingProgressResponse.from_orm(progress).dict()
        )
    except HTTPException as e:
        return generate_response(
            status_code=e.status_code,
            response_message=e.detail,
            customer_message="Failed to complete onboarding",
            body=None
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=str(e),
            customer_message="An unexpected error occurred",
            body=None
        )

@router.post("/reset", response_model=Dict[str, Any])
async def reset_onboarding(
    request: Request,
    onboarding_service: OnboardingService = Depends(get_onboarding_service)
):
    """
    Reset onboarding progress
    
    This endpoint resets the onboarding progress for the currently authenticated user.
    """
    try:
        user = request.state.user
        progress = await onboarding_service.reset_onboarding(user.id)
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="Onboarding reset successfully",
            customer_message="Your onboarding progress has been reset",
            body=OnboardingProgressResponse.from_orm(progress).dict()
        )
    except HTTPException as e:
        return generate_response(
            status_code=e.status_code,
            response_message=e.detail,
            customer_message="Failed to reset onboarding",
            body=None
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=str(e),
            customer_message="An unexpected error occurred",
            body=None
        )

@router.get("/steps", response_model=Dict[str, Any])
async def get_onboarding_steps(
    request: Request,
    onboarding_service: OnboardingService = Depends(get_onboarding_service)
):
    """
    Get onboarding steps
    
    This endpoint returns all onboarding steps and their descriptions.
    """
    try:
        steps = await onboarding_service.get_onboarding_steps()
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="Onboarding steps retrieved successfully",
            customer_message="Onboarding steps have been retrieved",
            body=steps
        )
    except HTTPException as e:
        return generate_response(
            status_code=e.status_code,
            response_message=e.detail,
            customer_message="Failed to retrieve onboarding steps",
            body=None
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=str(e),
            customer_message="An unexpected error occurred",
            body=None
        )
