"""
Bookmark manager for constitution content.
Handles user bookmark creation, retrieval, and management.
"""

import uuid
from typing import Dict, List, Optional
from datetime import datetime
from fastapi import BackgroundTasks
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..base import BaseService, ConstitutionCacheManager
from ....utils.cache import HOUR
from ....models.user_models import Bookmark


class BookmarkManager(BaseService):
    """
    Service for managing user bookmarks.
    Handles bookmark creation, retrieval, updating, and deletion.
    """
    
    def __init__(self, cache_manager: ConstitutionCacheManager, 
                 db_session: Optional[AsyncSession] = None):
        """
        Initialize the bookmark manager.
        
        Args:
            cache_manager: Cache manager instance
            db_session: Database session
        """
        super().__init__(cache_manager, db_session)
    
    def get_service_name(self) -> str:
        """Get the service name."""
        return "bookmark_manager"
    
    async def get_user_bookmarks(self, user_id: str, 
                                background_tasks: Optional[BackgroundTasks] = None) -> List[Dict]:
        """
        Get all bookmarks for a user.
        
        Args:
            user_id: User ID
            background_tasks: Optional background tasks
            
        Returns:
            List[Dict]: User bookmarks
        """
        try:
            # Validate user ID
            user_id = self.validator.validate_user_id(user_id)
            
            # Check cache first
            cached_bookmarks = await self.cache.get_user_bookmarks(user_id)
            if cached_bookmarks:
                return cached_bookmarks
            
            # Get from database
            bookmarks = await self._get_bookmarks_from_database(user_id)
            
            # Cache the results
            await self.cache.set_user_bookmarks(user_id, bookmarks, HOUR)
            
            return bookmarks
            
        except Exception as e:
            self._handle_service_error(e, f"Error getting bookmarks for user {user_id}")
    
    async def _get_bookmarks_from_database(self, user_id: str) -> List[Dict]:
        """
        Get bookmarks from database.
        
        Args:
            user_id: User ID
            
        Returns:
            List[Dict]: Bookmarks from database
        """
        try:
            if not self.db_session:
                self.logger.warning("Database session not available for bookmarks")
                return []
            
            user_uuid = uuid.UUID(user_id)
            
            stmt = select(Bookmark).where(
                Bookmark.user_id == user_uuid
            ).order_by(Bookmark.created_at.desc())
            
            result = await self.db_session.execute(stmt)
            db_bookmarks = result.scalars().all()
            
            # Convert to dict format
            bookmarks = []
            for bookmark in db_bookmarks:
                bookmarks.append({
                    "id": str(bookmark.id),
                    "bookmark_id": str(bookmark.id),  # For backward compatibility
                    "type": bookmark.bookmark_type,
                    "reference": bookmark.reference,
                    "title": bookmark.title,
                    "created_at": bookmark.created_at.isoformat(),
                    "updated_at": bookmark.updated_at.isoformat()
                })
            
            self.logger.info(f"Retrieved {len(bookmarks)} bookmarks for user {user_id}")
            return bookmarks
            
        except Exception as e:
            self.logger.error(f"Error getting bookmarks from database: {str(e)}")
            return []
    
    async def add_bookmark(self, user_id: str, bookmark_type: str, reference: str, 
                          title: str, background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """
        Add a new bookmark for a user.
        
        Args:
            user_id: User ID
            bookmark_type: Type of bookmark (chapter, article, etc.)
            reference: Reference string
            title: Bookmark title
            background_tasks: Optional background tasks
            
        Returns:
            Dict: Operation result
        """
        try:
            # Validate inputs
            user_id = self.validator.validate_user_id(user_id)
            bookmark_type = self.validator.validate_bookmark_type(bookmark_type)
            reference = self.validator.validate_bookmark_reference(reference, bookmark_type)
            title = self.validator.validate_bookmark_title(title)
            
            if not self.db_session:
                return {"success": False, "message": "Database session not available"}
            
            user_uuid = uuid.UUID(user_id)
            
            # Check if bookmark already exists
            existing_bookmark = await self._check_existing_bookmark(user_uuid, bookmark_type, reference)
            if existing_bookmark:
                return {"success": False, "message": "Bookmark already exists"}
            
            # Create new bookmark
            new_bookmark = Bookmark(
                user_id=user_uuid,
                bookmark_type=bookmark_type,
                reference=reference,
                title=title
            )
            
            self.db_session.add(new_bookmark)
            await self.db_session.commit()
            await self.db_session.refresh(new_bookmark)
            
            # Clear cache to ensure fresh data
            await self.cache.clear_user_bookmarks(user_id)
            
            # Create response
            bookmark_response = {
                "id": str(new_bookmark.id),
                "bookmark_id": str(new_bookmark.id),
                "type": new_bookmark.bookmark_type,
                "reference": new_bookmark.reference,
                "title": new_bookmark.title,
                "created_at": new_bookmark.created_at.isoformat(),
                "updated_at": new_bookmark.updated_at.isoformat()
            }
            
            self.logger.info(f"Added bookmark {new_bookmark.id} for user {user_id}")
            
            return {
                "success": True,
                "message": "Bookmark added successfully",
                "bookmark": bookmark_response
            }
            
        except Exception as e:
            if self.db_session:
                await self.db_session.rollback()
            self.logger.error(f"Error adding bookmark: {str(e)}")
            return {"success": False, "message": f"Error adding bookmark: {str(e)}"}
    
    async def _check_existing_bookmark(self, user_uuid: uuid.UUID, bookmark_type: str, 
                                     reference: str) -> Optional[Bookmark]:
        """
        Check if a bookmark already exists.
        
        Args:
            user_uuid: User UUID
            bookmark_type: Bookmark type
            reference: Reference string
            
        Returns:
            Optional[Bookmark]: Existing bookmark or None
        """
        try:
            stmt = select(Bookmark).where(
                and_(
                    Bookmark.user_id == user_uuid,
                    Bookmark.bookmark_type == bookmark_type,
                    Bookmark.reference == reference
                )
            )
            result = await self.db_session.execute(stmt)
            return result.scalar_one_or_none()
            
        except Exception as e:
            self.logger.error(f"Error checking existing bookmark: {str(e)}")
            return None
    
    async def remove_bookmark(self, user_id: str, bookmark_id: str,
                            background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """
        Remove a bookmark.
        
        Args:
            user_id: User ID
            bookmark_id: Bookmark ID to remove
            background_tasks: Optional background tasks
            
        Returns:
            Dict: Operation result
        """
        try:
            # Validate inputs
            user_id = self.validator.validate_user_id(user_id)
            
            if not self.db_session:
                return {"success": False, "message": "Database session not available"}
            
            user_uuid = uuid.UUID(user_id)
            bookmark_uuid = uuid.UUID(bookmark_id)
            
            # Find the bookmark
            stmt = select(Bookmark).where(
                and_(
                    Bookmark.user_id == user_uuid,
                    Bookmark.id == bookmark_uuid
                )
            )
            result = await self.db_session.execute(stmt)
            bookmark = result.scalar_one_or_none()
            
            if not bookmark:
                return {"success": False, "message": "Bookmark not found"}
            
            # Remove the bookmark
            await self.db_session.delete(bookmark)
            await self.db_session.commit()
            
            # Clear cache to ensure fresh data
            await self.cache.clear_user_bookmarks(user_id)
            
            self.logger.info(f"Removed bookmark {bookmark_id} for user {user_id}")
            
            return {"success": True, "message": "Bookmark removed successfully"}
            
        except Exception as e:
            if self.db_session:
                await self.db_session.rollback()
            self.logger.error(f"Error removing bookmark: {str(e)}")
            return {"success": False, "message": f"Error removing bookmark: {str(e)}"}
    
    async def update_bookmark(self, user_id: str, bookmark_id: str, 
                            title: Optional[str] = None,
                            background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """
        Update a bookmark.
        
        Args:
            user_id: User ID
            bookmark_id: Bookmark ID to update
            title: New title (optional)
            background_tasks: Optional background tasks
            
        Returns:
            Dict: Operation result
        """
        try:
            # Validate inputs
            user_id = self.validator.validate_user_id(user_id)
            
            if title:
                title = self.validator.validate_bookmark_title(title)
            
            if not self.db_session:
                return {"success": False, "message": "Database session not available"}
            
            user_uuid = uuid.UUID(user_id)
            bookmark_uuid = uuid.UUID(bookmark_id)
            
            # Find the bookmark
            stmt = select(Bookmark).where(
                and_(
                    Bookmark.user_id == user_uuid,
                    Bookmark.id == bookmark_uuid
                )
            )
            result = await self.db_session.execute(stmt)
            bookmark = result.scalar_one_or_none()
            
            if not bookmark:
                return {"success": False, "message": "Bookmark not found"}
            
            # Update the bookmark
            if title:
                bookmark.title = title
            bookmark.updated_at = datetime.now()
            
            await self.db_session.commit()
            
            # Clear cache to ensure fresh data
            await self.cache.clear_user_bookmarks(user_id)
            
            # Create response
            bookmark_response = {
                "id": str(bookmark.id),
                "bookmark_id": str(bookmark.id),
                "type": bookmark.bookmark_type,
                "reference": bookmark.reference,
                "title": bookmark.title,
                "created_at": bookmark.created_at.isoformat(),
                "updated_at": bookmark.updated_at.isoformat()
            }
            
            self.logger.info(f"Updated bookmark {bookmark_id} for user {user_id}")
            
            return {
                "success": True,
                "message": "Bookmark updated successfully",
                "bookmark": bookmark_response
            }
            
        except Exception as e:
            if self.db_session:
                await self.db_session.rollback()
            self.logger.error(f"Error updating bookmark: {str(e)}")
            return {"success": False, "message": f"Error updating bookmark: {str(e)}"}
    
    async def get_bookmark_by_id(self, user_id: str, bookmark_id: str) -> Optional[Dict]:
        """
        Get a specific bookmark by ID.
        
        Args:
            user_id: User ID
            bookmark_id: Bookmark ID
            
        Returns:
            Optional[Dict]: Bookmark data or None
        """
        try:
            # Validate inputs
            user_id = self.validator.validate_user_id(user_id)
            
            if not self.db_session:
                return None
            
            user_uuid = uuid.UUID(user_id)
            bookmark_uuid = uuid.UUID(bookmark_id)
            
            # Find the bookmark
            stmt = select(Bookmark).where(
                and_(
                    Bookmark.user_id == user_uuid,
                    Bookmark.id == bookmark_uuid
                )
            )
            result = await self.db_session.execute(stmt)
            bookmark = result.scalar_one_or_none()
            
            if not bookmark:
                return None
            
            return {
                "id": str(bookmark.id),
                "bookmark_id": str(bookmark.id),
                "type": bookmark.bookmark_type,
                "reference": bookmark.reference,
                "title": bookmark.title,
                "created_at": bookmark.created_at.isoformat(),
                "updated_at": bookmark.updated_at.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting bookmark by ID: {str(e)}")
            return None
    
    async def get_bookmarks_by_type(self, user_id: str, bookmark_type: str,
                                   background_tasks: Optional[BackgroundTasks] = None) -> List[Dict]:
        """
        Get bookmarks of a specific type for a user.
        
        Args:
            user_id: User ID
            bookmark_type: Type of bookmarks to retrieve
            background_tasks: Optional background tasks
            
        Returns:
            List[Dict]: Bookmarks of the specified type
        """
        try:
            # Validate inputs
            user_id = self.validator.validate_user_id(user_id)
            bookmark_type = self.validator.validate_bookmark_type(bookmark_type)
            
            cache_key = self._generate_cache_key("bookmarks_by_type", user_id, bookmark_type)
            
            # Check cache first
            cached_bookmarks = await self._cache_get(cache_key)
            if cached_bookmarks:
                return cached_bookmarks
            
            # Get all bookmarks and filter by type
            all_bookmarks = await self.get_user_bookmarks(user_id, background_tasks)
            filtered_bookmarks = [
                bookmark for bookmark in all_bookmarks 
                if bookmark["type"] == bookmark_type
            ]
            
            # Cache the filtered results
            await self._cache_set(cache_key, filtered_bookmarks, HOUR, background_tasks)
            
            return filtered_bookmarks
            
        except Exception as e:
            self.logger.error(f"Error getting bookmarks by type: {str(e)}")
            return []
    
    async def bookmark_exists(self, user_id: str, bookmark_type: str, reference: str) -> bool:
        """
        Check if a bookmark exists.
        
        Args:
            user_id: User ID
            bookmark_type: Bookmark type
            reference: Reference string
            
        Returns:
            bool: True if bookmark exists, False otherwise
        """
        try:
            # Validate inputs
            user_id = self.validator.validate_user_id(user_id)
            bookmark_type = self.validator.validate_bookmark_type(bookmark_type)
            reference = self.validator.validate_bookmark_reference(reference, bookmark_type)
            
            if not self.db_session:
                return False
            
            user_uuid = uuid.UUID(user_id)
            
            # Check if bookmark exists
            existing_bookmark = await self._check_existing_bookmark(user_uuid, bookmark_type, reference)
            return existing_bookmark is not None
            
        except Exception as e:
            self.logger.error(f"Error checking bookmark existence: {str(e)}")
            return False
    
    async def get_bookmark_statistics(self, user_id: str) -> Dict:
        """
        Get bookmark statistics for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Dict: Bookmark statistics
        """
        try:
            # Validate user ID
            user_id = self.validator.validate_user_id(user_id)
            
            # Get all bookmarks
            bookmarks = await self.get_user_bookmarks(user_id)
            
            # Calculate statistics
            total_bookmarks = len(bookmarks)
            
            # Count by type
            type_counts = {}
            for bookmark in bookmarks:
                bookmark_type = bookmark["type"]
                type_counts[bookmark_type] = type_counts.get(bookmark_type, 0) + 1
            
            # Most recent bookmark
            most_recent = None
            if bookmarks:
                most_recent = max(bookmarks, key=lambda x: x["created_at"])
            
            return {
                "total_bookmarks": total_bookmarks,
                "bookmarks_by_type": type_counts,
                "most_recent_bookmark": most_recent,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting bookmark statistics: {str(e)}")
            return {"error": str(e)}
    
    async def bulk_create_bookmarks(self, user_id: str, bookmarks: List[Dict],
                                   background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """
        Create multiple bookmarks in bulk.
        
        Args:
            user_id: User ID
            bookmarks: List of bookmark data
            background_tasks: Optional background tasks
            
        Returns:
            Dict: Bulk operation result
        """
        try:
            # Validate user ID
            user_id = self.validator.validate_user_id(user_id)
            
            if not self.db_session:
                return {"success": False, "message": "Database session not available"}
            
            successful_creates = 0
            failed_creates = 0
            created_bookmarks = []
            
            for bookmark_data in bookmarks:
                try:
                    result = await self.add_bookmark(
                        user_id,
                        bookmark_data.get("type"),
                        bookmark_data.get("reference"),
                        bookmark_data.get("title"),
                        background_tasks
                    )
                    
                    if result.get("success"):
                        successful_creates += 1
                        created_bookmarks.append(result.get("bookmark"))
                    else:
                        failed_creates += 1
                        
                except Exception as e:
                    self.logger.error(f"Failed to create bookmark: {str(e)}")
                    failed_creates += 1
            
            return {
                "success": True,
                "total_bookmarks": len(bookmarks),
                "successful_creates": successful_creates,
                "failed_creates": failed_creates,
                "created_bookmarks": created_bookmarks
            }
            
        except Exception as e:
            self.logger.error(f"Error in bulk bookmark creation: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def clear_all_bookmarks(self, user_id: str) -> Dict:
        """
        Clear all bookmarks for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Dict: Operation result
        """
        try:
            # Validate user ID
            user_id = self.validator.validate_user_id(user_id)
            
            if not self.db_session:
                return {"success": False, "message": "Database session not available"}
            
            user_uuid = uuid.UUID(user_id)
            
            # Get all bookmarks for the user
            stmt = select(Bookmark).where(Bookmark.user_id == user_uuid)
            result = await self.db_session.execute(stmt)
            bookmarks = result.scalars().all()
            
            # Delete all bookmarks
            deleted_count = len(bookmarks)
            for bookmark in bookmarks:
                await self.db_session.delete(bookmark)
            
            await self.db_session.commit()
            
            # Clear cache
            await self.cache.clear_user_bookmarks(user_id)
            
            self.logger.info(f"Cleared {deleted_count} bookmarks for user {user_id}")
            
            return {
                "success": True,
                "message": f"Cleared {deleted_count} bookmarks successfully",
                "deleted_count": deleted_count
            }
            
        except Exception as e:
            if self.db_session:
                await self.db_session.rollback()
            self.logger.error(f"Error clearing bookmarks: {str(e)}")
            return {"success": False, "message": f"Error clearing bookmarks: {str(e)}"}
    
    # Legacy method for backward compatibility
    async def create_bookmark(self, user_id: str, bookmark_type: str, reference: str, title: str) -> Dict:
        """
        Create a new bookmark (alias for add_bookmark).
        
        Args:
            user_id: User ID
            bookmark_type: Bookmark type
            reference: Reference string
            title: Bookmark title
            
        Returns:
            Dict: Operation result
        """
        return await self.add_bookmark(user_id, bookmark_type, reference, title)