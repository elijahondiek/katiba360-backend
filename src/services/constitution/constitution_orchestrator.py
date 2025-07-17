"""
Constitution orchestrator service.
Coordinates all constitution-related services and maintains backward compatibility.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseService, ConstitutionCacheManager, ConstitutionValidator
from ...utils.cache import CacheManager

# Content services
from .content import ContentLoader, ContentRetrieval, ContentOverview

# Search services
from .search import SearchEngine, QueryProcessor, ResultHighlighter

# Analytics services
from .analytics import ViewTracker, PopularContent, AnalyticsReporter

# User services
from .user import BookmarkManager, ReadingProgressManager, UserAnalytics

# Relations services
from .relations import ContentRelationships, ArticleRecommender


class ConstitutionOrchestrator(BaseService):
    """
    Main orchestrator for all constitution services.
    Provides a unified interface while maintaining backward compatibility.
    """
    
    def __init__(self, redis_client, db_session: Optional[AsyncSession] = None):
        """
        Initialize the constitution orchestrator.
        
        Args:
            redis_client: Redis client for caching
            db_session: Database session
        """
        # Initialize base components
        self.base_cache = CacheManager(redis_client, "constitution")
        self.cache = ConstitutionCacheManager(redis_client, "constitution")
        self.validator = ConstitutionValidator()
        
        # Initialize base service
        super().__init__(self.cache, db_session, self.validator)
        
        # Initialize content services
        self.content_loader = ContentLoader(self.cache)
        self.content_retrieval = ContentRetrieval(self.cache, self.content_loader)
        self.content_overview = ContentOverview(self.cache, self.content_loader)
        
        # Initialize search services
        self.query_processor = QueryProcessor(self.cache)
        self.result_highlighter = ResultHighlighter(self.cache)
        self.search_engine = SearchEngine(
            self.cache, self.content_loader, self.query_processor, self.result_highlighter
        )
        
        # Initialize analytics services
        self.view_tracker = ViewTracker(self.cache, db_session)
        self.popular_content = PopularContent(self.cache, self.content_retrieval, db_session)
        self.analytics_reporter = AnalyticsReporter(
            self.cache, self.view_tracker, self.popular_content, db_session
        )
        
        # Initialize user services
        self.bookmark_manager = BookmarkManager(self.cache, db_session)
        self.reading_progress_manager = ReadingProgressManager(self.cache, db_session)
        self.user_analytics = UserAnalytics(
            self.cache, self.bookmark_manager, self.reading_progress_manager, self.view_tracker
        )
        
        # Initialize relations services
        self.content_relationships = ContentRelationships(
            self.cache, self.content_loader, self.content_retrieval
        )
        self.article_recommender = ArticleRecommender(
            self.cache, self.content_relationships, self.content_retrieval,
            self.popular_content, self.reading_progress_manager, self.bookmark_manager
        )
    
    def get_service_name(self) -> str:
        """Get the service name."""
        return "constitution_orchestrator"
    
    # ======================
    # Content API Methods
    # ======================
    
    async def get_constitution_overview(self, background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """
        Get constitution overview.
        
        Args:
            background_tasks: Optional background tasks
            
        Returns:
            Dict: Constitution overview
        """
        return await self.content_overview.get_constitution_overview(background_tasks)
    
    async def get_all_chapters(self, background_tasks: Optional[BackgroundTasks] = None,
                              limit: Optional[int] = None, offset: Optional[int] = 0,
                              fields: Optional[List[str]] = None) -> Dict:
        """
        Get all chapters with pagination.
        
        Args:
            background_tasks: Optional background tasks
            limit: Maximum number of chapters
            offset: Number of chapters to skip
            fields: Specific fields to include
            
        Returns:
            Dict: Chapters data with pagination
        """
        return await self.content_retrieval.get_all_chapters(
            background_tasks, limit, offset, fields
        )
    
    async def get_chapter_by_number(self, chapter_num: int,
                                   background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """
        Get chapter by number.
        
        Args:
            chapter_num: Chapter number
            background_tasks: Optional background tasks
            
        Returns:
            Dict: Chapter data
        """
        return await self.content_retrieval.get_chapter_by_number(chapter_num, background_tasks)
    
    async def get_article_by_number(self, chapter_num: int, article_num: int,
                                   background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """
        Get article by number.
        
        Args:
            chapter_num: Chapter number
            article_num: Article number
            background_tasks: Optional background tasks
            
        Returns:
            Dict: Article data
        """
        return await self.content_retrieval.get_article_by_number(
            chapter_num, article_num, background_tasks
        )
    
    async def get_content_tree(self, background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """
        Get content tree structure.
        
        Args:
            background_tasks: Optional background tasks
            
        Returns:
            Dict: Content tree
        """
        return await self.content_retrieval.get_content_tree(background_tasks)
    
    async def get_preamble(self, background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """
        Get constitution preamble.
        
        Args:
            background_tasks: Optional background tasks
            
        Returns:
            Dict: Preamble data
        """
        return await self.content_retrieval.get_preamble(background_tasks)
    
    # ======================
    # Search API Methods
    # ======================
    
    async def search_constitution(self, query: str, filters: Optional[Dict] = None,
                                 limit: Optional[int] = 10, offset: Optional[int] = 0,
                                 highlight: bool = True,
                                 background_tasks: Optional[BackgroundTasks] = None,
                                 no_cache: bool = False) -> Dict:
        """
        Search the constitution.
        
        Args:
            query: Search query
            filters: Optional filters
            limit: Maximum results
            offset: Results offset
            highlight: Whether to highlight matches
            background_tasks: Optional background tasks
            no_cache: Whether to bypass cache
            
        Returns:
            Dict: Search results
        """
        return await self.search_engine.search_constitution(
            query, filters, limit, offset, highlight, background_tasks, no_cache
        )
    
    async def get_search_suggestions(self, query: str, limit: int = 5) -> List[str]:
        """
        Get search suggestions.
        
        Args:
            query: Partial query
            limit: Maximum suggestions
            
        Returns:
            List[str]: Search suggestions
        """
        return await self.search_engine.search_suggestions(query, limit)
    
    # ======================
    # Analytics API Methods
    # ======================
    
    async def track_view(self, item_type: str, item_id: str,
                        user_id: Optional[str] = None,
                        device_type: Optional[str] = None,
                        ip_address: Optional[str] = None,
                        background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """
        Track a content view.
        
        Args:
            item_type: Type of content
            item_id: Content ID
            user_id: Optional user ID
            device_type: Optional device type
            ip_address: Optional IP address
            background_tasks: Optional background tasks
            
        Returns:
            Dict: Tracking result
        """
        return await self.view_tracker.track_view(
            item_type, item_id, user_id, device_type, ip_address, background_tasks
        )
    
    async def get_popular_sections(self, timeframe: str = "daily", limit: int = 5,
                                  background_tasks: Optional[BackgroundTasks] = None) -> List[Dict]:
        """
        Get popular sections.
        
        Args:
            timeframe: Timeframe for popularity
            limit: Maximum sections
            background_tasks: Optional background tasks
            
        Returns:
            List[Dict]: Popular sections
        """
        return await self.popular_content.get_popular_content(timeframe, limit, background_tasks=background_tasks)
    
    async def get_analytics_summary(self, timeframe: str = "daily",
                                   background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """
        Get analytics summary.
        
        Args:
            timeframe: Timeframe for analysis
            background_tasks: Optional background tasks
            
        Returns:
            Dict: Analytics summary
        """
        return await self.analytics_reporter.get_analytics_summary(timeframe, background_tasks)
    
    # ======================
    # User API Methods
    # ======================
    
    async def get_user_bookmarks(self, user_id: str,
                                background_tasks: Optional[BackgroundTasks] = None) -> List[Dict]:
        """
        Get user bookmarks.
        
        Args:
            user_id: User ID
            background_tasks: Optional background tasks
            
        Returns:
            List[Dict]: User bookmarks
        """
        return await self.bookmark_manager.get_user_bookmarks(user_id, background_tasks)
    
    async def add_user_bookmark(self, user_id: str, bookmark_type: str, reference: str,
                               title: str, background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """
        Add user bookmark.
        
        Args:
            user_id: User ID
            bookmark_type: Bookmark type
            reference: Reference string
            title: Bookmark title
            background_tasks: Optional background tasks
            
        Returns:
            Dict: Operation result
        """
        return await self.bookmark_manager.add_bookmark(
            user_id, bookmark_type, reference, title, background_tasks
        )
    
    async def remove_user_bookmark(self, user_id: str, bookmark_id: str,
                                  background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """
        Remove user bookmark.
        
        Args:
            user_id: User ID
            bookmark_id: Bookmark ID
            background_tasks: Optional background tasks
            
        Returns:
            Dict: Operation result
        """
        return await self.bookmark_manager.remove_bookmark(user_id, bookmark_id, background_tasks)
    
    async def get_user_reading_progress(self, user_id: str,
                                       background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """
        Get user reading progress.
        
        Args:
            user_id: User ID
            background_tasks: Optional background tasks
            
        Returns:
            Dict: Reading progress
        """
        return await self.reading_progress_manager.get_user_reading_progress(user_id, background_tasks)
    
    async def update_user_reading_progress(self, user_id: str, item_type: str, reference: str,
                                         read_time_minutes: float = 1.0,
                                         background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """
        Update user reading progress.
        
        Args:
            user_id: User ID
            item_type: Item type
            reference: Reference string
            read_time_minutes: Reading time
            background_tasks: Optional background tasks
            
        Returns:
            Dict: Updated progress
        """
        return await self.reading_progress_manager.update_reading_progress(
            user_id, item_type, reference, read_time_minutes, background_tasks
        )
    
    async def get_user_dashboard(self, user_id: str,
                               background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """
        Get user dashboard.
        
        Args:
            user_id: User ID
            background_tasks: Optional background tasks
            
        Returns:
            Dict: User dashboard
        """
        return await self.user_analytics.get_user_dashboard(user_id, background_tasks)
    
    # ======================
    # Relations API Methods
    # ======================
    
    async def get_related_articles(self, article_ref: str,
                                  background_tasks: Optional[BackgroundTasks] = None) -> List[Dict]:
        """
        Get related articles.
        
        Args:
            article_ref: Article reference
            background_tasks: Optional background tasks
            
        Returns:
            List[Dict]: Related articles
        """
        return await self.content_relationships.get_related_articles(article_ref, background_tasks)
    
    async def get_personalized_recommendations(self, user_id: str, limit: int = 10,
                                             background_tasks: Optional[BackgroundTasks] = None) -> List[Dict]:
        """
        Get personalized recommendations.
        
        Args:
            user_id: User ID
            limit: Maximum recommendations
            background_tasks: Optional background tasks
            
        Returns:
            List[Dict]: Personalized recommendations
        """
        return await self.article_recommender.get_personalized_recommendations(
            user_id, limit, background_tasks
        )
    
    # ======================
    # Legacy/Compatibility Methods
    # ======================
    
    async def create_bookmark(self, user_id: str, bookmark_type: str, reference: str, title: str) -> Dict:
        """
        Create bookmark (legacy method for backward compatibility).
        
        Args:
            user_id: User ID
            bookmark_type: Bookmark type
            reference: Reference string
            title: Bookmark title
            
        Returns:
            Dict: Operation result
        """
        return await self.bookmark_manager.create_bookmark(user_id, bookmark_type, reference, title)
    
    async def get_constitution_data(self, background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """
        Get raw constitution data (legacy method).
        
        Args:
            background_tasks: Optional background tasks
            
        Returns:
            Dict: Constitution data
        """
        return await self.content_loader.get_constitution_data(background_tasks)
    
    async def reload_constitution_data(self, background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """
        Reload constitution data (legacy method).
        
        Args:
            background_tasks: Optional background tasks
            
        Returns:
            Dict: Reloaded data
        """
        return await self.content_loader.reload_constitution_data(background_tasks)
    
    # ======================
    # Service Management
    # ======================
    
    async def health_check(self) -> Dict:
        """
        Perform comprehensive health check.
        
        Returns:
            Dict: Health check results
        """
        try:
            health_results = {
                "orchestrator": {"healthy": True},
                "services": {},
                "overall_health": True
            }
            
            # Check all services
            services = {
                "content_loader": self.content_loader,
                "content_retrieval": self.content_retrieval,
                "content_overview": self.content_overview,
                "search_engine": self.search_engine,
                "view_tracker": self.view_tracker,
                "popular_content": self.popular_content,
                "analytics_reporter": self.analytics_reporter,
                "bookmark_manager": self.bookmark_manager,
                "reading_progress_manager": self.reading_progress_manager,
                "user_analytics": self.user_analytics,
                "content_relationships": self.content_relationships,
                "article_recommender": self.article_recommender
            }
            
            for service_name, service in services.items():
                try:
                    service_health = await service.health_check()
                    health_results["services"][service_name] = service_health
                    
                    if not service_health.get("healthy", False):
                        health_results["overall_health"] = False
                        
                except Exception as e:
                    health_results["services"][service_name] = {
                        "healthy": False,
                        "error": str(e)
                    }
                    health_results["overall_health"] = False
            
            return health_results
            
        except Exception as e:
            return {
                "orchestrator": {"healthy": False, "error": str(e)},
                "services": {},
                "overall_health": False
            }
    
    async def get_service_statistics(self) -> Dict:
        """
        Get statistics for all services.
        
        Returns:
            Dict: Service statistics
        """
        try:
            stats = {
                "cache_stats": await self.cache.get_cache_stats(),
                "content_stats": await self.content_loader.get_data_statistics(),
                "search_stats": await self.search_engine.get_search_statistics(),
                "generated_at": datetime.now().isoformat()
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting service statistics: {str(e)}")
            return {"error": str(e)}
    
    async def clear_all_cache(self) -> Dict:
        """
        Clear all caches.
        
        Returns:
            Dict: Clear operation result
        """
        try:
            cleared_count = await self.cache.clear_all_constitution_cache()
            
            return {
                "success": True,
                "cleared_entries": cleared_count,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error clearing cache: {str(e)}")
            return {"success": False, "error": str(e)}
    
    # ======================
    # Utility Methods
    # ======================
    
    def get_all_services(self) -> Dict[str, Any]:
        """
        Get all service instances.
        
        Returns:
            Dict[str, Any]: All service instances
        """
        return {
            "content_loader": self.content_loader,
            "content_retrieval": self.content_retrieval,
            "content_overview": self.content_overview,
            "search_engine": self.search_engine,
            "query_processor": self.query_processor,
            "result_highlighter": self.result_highlighter,
            "view_tracker": self.view_tracker,
            "popular_content": self.popular_content,
            "analytics_reporter": self.analytics_reporter,
            "bookmark_manager": self.bookmark_manager,
            "reading_progress_manager": self.reading_progress_manager,
            "user_analytics": self.user_analytics,
            "content_relationships": self.content_relationships,
            "article_recommender": self.article_recommender
        }
    
    def get_service_by_name(self, service_name: str) -> Optional[Any]:
        """
        Get a specific service by name.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Optional[Any]: Service instance or None
        """
        services = self.get_all_services()
        return services.get(service_name)
    
    async def validate_data_integrity(self) -> Dict:
        """
        Validate data integrity across all services.
        
        Returns:
            Dict: Validation results
        """
        try:
            # Validate content data
            content_validation = await self.content_loader.validate_data_integrity()
            
            # Check service connectivity
            health_check = await self.health_check()
            
            return {
                "content_validation": content_validation,
                "service_health": health_check,
                "overall_valid": (
                    content_validation.get("valid", False) and 
                    health_check.get("overall_health", False)
                ),
                "validated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error validating data integrity: {str(e)}")
            return {"error": str(e)}
    
    async def get_service_metrics(self) -> Dict:
        """
        Get comprehensive service metrics.
        
        Returns:
            Dict: Service metrics
        """
        try:
            metrics = {
                "health": await self.health_check(),
                "statistics": await self.get_service_statistics(),
                "cache_stats": await self.cache.get_cache_stats(),
                "integrity": await self.validate_data_integrity(),
                "generated_at": datetime.now().isoformat()
            }
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error getting service metrics: {str(e)}")
            return {"error": str(e)}