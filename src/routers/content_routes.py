from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
import uuid

from src.database import get_db
from src.services.content_service import ContentService, get_content_service
from src.schemas.user_schemas import (
    ContentFolderCreate,
    ContentFolderResponse,
    SavedContentCreate,
    SavedContentResponse,
    OfflineContentCreate,
    OfflineContentResponse
)
from src.utils.custom_utils import generate_response

router = APIRouter(prefix="/content", tags=["Content"])

# Folder routes
@router.get("/folders", response_model=Dict[str, Any])
async def get_user_folders(
    request: Request,
    content_service: ContentService = Depends(get_content_service)
):
    """
    Get the current user's content folders
    
    This endpoint returns all content folders of the currently authenticated user.
    """
    try:
        user = request.state.user
        folders = await content_service.get_user_folders(user.id)
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="User folders retrieved successfully",
            customer_message="Your folders have been retrieved",
            body=[ContentFolderResponse.from_orm(folder).dict() for folder in folders]
        )
    except HTTPException as e:
        return generate_response(
            status_code=e.status_code,
            response_message=e.detail,
            customer_message="Failed to retrieve folders",
            body=None
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=str(e),
            customer_message="An unexpected error occurred",
            body=None
        )

@router.post("/folders", response_model=Dict[str, Any])
async def create_folder(
    folder_data: ContentFolderCreate,
    request: Request,
    content_service: ContentService = Depends(get_content_service)
):
    """
    Create a new content folder
    
    This endpoint creates a new content folder for the currently authenticated user.
    """
    try:
        user = request.state.user
        folder = await content_service.create_folder(user.id, folder_data)
        
        return generate_response(
            status_code=status.HTTP_201_CREATED,
            response_message="Folder created successfully",
            customer_message="Your folder has been created",
            body=ContentFolderResponse.from_orm(folder).dict()
        )
    except HTTPException as e:
        return generate_response(
            status_code=e.status_code,
            response_message=e.detail,
            customer_message="Failed to create folder",
            body=None
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=str(e),
            customer_message="An unexpected error occurred",
            body=None
        )

@router.get("/folders/{folder_id}", response_model=Dict[str, Any])
async def get_folder(
    folder_id: uuid.UUID,
    request: Request,
    content_service: ContentService = Depends(get_content_service)
):
    """
    Get a specific content folder
    
    This endpoint returns a specific content folder of the currently authenticated user.
    """
    try:
        user = request.state.user
        folder = await content_service.get_folder(folder_id, user.id)
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="Folder retrieved successfully",
            customer_message="Your folder has been retrieved",
            body=ContentFolderResponse.from_orm(folder).dict()
        )
    except HTTPException as e:
        return generate_response(
            status_code=e.status_code,
            response_message=e.detail,
            customer_message="Failed to retrieve folder",
            body=None
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=str(e),
            customer_message="An unexpected error occurred",
            body=None
        )

@router.put("/folders/{folder_id}", response_model=Dict[str, Any])
async def update_folder(
    folder_id: uuid.UUID,
    folder_data: ContentFolderCreate,
    request: Request,
    content_service: ContentService = Depends(get_content_service)
):
    """
    Update a content folder
    
    This endpoint updates a specific content folder of the currently authenticated user.
    """
    try:
        user = request.state.user
        folder = await content_service.update_folder(folder_id, user.id, folder_data)
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="Folder updated successfully",
            customer_message="Your folder has been updated",
            body=ContentFolderResponse.from_orm(folder).dict()
        )
    except HTTPException as e:
        return generate_response(
            status_code=e.status_code,
            response_message=e.detail,
            customer_message="Failed to update folder",
            body=None
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=str(e),
            customer_message="An unexpected error occurred",
            body=None
        )

@router.delete("/folders/{folder_id}", response_model=Dict[str, Any])
async def delete_folder(
    folder_id: uuid.UUID,
    request: Request,
    content_service: ContentService = Depends(get_content_service)
):
    """
    Delete a content folder
    
    This endpoint deletes a specific content folder of the currently authenticated user.
    """
    try:
        user = request.state.user
        await content_service.delete_folder(folder_id, user.id)
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="Folder deleted successfully",
            customer_message="Your folder has been deleted",
            body=None
        )
    except HTTPException as e:
        return generate_response(
            status_code=e.status_code,
            response_message=e.detail,
            customer_message="Failed to delete folder",
            body=None
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=str(e),
            customer_message="An unexpected error occurred",
            body=None
        )

