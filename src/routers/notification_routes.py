from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
import uuid

from src.database import get_db
from src.services.notification_service import NotificationService, get_notification_service
from src.schemas.user_schemas import (
    UserNotificationCreate,
    UserNotificationResponse,
    UserNotificationUpdate
)
from src.utils.custom_utils import generate_response

router = APIRouter(prefix="/notifications", tags=["Notifications"])

@router.get("", response_model=Dict[str, Any])
async def get_user_notifications(
    request: Request,
    unread_only: bool = False,
    notification_service: NotificationService = Depends(get_notification_service)
):
    """
    Get the current user's notifications
    
    This endpoint returns all notifications of the currently authenticated user.
    Optionally filter to only show unread notifications.
    """
    try:
        user = request.state.user
        notifications = await notification_service.get_user_notifications(user.id, unread_only)
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="User notifications retrieved successfully",
            customer_message="Your notifications have been retrieved",
            body=[UserNotificationResponse.from_orm(notification).dict() for notification in notifications]
        )
    except HTTPException as e:
        return generate_response(
            status_code=e.status_code,
            response_message=e.detail,
            customer_message="Failed to retrieve notifications",
            body=None
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=str(e),
            customer_message="An unexpected error occurred",
            body=None
        )

@router.get("/count", response_model=Dict[str, Any])
async def get_notification_count(
    request: Request,
    unread_only: bool = True,
    notification_service: NotificationService = Depends(get_notification_service)
):
    """
    Get the count of the current user's notifications
    
    This endpoint returns the count of notifications for the currently authenticated user.
    By default, only counts unread notifications.
    """
    try:
        user = request.state.user
        count = await notification_service.get_notification_count(user.id, unread_only)
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="Notification count retrieved successfully",
            customer_message="Your notification count has been retrieved",
            body={"count": count}
        )
    except HTTPException as e:
        return generate_response(
            status_code=e.status_code,
            response_message=e.detail,
            customer_message="Failed to retrieve notification count",
            body=None
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=str(e),
            customer_message="An unexpected error occurred",
            body=None
        )

@router.get("/{notification_id}", response_model=Dict[str, Any])
async def get_notification(
    notification_id: uuid.UUID,
    request: Request,
    notification_service: NotificationService = Depends(get_notification_service)
):
    """
    Get a specific notification
    
    This endpoint returns a specific notification of the currently authenticated user.
    """
    try:
        user = request.state.user
        notification = await notification_service.get_notification(notification_id, user.id)
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="Notification retrieved successfully",
            customer_message="Your notification has been retrieved",
            body=UserNotificationResponse.from_orm(notification).dict()
        )
    except HTTPException as e:
        return generate_response(
            status_code=e.status_code,
            response_message=e.detail,
            customer_message="Failed to retrieve notification",
            body=None
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=str(e),
            customer_message="An unexpected error occurred",
            body=None
        )

@router.post("", response_model=Dict[str, Any])
async def create_notification(
    notification_data: UserNotificationCreate,
    request: Request,
    notification_service: NotificationService = Depends(get_notification_service)
):
    """
    Create a notification for the current user
    
    This endpoint creates a notification for the currently authenticated user.
    """
    try:
        user = request.state.user
        notification = await notification_service.create_notification(user.id, notification_data)
        
        return generate_response(
            status_code=status.HTTP_201_CREATED,
            response_message="Notification created successfully",
            customer_message="Notification has been created",
            body=UserNotificationResponse.from_orm(notification).dict()
        )
    except HTTPException as e:
        return generate_response(
            status_code=e.status_code,
            response_message=e.detail,
            customer_message="Failed to create notification",
            body=None
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=str(e),
            customer_message="An unexpected error occurred",
            body=None
        )

@router.put("/{notification_id}/read", response_model=Dict[str, Any])
async def mark_notification_as_read(
    notification_id: uuid.UUID,
    request: Request,
    notification_service: NotificationService = Depends(get_notification_service)
):
    """
    Mark a notification as read
    
    This endpoint marks a specific notification as read for the currently authenticated user.
    """
    try:
        user = request.state.user
        notification = await notification_service.mark_as_read(notification_id, user.id)
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="Notification marked as read successfully",
            customer_message="Notification has been marked as read",
            body=UserNotificationResponse.from_orm(notification).dict()
        )
    except HTTPException as e:
        return generate_response(
            status_code=e.status_code,
            response_message=e.detail,
            customer_message="Failed to mark notification as read",
            body=None
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=str(e),
            customer_message="An unexpected error occurred",
            body=None
        )

@router.put("/read-all", response_model=Dict[str, Any])
async def mark_all_notifications_as_read(
    request: Request,
    notification_service: NotificationService = Depends(get_notification_service)
):
    """
    Mark all notifications as read
    
    This endpoint marks all notifications as read for the currently authenticated user.
    """
    try:
        user = request.state.user
        count = await notification_service.mark_all_as_read(user.id)
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="All notifications marked as read successfully",
            customer_message="All notifications have been marked as read",
            body={"updated_count": count}
        )
    except HTTPException as e:
        return generate_response(
            status_code=e.status_code,
            response_message=e.detail,
            customer_message="Failed to mark all notifications as read",
            body=None
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=str(e),
            customer_message="An unexpected error occurred",
            body=None
        )

@router.delete("/{notification_id}", response_model=Dict[str, Any])
async def delete_notification(
    notification_id: uuid.UUID,
    request: Request,
    notification_service: NotificationService = Depends(get_notification_service)
):
    """
    Delete a notification
    
    This endpoint deletes a specific notification of the currently authenticated user.
    """
    try:
        user = request.state.user
        await notification_service.delete_notification(notification_id, user.id)
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="Notification deleted successfully",
            customer_message="Notification has been deleted",
            body=None
        )
    except HTTPException as e:
        return generate_response(
            status_code=e.status_code,
            response_message=e.detail,
            customer_message="Failed to delete notification",
            body=None
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=str(e),
            customer_message="An unexpected error occurred",
            body=None
        )

@router.delete("", response_model=Dict[str, Any])
async def delete_all_notifications(
    request: Request,
    notification_service: NotificationService = Depends(get_notification_service)
):
    """
    Delete all notifications
    
    This endpoint deletes all notifications of the currently authenticated user.
    """
    try:
        user = request.state.user
        count = await notification_service.delete_all_notifications(user.id)
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="All notifications deleted successfully",
            customer_message="All notifications have been deleted",
            body={"deleted_count": count}
        )
    except HTTPException as e:
        return generate_response(
            status_code=e.status_code,
            response_message=e.detail,
            customer_message="Failed to delete all notifications",
            body=None
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=str(e),
            customer_message="An unexpected error occurred",
            body=None
        )
