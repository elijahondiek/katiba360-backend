"""
Backward compatibility layer for the constitution service.
This module maintains the old API while using the new modular architecture underneath.
"""

import logging
from typing import Dict, List, Optional, Any
from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from .constitution import ConstitutionOrchestrator
from ..utils.cache import CacheManager

logger = logging.getLogger(__name__)


class ConstitutionData:
    """
    Legacy ConstitutionData class for backward compatibility.
    Wraps the new modular architecture.
    """
    
    def __init__(self, cache: CacheManager):
        self.cache = cache
        self._orchestrator = None
        self._last_loaded = None
        self.db_session = None
    
    def _get_orchestrator(self) -> ConstitutionOrchestrator:
        """Get or create the orchestrator instance."""
        if self._orchestrator is None:
            redis_client = self.cache.redis
            self._orchestrator = ConstitutionOrchestrator(redis_client, self.db_session)
        return self._orchestrator
    
    async def get_data(self, background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """Get the cached constitution data from Redis or load from file."""
        orchestrator = self._get_orchestrator()
        return await orchestrator.get_constitution_data(background_tasks)
    
    async def get_chapter(self, chapter_num: int, background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """Get a specific chapter from cache or load from file."""
        orchestrator = self._get_orchestrator()
        return await orchestrator.get_chapter_by_number(chapter_num, background_tasks)
    
    async def get_article(self, chapter_num: int, article_num: int, background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """Get a specific article from cache or load from file."""
        orchestrator = self._get_orchestrator()
        return await orchestrator.get_article_by_number(chapter_num, article_num, background_tasks)
    
    async def reload_data(self, background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """Force reload of the constitution data and update cache."""
        orchestrator = self._get_orchestrator()
        return await orchestrator.reload_constitution_data(background_tasks)
    
    def get_last_loaded(self) -> Optional[Any]:
        """Get the timestamp when the data was last loaded from file."""
        orchestrator = self._get_orchestrator()
        if hasattr(orchestrator.content_loader, 'get_last_loaded_time'):
            return orchestrator.content_loader.get_last_loaded_time()
        return self._last_loaded
    
    async def track_view(self, item_type: str, item_id: str, user_id: Optional[str] = None, 
                        device_type: Optional[str] = None, ip_address: Optional[str] = None, 
                        background_tasks: Optional[BackgroundTasks] = None) -> None:
        """Track views for analytics purposes in both database and cache."""
        orchestrator = self._get_orchestrator()
        await orchestrator.track_view(item_type, item_id, user_id, device_type, ip_address, background_tasks)
    
    async def get_popular_content_from_db(self, timeframe: str = "daily", limit: int = 10, 
                                         content_type: Optional[str] = None) -> List[Dict]:
        """Get popular content from database based on view counts."""
        orchestrator = self._get_orchestrator()
        if hasattr(orchestrator.popular_content, 'get_popular_content_from_db'):
            return await orchestrator.popular_content.get_popular_content_from_db(timeframe, limit, content_type)
        # Fallback to using the general popular content method
        popular = await orchestrator.get_popular_sections(timeframe, limit, background_tasks=None)
        # Filter by content type if specified
        if content_type:
            popular = [item for item in popular if item.get('type') == content_type]
        return popular
    
    async def get_view_trends(self, content_type: Optional[str] = None, 
                            content_reference: Optional[str] = None, 
                            days: int = 30) -> List[Dict]:
        """Get view trends over time."""
        orchestrator = self._get_orchestrator()
        if hasattr(orchestrator.analytics_reporter, 'get_view_trends'):
            return await orchestrator.analytics_reporter.get_view_trends(content_type, content_reference, days)
        return []
    
    async def get_user_view_history(self, user_id: str, limit: int = 50) -> List[Dict]:
        """Get user-specific view history."""
        orchestrator = self._get_orchestrator()
        if hasattr(orchestrator.user_analytics, 'get_user_view_history'):
            return await orchestrator.user_analytics.get_user_view_history(user_id, limit)
        return []
    
    async def get_analytics_summary(self, timeframe: str = "daily") -> Dict:
        """Get analytics summary including total views, unique users, and popular content."""
        orchestrator = self._get_orchestrator()
        return await orchestrator.get_analytics_summary(timeframe, background_tasks=None)


class ConstitutionService:
    """
    Legacy ConstitutionService class for backward compatibility.
    Wraps the new modular architecture.
    """
    
    def __init__(self, cache: CacheManager, db_session: Optional[AsyncSession] = None):
        self.cache = cache
        self.db_session = db_session
        redis_client = cache.redis
        self._orchestrator = ConstitutionOrchestrator(redis_client, db_session)
        
        # Create legacy ConstitutionData instance
        self.constitution_data = ConstitutionData(cache)
        self.constitution_data.db_session = db_session
    
    async def get_constitution_overview(self, background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """Get an overview of the constitution including metadata and structure."""
        return await self._orchestrator.get_constitution_overview(background_tasks)
    
    async def get_all_chapters(self, background_tasks: Optional[BackgroundTasks] = None, 
                              limit: Optional[int] = None, offset: Optional[int] = 0, 
                              fields: Optional[List[str]] = None) -> Dict:
        """Get all chapters with pagination support."""
        return await self._orchestrator.get_all_chapters(background_tasks, limit, offset, fields)
    
    async def get_chapter_by_number(self, chapter_num: int, background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """Get a specific chapter by its number."""
        return await self._orchestrator.get_chapter_by_number(chapter_num, background_tasks)
    
    async def get_article_by_number(self, chapter_num: int, article_num: int, background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """Get a specific article by its chapter and article number."""
        return await self._orchestrator.get_article_by_number(chapter_num, article_num, background_tasks)
    
    async def search_constitution(self, query: str, filters: Optional[Dict] = None, 
                                 limit: Optional[int] = 10, offset: Optional[int] = 0,
                                 highlight: bool = True, background_tasks: Optional[BackgroundTasks] = None,
                                 no_cache: bool = False) -> Dict:
        """Search the constitution for a specific query with optional filters."""
        return await self._orchestrator.search_constitution(query, filters, limit, offset, highlight, background_tasks, no_cache)
    
    def _generate_search_hash(self, query: str, filters: Optional[Dict] = None, 
                              limit: Optional[int] = 10, offset: Optional[int] = 0,
                              highlight: bool = True) -> str:
        """Generate a consistent hash for search parameters to use as cache key."""
        if hasattr(self._orchestrator.search_engine, '_generate_search_hash'):
            return self._orchestrator.search_engine._generate_search_hash(query, filters, limit, offset, highlight)
        # Fallback implementation
        import hashlib
        import json
        filters_str = json.dumps(filters, sort_keys=True) if filters else "none"
        params_str = f"{query}:{filters_str}:{limit}:{offset}:{highlight}"
        return hashlib.md5(params_str.encode()).hexdigest()
    
    def _highlight_text(self, text: str, query: str) -> str:
        """Highlight the query in the text."""
        if hasattr(self._orchestrator.result_highlighter, 'highlight_text'):
            return self._orchestrator.result_highlighter.highlight_text(text, query)
        # Fallback implementation
        if not query or not text:
            return text
        text_lower = text.lower()
        query_lower = query.lower()
        if query_lower not in text_lower:
            return text
        result = ""
        last_end = 0
        for i in range(len(text_lower)):
            if text_lower[i:i+len(query_lower)] == query_lower:
                result += text[last_end:i] + "**" + text[i:i+len(query_lower)] + "**"
                last_end = i + len(query_lower)
        result += text[last_end:]
        return result
    
    async def get_related_articles(self, article_ref: str, background_tasks: Optional[BackgroundTasks] = None) -> List[Dict]:
        """Find articles related to a specific article reference."""
        return await self._orchestrator.get_related_articles(article_ref, background_tasks)
    
    async def get_user_bookmarks(self, user_id: str, background_tasks: Optional[BackgroundTasks] = None) -> List[Dict]:
        """Get bookmarks for a specific user."""
        return await self._orchestrator.get_user_bookmarks(user_id, background_tasks)
    
    async def add_user_bookmark(self, user_id: str, bookmark_type: str, reference: str, 
                               title: str, background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """Add a bookmark for a specific user."""
        return await self._orchestrator.add_user_bookmark(user_id, bookmark_type, reference, title, background_tasks)
    
    async def remove_user_bookmark(self, user_id: str, bookmark_id: str, 
                              background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """Remove a bookmark for a specific user."""
        return await self._orchestrator.remove_user_bookmark(user_id, bookmark_id, background_tasks)
    
    async def create_bookmark(self, user_id: str, bookmark_type: str, reference: str, title: str) -> Dict:
        """Create a new bookmark for a user (alias for add_user_bookmark for convenience)."""
        return await self._orchestrator.create_bookmark(user_id, bookmark_type, reference, title)
    
    async def get_user_reading_progress(self, user_id: str, background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """Get reading progress for a specific user."""
        return await self._orchestrator.get_user_reading_progress(user_id, background_tasks)
    
    async def update_user_reading_progress(self, user_id: str, item_type: str, reference: str, 
                                         read_time_minutes: float = 1.0, 
                                         background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """Update reading progress for a specific user."""
        return await self._orchestrator.update_user_reading_progress(user_id, item_type, reference, read_time_minutes, background_tasks)
    
    async def get_popular_sections(self, timeframe: str = "daily", limit: int = 5, background_tasks: Optional[BackgroundTasks] = None) -> List[Dict]:
        """Get popular sections of the constitution based on analytics data."""
        return await self._orchestrator.get_popular_sections(timeframe, limit, background_tasks)
    
    # Legacy methods for supporting old code
    async def _search_in_chapter_titles(self, data: Dict, query_lower: str, filters: Optional[Dict], highlight: bool, query: str) -> List[Dict]:
        """Legacy method - delegates to orchestrator's search engine."""
        # This would be handled internally by the search engine
        return []
    
    async def _search_in_articles(self, data: Dict, query_lower: str, filters: Optional[Dict], highlight: bool, query: str) -> List[Dict]:
        """Legacy method - delegates to orchestrator's search engine."""
        # This would be handled internally by the search engine
        return []
    
    async def _search_in_clauses(self, chapter: Dict, article: Dict, query_lower: str, highlight: bool, query: str) -> List[Dict]:
        """Legacy method - delegates to orchestrator's search engine."""
        # This would be handled internally by the search engine
        return []