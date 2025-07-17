from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
import uuid

from src.database import get_db
from src.services.reading_service import ReadingService, get_reading_service
from src.schemas.user_schemas import (
    ReadingHistoryCreate,
    ReadingHistoryResponse,
    ReadingProgressResponse,
    ReadingStreakResponse
)
from src.utils.custom_utils import generate_response

router = APIRouter(prefix="/reading", tags=["Reading"])

@router.get("/history", response_model=Dict[str, Any])
async def get_reading_history(
    request: Request,
    content_id: Optional[str] = None,
    reading_service: ReadingService = Depends(get_reading_service)
):
    """
    Get the current user's reading history
    
    This endpoint returns the reading history of the currently authenticated user.
    Optionally filter by content_id.
    """
    try:
        user = request.state.user
        history = await reading_service.get_reading_history(user.id, content_id)
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="Reading history retrieved successfully",
            customer_message="Your reading history has been retrieved",
            body=[ReadingHistoryResponse.model_validate(entry).model_dump() for entry in history]
        )
    except HTTPException as e:
        return generate_response(
            status_code=e.status_code,
            response_message=e.detail,
            customer_message="Failed to retrieve reading history",
            body=None
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=str(e),
            customer_message="An unexpected error occurred",
            body=None
        )

@router.post("/history", response_model=Dict[str, Any])
async def create_reading_history(
    history_data: ReadingHistoryCreate,
    request: Request,
    reading_service: ReadingService = Depends(get_reading_service)
):
    """
    Create a reading history entry
    
    This endpoint creates a reading history entry for the currently authenticated user.
    """
    try:
        user = request.state.user
        history = await reading_service.create_reading_history(user.id, history_data)
        
        return generate_response(
            status_code=status.HTTP_201_CREATED,
            response_message="Reading history created successfully",
            customer_message="Your reading has been recorded",
            body=ReadingHistoryResponse.from_orm(history).dict()
        )
    except HTTPException as e:
        return generate_response(
            status_code=e.status_code,
            response_message=e.detail,
            customer_message="Failed to record reading",
            body=None
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=str(e),
            customer_message="An unexpected error occurred",
            body=None
        )

@router.get("/progress", response_model=Dict[str, Any])
async def get_reading_progress(
    request: Request,
    content_id: str,
    reading_service: ReadingService = Depends(get_reading_service)
):
    """
    Get the current user's reading progress for a specific content
    
    This endpoint returns the reading progress of the currently authenticated user for a specific content.
    """
    try:
        user = request.state.user
        progress = await reading_service.get_reading_progress(user.id, content_id)
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="Reading progress retrieved successfully",
            customer_message="Your reading progress has been retrieved",
            body=ReadingProgressResponse(
                content_id=content_id,
                progress_percentage=progress.get("progress_percentage", 0),
                last_position=progress.get("last_position", 0),
                last_read_at=progress.get("last_read_at")
            ).dict()
        )
    except HTTPException as e:
        return generate_response(
            status_code=e.status_code,
            response_message=e.detail,
            customer_message="Failed to retrieve reading progress",
            body=None
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=str(e),
            customer_message="An unexpected error occurred",
            body=None
        )

@router.get("/streak", response_model=Dict[str, Any])
async def get_reading_streak(
    request: Request,
    reading_service: ReadingService = Depends(get_reading_service)
):
    """
    Get the current user's reading streak
    
    This endpoint returns the reading streak of the currently authenticated user.
    """
    try:
        user = request.state.user
        streak_info = await reading_service.get_reading_streak(user.id)
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="Reading streak retrieved successfully",
            customer_message="Your reading streak has been retrieved",
            body=ReadingStreakResponse(
                current_streak=streak_info.get("current_streak", 0),
                longest_streak=streak_info.get("longest_streak", 0),
                last_read_date=streak_info.get("last_read_date"),
                streak_maintained=streak_info.get("streak_maintained", False)
            ).dict()
        )
    except HTTPException as e:
        return generate_response(
            status_code=e.status_code,
            response_message=e.detail,
            customer_message="Failed to retrieve reading streak",
            body=None
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=str(e),
            customer_message="An unexpected error occurred",
            body=None
        )


@router.get("/analytics/{period}", response_model=Dict[str, Any])
async def get_reading_analytics(
    period: str,
    request: Request,
    reading_service: ReadingService = Depends(get_reading_service)
):
    """
    Get reading analytics for a specific period (week, month, year)
    
    This endpoint returns reading analytics for the specified time period.
    """
    try:
        if period not in ["week", "month", "year"]:
            return generate_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                response_message="Invalid period. Must be 'week', 'month', or 'year'",
                customer_message="Invalid time period specified",
                body=None
            )
        
        user = request.state.user
        analytics = await reading_service.get_reading_analytics(user.id, period)
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message=f"Reading analytics for {period} retrieved successfully",
            customer_message=f"Your {period} reading analytics have been retrieved",
            body=analytics
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=str(e),
            customer_message="Failed to retrieve reading analytics",
            body=None
        )