# Saved content routes
@router.get("/saved", response_model=Dict[str, Any])
async def get_saved_content(
    request: Request,
    folder_id: Optional[uuid.UUID] = None,
    content_service: ContentService = Depends(get_content_service)
):
    """
    Get the current user's saved content
    
    This endpoint returns all saved content of the currently authenticated user.
    Optionally filter by folder_id.
    """
    try:
        user = request.state.user
        saved_content = await content_service.get_user_saved_content(user.id, folder_id)
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="Saved content retrieved successfully",
            customer_message="Your saved content has been retrieved",
            body=[SavedContentResponse.from_orm(content).dict() for content in saved_content]
        )
    except HTTPException as e:
        return generate_response(
            status_code=e.status_code,
            response_message=e.detail,
            customer_message="Failed to retrieve saved content",
            body=None
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=str(e),
            customer_message="An unexpected error occurred",
            body=None
        )

@router.post("/saved", response_model=Dict[str, Any])
async def save_content(
    content_data: SavedContentCreate,
    request: Request,
    content_service: ContentService = Depends(get_content_service)
):
    """
    Save content
    
    This endpoint saves content for the currently authenticated user.
    """
    try:
        user = request.state.user
        saved_content = await content_service.save_content(user.id, content_data)
        
        return generate_response(
            status_code=status.HTTP_201_CREATED,
            response_message="Content saved successfully",
            customer_message="Content has been saved",
            body=SavedContentResponse.from_orm(saved_content).dict()
        )
    except HTTPException as e:
        return generate_response(
            status_code=e.status_code,
            response_message=e.detail,
            customer_message="Failed to save content",
            body=None
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=str(e),
            customer_message="An unexpected error occurred",
            body=None
        )

@router.delete("/saved/{content_id}", response_model=Dict[str, Any])
async def unsave_content(
    content_id: uuid.UUID,
    request: Request,
    content_service: ContentService = Depends(get_content_service)
):
    """
    Unsave content
    
    This endpoint removes saved content for the currently authenticated user.
    """
    try:
        user = request.state.user
        await content_service.unsave_content(content_id, user.id)
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="Content unsaved successfully",
            customer_message="Content has been removed from your saved items",
            body=None
        )
    except HTTPException as e:
        return generate_response(
            status_code=e.status_code,
            response_message=e.detail,
            customer_message="Failed to unsave content",
            body=None
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=str(e),
            customer_message="An unexpected error occurred",
            body=None
        )

# Offline content routes
@router.get("/offline", response_model=Dict[str, Any])
async def get_offline_content(
    request: Request,
    content_service: ContentService = Depends(get_content_service)
):
    """
    Get the current user's offline content
    
    This endpoint returns all offline content of the currently authenticated user.
    """
    try:
        user = request.state.user
        offline_content = await content_service.get_offline_content(user.id)
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="Offline content retrieved successfully",
            customer_message="Your offline content has been retrieved",
            body=[OfflineContentResponse.from_orm(content).dict() for content in offline_content]
        )
    except HTTPException as e:
        return generate_response(
            status_code=e.status_code,
            response_message=e.detail,
            customer_message="Failed to retrieve offline content",
            body=None
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=str(e),
            customer_message="An unexpected error occurred",
            body=None
        )

@router.post("/offline", response_model=Dict[str, Any])
async def add_offline_content(
    content_data: OfflineContentCreate,
    request: Request,
    content_service: ContentService = Depends(get_content_service)
):
    """
    Add content for offline access
    
    This endpoint adds content for offline access for the currently authenticated user.
    """
    try:
        user = request.state.user
        offline_content = await content_service.add_offline_content(user.id, content_data)
        
        return generate_response(
            status_code=status.HTTP_201_CREATED,
            response_message="Content added for offline access successfully",
            customer_message="Content has been added for offline access",
            body=OfflineContentResponse.from_orm(offline_content).dict()
        )
    except HTTPException as e:
        return generate_response(
            status_code=e.status_code,
            response_message=e.detail,
            customer_message="Failed to add content for offline access",
            body=None
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=str(e),
            customer_message="An unexpected error occurred",
            body=None
        )

@router.delete("/offline/{content_id}", response_model=Dict[str, Any])
async def remove_offline_content(
    content_id: uuid.UUID,
    request: Request,
    content_service: ContentService = Depends(get_content_service)
):
    """
    Remove content from offline access
    
    This endpoint removes content from offline access for the currently authenticated user.
    """
    try:
        user = request.state.user
        await content_service.remove_offline_content(content_id, user.id)
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="Content removed from offline access successfully",
            customer_message="Content has been removed from your offline items",
            body=None
        )
    except HTTPException as e:
        return generate_response(
            status_code=e.status_code,
            response_message=e.detail,
            customer_message="Failed to remove content from offline access",
            body=None
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=str(e),
            customer_message="An unexpected error occurred",
            body=None
        )
