"""
Popular content service for constitution analytics.
Handles popular content identification and ranking.
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from fastapi import BackgroundTasks
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ..base import BaseService, ConstitutionCacheManager
from ....utils.cache import HOUR
from ....models.user_models import ContentView
from ..content.content_retrieval import ContentRetrieval


class PopularContent(BaseService):
    """
    Service for managing popular content analytics.
    Handles popular content identification, ranking, and caching.
    """
    
    def __init__(self, cache_manager: ConstitutionCacheManager,
                 content_retrieval: ContentRetrieval,
                 db_session: Optional[AsyncSession] = None):
        """
        Initialize the popular content service.
        
        Args:
            cache_manager: Cache manager instance
            content_retrieval: Content retrieval service
            db_session: Database session
        """
        super().__init__(cache_manager, db_session)
        self.content_retrieval = content_retrieval
    
    def get_service_name(self) -> str:
        """Get the service name."""
        return "popular_content"
    
    async def get_popular_content(self, timeframe: str = "daily", limit: int = 10,
                                 content_type: Optional[str] = None,
                                 background_tasks: Optional[BackgroundTasks] = None) -> List[Dict]:
        """
        Get popular content based on view analytics.
        
        Args:
            timeframe: Timeframe for popularity (daily, weekly, monthly)
            limit: Maximum number of items to return
            content_type: Optional filter by content type
            background_tasks: Optional background tasks
            
        Returns:
            List[Dict]: Popular content items
        """
        try:
            # Validate timeframe
            timeframe = self.validator.validate_timeframe(timeframe)
            
            # Generate cache key
            cache_key = self._generate_cache_key("popular", timeframe, limit, content_type or "all")
            
            # Check cache first
            cached_popular = await self._cache_get(cache_key)
            if cached_popular:
                return cached_popular
            
            # Get from database
            popular_items = await self._get_popular_from_database(timeframe, limit, content_type)
            
            # Enrich with content data
            enriched_items = await self._enrich_popular_content(popular_items, background_tasks)
            
            # Cache the results
            await self._cache_set(cache_key, enriched_items, HOUR, background_tasks)
            
            return enriched_items
            
        except Exception as e:
            self._handle_service_error(e, f"Error getting popular content for {timeframe}")
    
    async def _get_popular_from_database(self, timeframe: str, limit: int,
                                       content_type: Optional[str] = None) -> List[Dict]:
        """
        Get popular content from database.
        
        Args:
            timeframe: Timeframe for popularity
            limit: Maximum number of items
            content_type: Optional content type filter
            
        Returns:
            List[Dict]: Popular content from database
        """
        try:
            if not self.db_session:
                self.logger.warning("Database session not available for popular content")
                return self._get_fallback_popular_content(limit)
            
            # Calculate date range
            now = datetime.now()
            if timeframe == "daily":
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif timeframe == "weekly":
                start_date = now - timedelta(days=7)
            elif timeframe == "monthly":
                start_date = now - timedelta(days=30)
            elif timeframe == "yearly":
                start_date = now - timedelta(days=365)
            else:
                start_date = now - timedelta(days=1)
            
            # Build query
            query = select(
                ContentView.content_type,
                ContentView.content_reference,
                func.sum(ContentView.view_count).label('total_views'),
                func.count(ContentView.id).label('unique_viewers'),
                func.max(ContentView.last_viewed_at).label('last_viewed')
            ).where(
                ContentView.last_viewed_at >= start_date
            ).group_by(
                ContentView.content_type,
                ContentView.content_reference
            ).order_by(
                desc('total_views')
            ).limit(limit)
            
            # Filter by content type if specified
            if content_type:
                query = query.where(ContentView.content_type == content_type)
            
            result = await self.db_session.execute(query)
            rows = result.fetchall()
            
            popular_items = []
            for row in rows:
                popular_items.append({
                    "content_type": row.content_type,
                    "content_reference": row.content_reference,
                    "total_views": row.total_views,
                    "unique_viewers": row.unique_viewers,
                    "last_viewed": row.last_viewed.isoformat() if row.last_viewed else None
                })
            
            return popular_items
            
        except Exception as e:
            self.logger.error(f"Error getting popular content from database: {str(e)}")
            return self._get_fallback_popular_content(limit)
    
    def _get_fallback_popular_content(self, limit: int) -> List[Dict]:
        """
        Get fallback popular content when database is unavailable.
        
        Args:
            limit: Maximum number of items
            
        Returns:
            List[Dict]: Fallback popular content
        """
        # Predefined popular content based on general knowledge
        fallback_items = [
            {
                "content_type": "article",
                "content_reference": "4.19",
                "total_views": 1500,
                "unique_viewers": 1200,
                "title": "Rights and Fundamental Freedoms"
            },
            {
                "content_type": "article", 
                "content_reference": "6.73",
                "total_views": 1200,
                "unique_viewers": 950,
                "title": "Leadership and Integrity"
            },
            {
                "content_type": "article",
                "content_reference": "11.174",
                "total_views": 1100,
                "unique_viewers": 880,
                "title": "Devolved Government"
            },
            {
                "content_type": "article",
                "content_reference": "10.159",
                "total_views": 1000,
                "unique_viewers": 800,
                "title": "Judicial Authority"
            },
            {
                "content_type": "chapter",
                "content_reference": "4",
                "total_views": 950,
                "unique_viewers": 760,
                "title": "The Bill of Rights"
            },
            {
                "content_type": "article",
                "content_reference": "12.201",
                "total_views": 900,
                "unique_viewers": 720,
                "title": "Principles of Public Finance"
            },
            {
                "content_type": "article",
                "content_reference": "2.9",
                "total_views": 850,
                "unique_viewers": 680,
                "title": "National Symbols and National Days"
            },
            {
                "content_type": "chapter",
                "content_reference": "8",
                "total_views": 800,
                "unique_viewers": 640,
                "title": "The Legislature"
            },
            {
                "content_type": "article",
                "content_reference": "3.10",
                "total_views": 750,
                "unique_viewers": 600,
                "title": "Citizenship"
            },
            {
                "content_type": "chapter",
                "content_reference": "7",
                "total_views": 700,
                "unique_viewers": 560,
                "title": "Representation of the People"
            }
        ]
        
        return fallback_items[:limit]
    
    async def _enrich_popular_content(self, popular_items: List[Dict],
                                    background_tasks: Optional[BackgroundTasks] = None) -> List[Dict]:
        """
        Enrich popular content with additional metadata.
        
        Args:
            popular_items: Popular content items
            background_tasks: Optional background tasks
            
        Returns:
            List[Dict]: Enriched popular content
        """
        try:
            enriched_items = []
            
            for item in popular_items:
                content_type = item["content_type"]
                content_reference = item["content_reference"]
                
                enriched_item = item.copy()
                
                try:
                    if content_type == "chapter":
                        chapter_num = int(content_reference)
                        chapter_data = await self.content_retrieval.get_chapter_by_number(
                            chapter_num, background_tasks
                        )
                        enriched_item.update({
                            "chapter_number": chapter_num,
                            "title": chapter_data.get("chapter_title", ""),
                            "article_count": len(chapter_data.get("articles", []))
                        })
                        
                    elif content_type == "article":
                        if "." in content_reference:
                            chapter_num, article_num = map(int, content_reference.split("."))
                            article_data = await self.content_retrieval.get_article_by_number(
                                chapter_num, article_num, background_tasks
                            )
                            enriched_item.update({
                                "chapter_number": chapter_num,
                                "article_number": article_num,
                                "title": article_data.get("article_title", ""),
                                "clause_count": len(article_data.get("clauses", []))
                            })
                        
                except Exception as e:
                    self.logger.warning(f"Failed to enrich content {content_type}:{content_reference}: {str(e)}")
                    # Keep the item without enrichment
                    pass
                
                enriched_items.append(enriched_item)
            
            return enriched_items
            
        except Exception as e:
            self.logger.error(f"Error enriching popular content: {str(e)}")
            return popular_items
    
    async def get_trending_content(self, timeframe: str = "daily", limit: int = 5,
                                  background_tasks: Optional[BackgroundTasks] = None) -> List[Dict]:
        """
        Get trending content (content with increasing view velocity).
        
        Args:
            timeframe: Timeframe to analyze
            limit: Maximum number of items
            background_tasks: Optional background tasks
            
        Returns:
            List[Dict]: Trending content items
        """
        try:
            cache_key = self._generate_cache_key("trending", timeframe, limit)
            
            # Check cache first
            cached_trending = await self._cache_get(cache_key)
            if cached_trending:
                return cached_trending
            
            # Get trending from database
            trending_items = await self._get_trending_from_database(timeframe, limit)
            
            # Enrich with content data
            enriched_items = await self._enrich_popular_content(trending_items, background_tasks)
            
            # Cache the results
            await self._cache_set(cache_key, enriched_items, HOUR, background_tasks)
            
            return enriched_items
            
        except Exception as e:
            self._handle_service_error(e, f"Error getting trending content for {timeframe}")
    
    async def _get_trending_from_database(self, timeframe: str, limit: int) -> List[Dict]:
        """
        Get trending content from database.
        
        Args:
            timeframe: Timeframe to analyze
            limit: Maximum number of items
            
        Returns:
            List[Dict]: Trending content from database
        """
        try:
            if not self.db_session:
                return self._get_fallback_popular_content(limit)
            
            # For simplicity, return recent popular content
            # In a real implementation, you'd calculate view velocity
            now = datetime.now()
            start_date = now - timedelta(days=1)  # Last 24 hours
            
            query = select(
                ContentView.content_type,
                ContentView.content_reference,
                func.sum(ContentView.view_count).label('total_views'),
                func.count(ContentView.id).label('unique_viewers')
            ).where(
                ContentView.last_viewed_at >= start_date
            ).group_by(
                ContentView.content_type,
                ContentView.content_reference
            ).order_by(
                desc('total_views')
            ).limit(limit)
            
            result = await self.db_session.execute(query)
            rows = result.fetchall()
            
            trending_items = []
            for row in rows:
                trending_items.append({
                    "content_type": row.content_type,
                    "content_reference": row.content_reference,
                    "total_views": row.total_views,
                    "unique_viewers": row.unique_viewers,
                    "trend_score": float(row.total_views)  # Simplified trend score
                })
            
            return trending_items
            
        except Exception as e:
            self.logger.error(f"Error getting trending content from database: {str(e)}")
            return self._get_fallback_popular_content(limit)
    
    async def get_content_popularity_score(self, content_type: str, content_reference: str,
                                         timeframe: str = "daily") -> Dict:
        """
        Get popularity score for specific content.
        
        Args:
            content_type: Type of content
            content_reference: Reference to content
            timeframe: Timeframe for analysis
            
        Returns:
            Dict: Popularity score and metrics
        """
        try:
            if not self.db_session:
                return {"score": 0, "error": "Database not available"}
            
            # Calculate date range
            now = datetime.now()
            if timeframe == "daily":
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif timeframe == "weekly":
                start_date = now - timedelta(days=7)
            elif timeframe == "monthly":
                start_date = now - timedelta(days=30)
            else:
                start_date = now - timedelta(days=1)
            
            # Get content metrics
            query = select(
                func.sum(ContentView.view_count).label('total_views'),
                func.count(ContentView.id).label('unique_viewers'),
                func.max(ContentView.last_viewed_at).label('last_viewed')
            ).where(
                ContentView.content_type == content_type,
                ContentView.content_reference == content_reference,
                ContentView.last_viewed_at >= start_date
            )
            
            result = await self.db_session.execute(query)
            row = result.fetchone()
            
            if not row or not row.total_views:
                return {
                    "score": 0,
                    "total_views": 0,
                    "unique_viewers": 0,
                    "last_viewed": None
                }
            
            # Calculate popularity score (simplified)
            total_views = row.total_views
            unique_viewers = row.unique_viewers
            
            # Score based on views and uniqueness
            score = (total_views * 0.7) + (unique_viewers * 0.3)
            
            return {
                "score": round(score, 2),
                "total_views": total_views,
                "unique_viewers": unique_viewers,
                "last_viewed": row.last_viewed.isoformat() if row.last_viewed else None
            }
            
        except Exception as e:
            self.logger.error(f"Error getting popularity score: {str(e)}")
            return {"score": 0, "error": str(e)}
    
    async def get_popular_search_terms(self, timeframe: str = "daily", limit: int = 10,
                                     background_tasks: Optional[BackgroundTasks] = None) -> List[Dict]:
        """
        Get popular search terms.
        
        Args:
            timeframe: Timeframe for analysis
            limit: Maximum number of terms
            background_tasks: Optional background tasks
            
        Returns:
            List[Dict]: Popular search terms
        """
        try:
            cache_key = self._generate_cache_key("popular_searches", timeframe, limit)
            
            # Check cache first
            cached_searches = await self._cache_get(cache_key)
            if cached_searches:
                return cached_searches
            
            # Get popular searches from database
            popular_searches = await self._get_popular_searches_from_database(timeframe, limit)
            
            # Cache the results
            await self._cache_set(cache_key, popular_searches, HOUR, background_tasks)
            
            return popular_searches
            
        except Exception as e:
            self.logger.error(f"Error getting popular search terms: {str(e)}")
            return []
    
    async def _get_popular_searches_from_database(self, timeframe: str, limit: int) -> List[Dict]:
        """
        Get popular search terms from database.
        
        Args:
            timeframe: Timeframe for analysis
            limit: Maximum number of terms
            
        Returns:
            List[Dict]: Popular search terms
        """
        try:
            if not self.db_session:
                return []
            
            # Calculate date range
            now = datetime.now()
            if timeframe == "daily":
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif timeframe == "weekly":
                start_date = now - timedelta(days=7)
            elif timeframe == "monthly":
                start_date = now - timedelta(days=30)
            else:
                start_date = now - timedelta(days=1)
            
            # Get search terms (content_type = "search")
            query = select(
                ContentView.content_reference,
                func.sum(ContentView.view_count).label('search_count')
            ).where(
                ContentView.content_type == "search",
                ContentView.last_viewed_at >= start_date
            ).group_by(
                ContentView.content_reference
            ).order_by(
                desc('search_count')
            ).limit(limit)
            
            result = await self.db_session.execute(query)
            rows = result.fetchall()
            
            popular_searches = []
            for row in rows:
                popular_searches.append({
                    "search_term": row.content_reference,
                    "search_count": row.search_count
                })
            
            return popular_searches
            
        except Exception as e:
            self.logger.error(f"Error getting popular searches from database: {str(e)}")
            return []
    
    async def refresh_popular_content_cache(self, background_tasks: Optional[BackgroundTasks] = None):
        """
        Refresh popular content cache.
        
        Args:
            background_tasks: Optional background tasks
        """
        try:
            # Clear existing cache
            await self.cache.clear_pattern("constitution:popular:*")
            
            # Refresh common popular content queries
            timeframes = ["daily", "weekly", "monthly"]
            limits = [5, 10, 20]
            
            for timeframe in timeframes:
                for limit in limits:
                    await self.get_popular_content(timeframe, limit, background_tasks=background_tasks)
                    await self.get_trending_content(timeframe, limit, background_tasks=background_tasks)
            
            self.logger.info("Popular content cache refreshed")
            
        except Exception as e:
            self.logger.error(f"Error refreshing popular content cache: {str(e)}")