from typing import Optional, List, Dict, Any, Union
import uuid
from datetime import datetime, timedelta
from fastapi import HTTPException, status, Depends
from sqlalchemy import select, func, update, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
from src.database import get_db
from src.models.user_models import (
    User, SavedContent, ContentFolder, OfflineContent
)
from src.schemas.user_schemas import (
    ContentFolderCreate, ContentFolderUpdate, SavedContentCreate, 
    SavedContentUpdate, OfflineContentCreate, OfflineContentUpdate
)
from src.utils.logging.activity_logger import ActivityLogger


class ContentService:
    """
    Service for handling content-related operations including saved content,
    folders, and offline content management
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.activity_logger = ActivityLogger()
    
    # Content Folder Methods
    
    async def get_user_folders(self, user_id: uuid.UUID) -> List[ContentFolder]:
        """
        Get all folders for a user
        
        Args:
            user_id: User ID
            
        Returns:
            List of content folders
        """
        query = (
            select(ContentFolder)
            .where(ContentFolder.user_id == user_id)
            .order_by(ContentFolder.sort_order)
        )
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_folder_by_id(self, folder_id: uuid.UUID, user_id: uuid.UUID) -> Optional[ContentFolder]:
        """
        Get a folder by ID
        
        Args:
            folder_id: Folder ID
            user_id: User ID for verification
            
        Returns:
            Content folder if found, None otherwise
        """
        query = (
            select(ContentFolder)
            .where(
                ContentFolder.id == folder_id,
                ContentFolder.user_id == user_id
            )
        )
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def create_folder(self, user_id: uuid.UUID, folder_data: ContentFolderCreate) -> ContentFolder:
        """
        Create a new content folder
        
        Args:
            user_id: User ID
            folder_data: Folder creation data
            
        Returns:
            Created content folder
            
        Raises:
            HTTPException: If parent folder not found
        """
        # Check if parent folder exists if provided
        if folder_data.parent_folder_id:
            parent_folder = await self.get_folder_by_id(folder_data.parent_folder_id, user_id)
            if not parent_folder:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Parent folder not found"
                )
        
        # Create folder
        folder = ContentFolder(
            user_id=user_id,
            **folder_data.dict()
        )
        
        self.db.add(folder)
        await self.db.commit()
        await self.db.refresh(folder)
        
        # Log activity
        await self.activity_logger.log_activity(
            f"User created content folder '{folder.name}'",
            user_id=str(user_id),
            activity_type="folder_created",
            metadata={
                "folder_id": str(folder.id),
                "folder_name": folder.name,
                "parent_folder_id": str(folder_data.parent_folder_id) if folder_data.parent_folder_id else None
            }
        )
        
        return folder
    
    async def update_folder(
        self, folder_id: uuid.UUID, user_id: uuid.UUID, folder_data: ContentFolderUpdate
    ) -> ContentFolder:
        """
        Update a content folder
        
        Args:
            folder_id: Folder ID
            user_id: User ID for verification
            folder_data: Folder update data
            
        Returns:
            Updated content folder
            
        Raises:
            HTTPException: If folder not found or parent folder not found
        """
        # Get folder
        folder = await self.get_folder_by_id(folder_id, user_id)
        if not folder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Folder not found"
            )
        
        # Check if parent folder exists if provided
        if folder_data.parent_folder_id:
            # Prevent circular reference
            if folder_data.parent_folder_id == folder_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Folder cannot be its own parent"
                )
            
            parent_folder = await self.get_folder_by_id(folder_data.parent_folder_id, user_id)
            if not parent_folder:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Parent folder not found"
                )
        
        # Update fields if provided
        update_data = folder_data.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(folder, key, value)
        
        await self.db.commit()
        await self.db.refresh(folder)
        
        # Log activity
        await self.activity_logger.log_activity(
            f"User updated content folder '{folder.name}'",
            user_id=str(user_id),
            activity_type="folder_updated",
            metadata={
                "folder_id": str(folder.id),
                "updated_fields": list(update_data.keys())
            }
        )
        
        return folder
    
    async def delete_folder(self, folder_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """
        Delete a content folder
        
        Args:
            folder_id: Folder ID
            user_id: User ID for verification
            
        Returns:
            True if successful
            
        Raises:
            HTTPException: If folder not found
        """
        # Get folder
        folder = await self.get_folder_by_id(folder_id, user_id)
        if not folder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Folder not found"
            )
        
        folder_name = folder.name
        
        # Update any content in this folder to no folder
        query = (
            update(SavedContent)
            .where(
                SavedContent.folder_id == folder_id,
                SavedContent.user_id == user_id
            )
            .values(folder_id=None)
        )
        await self.db.execute(query)
        
        # Update any child folders to have no parent
        query = (
            update(ContentFolder)
            .where(
                ContentFolder.parent_folder_id == folder_id,
                ContentFolder.user_id == user_id
            )
            .values(parent_folder_id=None)
        )
        await self.db.execute(query)
        
        # Delete folder
        await self.db.delete(folder)
        await self.db.commit()
        
        # Log activity
        await self.activity_logger.log_activity(
            f"User deleted content folder '{folder_name}'",
            user_id=str(user_id),
            activity_type="folder_deleted",
            metadata={
                "folder_id": str(folder_id),
                "folder_name": folder_name
            }
        )
        
        return True
    
    # Saved Content Methods
    
    async def get_user_saved_content(
        self, user_id: uuid.UUID, folder_id: Optional[uuid.UUID] = None
    ) -> List[SavedContent]:
        """
        Get all saved content for a user, optionally filtered by folder
        
        Args:
            user_id: User ID
            folder_id: Optional folder ID to filter by
            
        Returns:
            List of saved content
        """
        query = (
            select(SavedContent)
            .options(selectinload(SavedContent.folder))
            .where(SavedContent.user_id == user_id)
        )
        
        if folder_id:
            query = query.where(SavedContent.folder_id == folder_id)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_saved_content_by_id(
        self, content_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[SavedContent]:
        """
        Get saved content by ID
        
        Args:
            content_id: Saved content ID
            user_id: User ID for verification
            
        Returns:
            Saved content if found, None otherwise
        """
        query = (
            select(SavedContent)
            .options(selectinload(SavedContent.folder))
            .where(
                SavedContent.id == content_id,
                SavedContent.user_id == user_id
            )
        )
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def get_saved_content_by_content_id(
        self, content_id: uuid.UUID, content_type: str, user_id: uuid.UUID
    ) -> Optional[SavedContent]:
        """
        Get saved content by content ID and type
        
        Args:
            content_id: Content ID
            content_type: Content type
            user_id: User ID for verification
            
        Returns:
            Saved content if found, None otherwise
        """
        query = (
            select(SavedContent)
            .options(selectinload(SavedContent.folder))
            .where(
                SavedContent.content_id == content_id,
                SavedContent.content_type == content_type,
                SavedContent.user_id == user_id
            )
        )
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def save_content(
        self, user_id: uuid.UUID, content_data: SavedContentCreate
    ) -> SavedContent:
        """
        Save content for a user
        
        Args:
            user_id: User ID
            content_data: Content data
            
        Returns:
            Created saved content
            
        Raises:
            HTTPException: If content already saved or folder not found
        """
        # Check if content already saved
        existing_content = await self.get_saved_content_by_content_id(
            content_data.content_id, content_data.content_type, user_id
        )
        
        if existing_content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Content already saved"
            )
        
        # Check if folder exists if provided
        if content_data.folder_id:
            folder = await self.get_folder_by_id(content_data.folder_id, user_id)
            if not folder:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Folder not found"
                )
        
        # Save content
        saved_content = SavedContent(
            user_id=user_id,
            **content_data.dict()
        )
        
        self.db.add(saved_content)
        await self.db.commit()
        await self.db.refresh(saved_content)
        
        # Log activity
        await self.activity_logger.log_activity(
            f"User saved content of type '{content_data.content_type}'",
            user_id=str(user_id),
            activity_type="content_saved",
            metadata={
                "saved_content_id": str(saved_content.id),
                "content_id": str(content_data.content_id),
                "content_type": content_data.content_type,
                "folder_id": str(content_data.folder_id) if content_data.folder_id else None,
                "is_favorite": content_data.is_favorite
            }
        )
        
        return saved_content
    
    async def update_saved_content(
        self, content_id: uuid.UUID, user_id: uuid.UUID, content_data: SavedContentUpdate
    ) -> SavedContent:
        """
        Update saved content
        
        Args:
            content_id: Saved content ID
            user_id: User ID for verification
            content_data: Content update data
            
        Returns:
            Updated saved content
            
        Raises:
            HTTPException: If content not found or folder not found
        """
        # Get saved content
        saved_content = await self.get_saved_content_by_id(content_id, user_id)
        if not saved_content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Saved content not found"
            )
        
        # Check if folder exists if provided
        if content_data.folder_id:
            folder = await self.get_folder_by_id(content_data.folder_id, user_id)
            if not folder:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Folder not found"
                )
        
        # Update fields if provided
        update_data = content_data.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(saved_content, key, value)
        
        await self.db.commit()
        await self.db.refresh(saved_content)
        
        # Log activity
        await self.activity_logger.log_activity(
            f"User updated saved content",
            user_id=str(user_id),
            activity_type="saved_content_updated",
            metadata={
                "saved_content_id": str(content_id),
                "updated_fields": list(update_data.keys())
            }
        )
        
        return saved_content
    
    async def delete_saved_content(self, content_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """
        Delete saved content
        
        Args:
            content_id: Saved content ID
            user_id: User ID for verification
            
        Returns:
            True if successful
            
        Raises:
            HTTPException: If content not found
        """
        # Get saved content
        saved_content = await self.get_saved_content_by_id(content_id, user_id)
        if not saved_content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Saved content not found"
            )
        
        content_type = saved_content.content_type
        
        # Delete saved content
        await self.db.delete(saved_content)
        await self.db.commit()
        
        # Log activity
        await self.activity_logger.log_activity(
            f"User removed saved content of type '{content_type}'",
            user_id=str(user_id),
            activity_type="saved_content_deleted",
            metadata={
                "saved_content_id": str(content_id),
                "content_type": content_type
            }
        )
        
        return True
    
    # Offline Content Methods
    
    async def get_user_offline_content(self, user_id: uuid.UUID) -> List[OfflineContent]:
        """
        Get all offline content for a user
        
        Args:
            user_id: User ID
            
        Returns:
            List of offline content
        """
        query = (
            select(OfflineContent)
            .where(OfflineContent.user_id == user_id)
        )
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_offline_content_by_id(
        self, content_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[OfflineContent]:
        """
        Get offline content by ID
        
        Args:
            content_id: Offline content ID
            user_id: User ID for verification
            
        Returns:
            Offline content if found, None otherwise
        """
        query = (
            select(OfflineContent)
            .where(
                OfflineContent.id == content_id,
                OfflineContent.user_id == user_id
            )
        )
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def get_offline_content_by_content_id(
        self, content_id: uuid.UUID, content_type: str, user_id: uuid.UUID
    ) -> Optional[OfflineContent]:
        """
        Get offline content by content ID and type
        
        Args:
            content_id: Content ID
            content_type: Content type
            user_id: User ID for verification
            
        Returns:
            Offline content if found, None otherwise
        """
        query = (
            select(OfflineContent)
            .where(
                OfflineContent.content_id == content_id,
                OfflineContent.content_type == content_type,
                OfflineContent.user_id == user_id
            )
        )
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def add_offline_content(
        self, user_id: uuid.UUID, content_data: OfflineContentCreate
    ) -> OfflineContent:
        """
        Add content for offline access
        
        Args:
            user_id: User ID
            content_data: Content data
            
        Returns:
            Created offline content
            
        Raises:
            HTTPException: If content already added for offline access or storage limit exceeded
        """
        # Check if content already added for offline access
        existing_content = await self.get_offline_content_by_content_id(
            content_data.content_id, content_data.content_type, user_id
        )
        
        if existing_content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Content already added for offline access"
            )
        
        # Check storage limit
        if content_data.file_size_bytes:
            total_size = await self._get_total_offline_content_size(user_id)
            
            # Get user preferences for limit
            query = (
                select(User)
                .options(selectinload(User.preferences))
                .where(User.id == user_id)
            )
            result = await self.db.execute(query)
            user = result.scalars().first()
            
            if user and user.preferences:
                limit_mb = user.preferences.offline_content_limit_mb
                limit_bytes = limit_mb * 1024 * 1024
                
                if total_size + content_data.file_size_bytes > limit_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Offline storage limit of {limit_mb}MB exceeded"
                    )
        
        # Add offline content
        offline_content = OfflineContent(
            user_id=user_id,
            **content_data.dict()
        )
        
        self.db.add(offline_content)
        await self.db.commit()
        await self.db.refresh(offline_content)
        
        # Log activity
        await self.activity_logger.log_activity(
            f"User added content of type '{content_data.content_type}' for offline access",
            user_id=str(user_id),
            activity_type="offline_content_added",
            metadata={
                "offline_content_id": str(offline_content.id),
                "content_id": str(content_data.content_id),
                "content_type": content_data.content_type,
                "file_size_bytes": content_data.file_size_bytes,
                "download_status": content_data.download_status
            }
        )
        
        return offline_content
    
    async def update_offline_content(
        self, content_id: uuid.UUID, user_id: uuid.UUID, content_data: OfflineContentUpdate
    ) -> OfflineContent:
        """
        Update offline content
        
        Args:
            content_id: Offline content ID
            user_id: User ID for verification
            content_data: Content update data
            
        Returns:
            Updated offline content
            
        Raises:
            HTTPException: If content not found
        """
        # Get offline content
        offline_content = await self.get_offline_content_by_id(content_id, user_id)
        if not offline_content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Offline content not found"
            )
        
        # Update fields if provided
        update_data = content_data.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(offline_content, key, value)
        
        await self.db.commit()
        await self.db.refresh(offline_content)
        
        # Log activity
        await self.activity_logger.log_activity(
            f"User updated offline content status to '{offline_content.download_status}'",
            user_id=str(user_id),
            activity_type="offline_content_updated",
            metadata={
                "offline_content_id": str(content_id),
                "updated_fields": list(update_data.keys()),
                "download_status": offline_content.download_status
            }
        )
        
        return offline_content
    
    async def delete_offline_content(self, content_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """
        Delete offline content
        
        Args:
            content_id: Offline content ID
            user_id: User ID for verification
            
        Returns:
            True if successful
            
        Raises:
            HTTPException: If content not found
        """
        # Get offline content
        offline_content = await self.get_offline_content_by_id(content_id, user_id)
        if not offline_content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Offline content not found"
            )
        
        content_type = offline_content.content_type
        
        # Delete offline content
        await self.db.delete(offline_content)
        await self.db.commit()
        
        # Log activity
        await self.activity_logger.log_activity(
            f"User removed content of type '{content_type}' from offline access",
            user_id=str(user_id),
            activity_type="offline_content_deleted",
            metadata={
                "offline_content_id": str(content_id),
                "content_type": content_type
            }
        )
        
        return True
    
    async def _get_total_offline_content_size(self, user_id: uuid.UUID) -> int:
        """
        Get total size of all offline content for a user
        
        Args:
            user_id: User ID
            
        Returns:
            Total size in bytes
        """
        query = (
            select(func.sum(OfflineContent.file_size_bytes))
            .where(
                OfflineContent.user_id == user_id,
                OfflineContent.file_size_bytes.isnot(None)
            )
        )
        result = await self.db.execute(query)
        total_size = result.scalar() or 0
        return total_size


# Dependency to get ContentService
async def get_content_service(db: AsyncSession = Depends(get_db)) -> ContentService:
    """
    Dependency to get ContentService instance
    
    Args:
        db: Database session
        
    Returns:
        ContentService instance
    """
    return ContentService(db)
