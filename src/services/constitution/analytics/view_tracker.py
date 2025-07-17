"""
View tracking service for constitution content.
Handles view counting, database storage, and cache management.
"""

import uuid
from typing import Optional, Dict, List
from datetime import datetime
from fastapi import BackgroundTasks
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..base import BaseService, ConstitutionCacheManager
from ....models.user_models import ContentView


class ViewTracker(BaseService):
    """
    Service for tracking content views and analytics.
    Handles both cache-based and database-based view tracking.
    """
    
    def __init__(self, cache_manager: ConstitutionCacheManager, 
                 db_session: Optional[AsyncSession] = None):
        """
        Initialize the view tracker.
        
        Args:
            cache_manager: Cache manager instance
            db_session: Database session for persistent storage
        """
        super().__init__(cache_manager, db_session)
    
    def get_service_name(self) -> str:
        """Get the service name."""
        return "view_tracker"
    
    async def track_view(self, item_type: str, item_id: str, 
                        user_id: Optional[str] = None,
                        device_type: Optional[str] = None,
                        ip_address: Optional[str] = None,
                        background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """
        Track a view for analytics purposes.
        
        Args:
            item_type: Type of content (chapter, article, search, etc.)
            item_id: ID of the content
            user_id: Optional user ID
            device_type: Optional device type
            ip_address: Optional IP address
            background_tasks: Optional background tasks
            
        Returns:
            Dict: View tracking result
        """
        try:
            # Validate item type
            item_type = self.validator.validate_content_type(item_type)
            
            # Validate user ID if provided
            if user_id:
                user_id = self.validator.validate_user_id(user_id)
            
            # Track in cache for immediate performance
            cache_result = await self._track_view_in_cache(item_type, item_id, background_tasks)
            
            # Track in database for persistence
            if self.db_session:
                if background_tasks:
                    background_tasks.add_task(
                        self._store_view_in_database,
                        item_type, item_id, user_id, device_type, ip_address
                    )
                else:
                    await self._store_view_in_database(
                        item_type, item_id, user_id, device_type, ip_address
                    )
            
            self.logger.info(f"Tracked view for {item_type}:{item_id}")
            
            return {
                "success": True,
                "item_type": item_type,
                "item_id": item_id,
                "view_count": cache_result.get("view_count", 1),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error tracking view: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _track_view_in_cache(self, item_type: str, item_id: str,
                                  background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """
        Track view in cache for immediate performance.
        
        Args:
            item_type: Type of content
            item_id: ID of the content
            background_tasks: Optional background tasks
            
        Returns:
            Dict: Cache tracking result
        """
        try:
            # Increment view count
            view_count = await self.cache.increment_view_count(item_type, item_id)
            
            # Track in popular content
            await self._track_popular_content(item_type, item_id, background_tasks)
            
            return {
                "success": True,
                "view_count": view_count
            }
            
        except Exception as e:
            self.logger.error(f"Error tracking view in cache: {str(e)}")
            return {
                "success": False,
                "view_count": 0
            }
    
    async def _track_popular_content(self, item_type: str, item_id: str,
                                   background_tasks: Optional[BackgroundTasks] = None):
        """
        Track content in popular content metrics.
        
        Args:
            item_type: Type of content
            item_id: ID of the content
            background_tasks: Optional background tasks
        """
        try:
            popular_key = f"constitution:popular:daily:{item_type}:{item_id}"
            
            if background_tasks:
                background_tasks.add_task(self.cache.increment, popular_key)
            else:
                await self.cache.increment(popular_key)
                
        except Exception as e:
            self.logger.error(f"Error tracking popular content: {str(e)}")
    
    async def _store_view_in_database(self, item_type: str, item_id: str,
                                    user_id: Optional[str] = None,
                                    device_type: Optional[str] = None,
                                    ip_address: Optional[str] = None):
        """
        Store view data in database for persistent analytics.
        
        Args:
            item_type: Type of content
            item_id: ID of the content
            user_id: Optional user ID
            device_type: Optional device type
            ip_address: Optional IP address
        """
        if not self.db_session:
            self.logger.warning("Database session not available for view tracking")
            return
        
        try:
            # Convert user_id to UUID if provided
            user_uuid = None
            if user_id:
                try:
                    user_uuid = uuid.UUID(user_id)
                except ValueError:
                    self.logger.warning(f"Invalid user_id format: {user_id}")
                    user_uuid = None
            
            # Check if view record already exists
            existing_view = None
            if user_uuid:
                stmt = select(ContentView).where(
                    and_(
                        ContentView.user_id == user_uuid,
                        ContentView.content_type == item_type,
                        ContentView.content_reference == item_id
                    )
                )
                result = await self.db_session.execute(stmt)
                existing_view = result.scalar_one_or_none()
            
            now = datetime.now()
            
            if existing_view:
                # Update existing view record
                existing_view.view_count += 1
                existing_view.last_viewed_at = now
                if device_type:
                    existing_view.device_type = device_type
                if ip_address:
                    existing_view.ip_address = ip_address
                
                self.logger.info(f"Updated existing view record for {item_type}:{item_id}")
            else:
                # Create new view record
                new_view = ContentView(
                    content_type=item_type,
                    content_reference=item_id,
                    user_id=user_uuid,
                    view_count=1,
                    first_viewed_at=now,
                    last_viewed_at=now,
                    device_type=device_type,
                    ip_address=ip_address
                )
                self.db_session.add(new_view)
                self.logger.info(f"Created new view record for {item_type}:{item_id}")
            
            # Commit the transaction
            await self.db_session.commit()
            
        except Exception as e:
            self.logger.error(f"Error storing view in database: {str(e)}")
            await self.db_session.rollback()
    
    async def get_view_count(self, item_type: str, item_id: str) -> int:
        """
        Get view count for a specific item.
        
        Args:
            item_type: Type of content
            item_id: ID of the content
            
        Returns:
            int: View count
        """
        try:
            # Try cache first
            cache_count = await self.cache.get_view_count(item_type, item_id)
            if cache_count > 0:
                return cache_count
            
            # Fallback to database
            if self.db_session:
                stmt = select(ContentView).where(
                    and_(
                        ContentView.content_type == item_type,
                        ContentView.content_reference == item_id
                    )
                )
                result = await self.db_session.execute(stmt)
                views = result.scalars().all()
                
                total_views = sum(view.view_count for view in views)
                return total_views
            
            return 0
            
        except Exception as e:
            self.logger.error(f"Error getting view count: {str(e)}")
            return 0
    
    async def get_user_view_history(self, user_id: str, limit: int = 50) -> List[Dict]:
        """
        Get view history for a specific user.
        
        Args:
            user_id: User ID
            limit: Maximum number of records
            
        Returns:
            List[Dict]: User view history
        """
        try:
            if not self.db_session:
                self.logger.warning("Database session not available for view history")
                return []
            
            user_uuid = uuid.UUID(user_id)
            
            stmt = select(ContentView).where(
                ContentView.user_id == user_uuid
            ).order_by(
                ContentView.last_viewed_at.desc()
            ).limit(limit)
            
            result = await self.db_session.execute(stmt)
            views = result.scalars().all()
            
            history = []
            for view in views:
                history.append({
                    "content_type": view.content_type,
                    "content_reference": view.content_reference,
                    "view_count": view.view_count,
                    "first_viewed_at": view.first_viewed_at.isoformat(),
                    "last_viewed_at": view.last_viewed_at.isoformat(),
                    "device_type": view.device_type
                })
            
            return history
            
        except Exception as e:
            self.logger.error(f"Error getting user view history: {str(e)}")
            return []
    
    async def get_content_analytics(self, item_type: str, item_id: str) -> Dict:
        """
        Get detailed analytics for a specific content item.
        
        Args:
            item_type: Type of content
            item_id: ID of the content
            
        Returns:
            Dict: Content analytics
        """
        try:
            analytics = {
                "content_type": item_type,
                "content_reference": item_id,
                "total_views": 0,
                "unique_viewers": 0,
                "device_breakdown": {},
                "recent_activity": []
            }
            
            if not self.db_session:
                # Fallback to cache data
                cache_views = await self.cache.get_view_count(item_type, item_id)
                analytics["total_views"] = cache_views
                return analytics
            
            # Get detailed data from database
            stmt = select(ContentView).where(
                and_(
                    ContentView.content_type == item_type,
                    ContentView.content_reference == item_id
                )
            )
            result = await self.db_session.execute(stmt)
            views = result.scalars().all()
            
            # Calculate analytics
            analytics["total_views"] = sum(view.view_count for view in views)
            analytics["unique_viewers"] = len([v for v in views if v.user_id])
            
            # Device breakdown
            device_counts = {}
            for view in views:
                if view.device_type:
                    device_counts[view.device_type] = device_counts.get(view.device_type, 0) + view.view_count
            analytics["device_breakdown"] = device_counts
            
            # Recent activity (last 10 views)
            recent_views = sorted(views, key=lambda x: x.last_viewed_at, reverse=True)[:10]
            analytics["recent_activity"] = [
                {
                    "timestamp": view.last_viewed_at.isoformat(),
                    "device_type": view.device_type,
                    "view_count": view.view_count
                }
                for view in recent_views
            ]
            
            return analytics
            
        except Exception as e:
            self.logger.error(f"Error getting content analytics: {str(e)}")
            return {
                "content_type": item_type,
                "content_reference": item_id,
                "error": str(e)
            }
    
    async def bulk_track_views(self, views: List[Dict],
                              background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """
        Track multiple views in bulk.
        
        Args:
            views: List of view data dictionaries
            background_tasks: Optional background tasks
            
        Returns:
            Dict: Bulk tracking result
        """
        try:
            successful_tracks = 0
            failed_tracks = 0
            
            for view_data in views:
                try:
                    await self.track_view(
                        view_data.get("item_type"),
                        view_data.get("item_id"),
                        view_data.get("user_id"),
                        view_data.get("device_type"),
                        view_data.get("ip_address"),
                        background_tasks
                    )
                    successful_tracks += 1
                except Exception as e:
                    self.logger.error(f"Failed to track view: {str(e)}")
                    failed_tracks += 1
            
            return {
                "success": True,
                "total_views": len(views),
                "successful_tracks": successful_tracks,
                "failed_tracks": failed_tracks
            }
            
        except Exception as e:
            self.logger.error(f"Error in bulk track views: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def clear_view_data(self, item_type: Optional[str] = None,
                             item_id: Optional[str] = None) -> Dict:
        """
        Clear view data from cache and database.
        
        Args:
            item_type: Optional specific item type to clear
            item_id: Optional specific item ID to clear
            
        Returns:
            Dict: Clear operation result
        """
        try:
            cleared_cache = 0
            cleared_db = 0
            
            if item_type and item_id:
                # Clear specific item
                await self.cache.delete(f"constitution:views:{item_type}:{item_id}")
                cleared_cache = 1
                
                if self.db_session:
                    stmt = select(ContentView).where(
                        and_(
                            ContentView.content_type == item_type,
                            ContentView.content_reference == item_id
                        )
                    )
                    result = await self.db_session.execute(stmt)
                    views = result.scalars().all()
                    
                    for view in views:
                        await self.db_session.delete(view)
                    
                    cleared_db = len(views)
                    await self.db_session.commit()
            else:
                # Clear all view data
                cleared_cache = await self.cache.clear_pattern("constitution:views:*")
                
                if self.db_session:
                    stmt = select(ContentView)
                    result = await self.db_session.execute(stmt)
                    views = result.scalars().all()
                    
                    for view in views:
                        await self.db_session.delete(view)
                    
                    cleared_db = len(views)
                    await self.db_session.commit()
            
            return {
                "success": True,
                "cleared_cache_entries": cleared_cache,
                "cleared_db_entries": cleared_db
            }
            
        except Exception as e:
            self.logger.error(f"Error clearing view data: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }