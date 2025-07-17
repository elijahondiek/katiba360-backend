from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
import uuid

from src.database import get_db
from src.services.sharing_service import SharingService, get_sharing_service
from src.schemas.user_schemas import (
    SharingEventCreate,
    SharingEventResponse
)
from src.utils.custom_utils import generate_response

router = APIRouter(prefix="/sharing", tags=["Sharing"])


@router.post("/events", response_model=Dict[str, Any])
async def create_sharing_event(
    sharing_data: SharingEventCreate,
    request: Request,
    sharing_service: SharingService = Depends(get_sharing_service)
):
    """
    Create a new sharing event
    
    This endpoint logs a sharing event when a user shares content via any method
    (Facebook, Twitter, WhatsApp, native sharing, or copy link).
    """
    try:
        user = request.state.user
        sharing_event = await sharing_service.create_sharing_event(user.id, sharing_data)
        
        return generate_response(
            status_code=status.HTTP_201_CREATED,
            response_message="Sharing event created successfully",
            customer_message="Your sharing activity has been recorded",
            body=SharingEventResponse.model_validate(sharing_event).model_dump()
        )
    except HTTPException as e:
        return generate_response(
            status_code=e.status_code,
            response_message=e.detail,
            customer_message="Failed to record sharing event",
            body=None
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=str(e),
            customer_message="An unexpected error occurred",
            body=None
        )


@router.get("/events", response_model=Dict[str, Any])
async def get_sharing_events(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    sharing_service: SharingService = Depends(get_sharing_service)
):
    """
    Get sharing events for the current user
    
    This endpoint returns the sharing history of the currently authenticated user.
    """
    try:
        user = request.state.user
        events = await sharing_service.get_user_sharing_events(user.id, limit, offset)
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="Sharing events retrieved successfully",
            customer_message="Your sharing history has been retrieved",
            body=[SharingEventResponse.model_validate(event).model_dump() for event in events]
        )
    except HTTPException as e:
        return generate_response(
            status_code=e.status_code,
            response_message=e.detail,
            customer_message="Failed to retrieve sharing events",
            body=None
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=str(e),
            customer_message="An unexpected error occurred",
            body=None
        )


@router.get("/analytics", response_model=Dict[str, Any])
async def get_sharing_analytics(
    request: Request,
    days: int = 30,
    sharing_service: SharingService = Depends(get_sharing_service)
):
    """
    Get sharing analytics for the current user
    
    This endpoint returns sharing analytics for the specified time period.
    """
    try:
        if days < 1 or days > 365:
            return generate_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                response_message="Days must be between 1 and 365",
                customer_message="Invalid time period specified",
                body=None
            )
        
        user = request.state.user
        analytics = await sharing_service.get_sharing_analytics(user.id, days)
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message=f"Sharing analytics for {days} days retrieved successfully",
            customer_message=f"Your sharing analytics have been retrieved",
            body=analytics
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=str(e),
            customer_message="Failed to retrieve sharing analytics",
            body=None
        )


@router.get("/achievement/sharing-citizen", response_model=Dict[str, Any])
async def check_sharing_citizen_achievement(
    request: Request,
    sharing_service: SharingService = Depends(get_sharing_service)
):
    """
    Check if user qualifies for Sharing Citizen achievement
    
    This endpoint checks if the current user has shared enough content to earn
    the "Sharing Citizen" achievement.
    """
    try:
        user = request.state.user
        qualifies = await sharing_service.check_sharing_citizen_achievement(user.id)
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="Sharing Citizen achievement status retrieved successfully",
            customer_message="Your achievement status has been checked",
            body={
                "qualifies": qualifies,
                "achievement_name": "Sharing Citizen",
                "description": "Awarded for sharing constitutional content to help spread civic knowledge"
            }
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=str(e),
            customer_message="Failed to check achievement status",
            body=None
        )