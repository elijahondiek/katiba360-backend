"""
Analytics reporter for constitution services.
Handles analytics reporting, trends, and insights generation.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from fastapi import BackgroundTasks
from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..base import BaseService, ConstitutionCacheManager
from ....utils.cache import HOUR
from ....models.user_models import ContentView
from .view_tracker import ViewTracker
from .popular_content import PopularContent


class AnalyticsReporter(BaseService):
    """
    Service for generating analytics reports and insights.
    Handles comprehensive analytics reporting and trend analysis.
    """
    
    def __init__(self, cache_manager: ConstitutionCacheManager,
                 view_tracker: ViewTracker,
                 popular_content: PopularContent,
                 db_session: Optional[AsyncSession] = None):
        """
        Initialize the analytics reporter.
        
        Args:
            cache_manager: Cache manager instance
            view_tracker: View tracker service
            popular_content: Popular content service
            db_session: Database session
        """
        super().__init__(cache_manager, db_session)
        self.view_tracker = view_tracker
        self.popular_content = popular_content
    
    def get_service_name(self) -> str:
        """Get the service name."""
        return "analytics_reporter"
    
    async def get_analytics_summary(self, timeframe: str = "daily",
                                   background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """
        Get comprehensive analytics summary.
        
        Args:
            timeframe: Timeframe for analysis
            background_tasks: Optional background tasks
            
        Returns:
            Dict: Analytics summary
        """
        try:
            # Validate timeframe
            timeframe = self.validator.validate_timeframe(timeframe)
            
            cache_key = self._generate_cache_key("analytics_summary", timeframe)
            
            # Check cache first
            cached_summary = await self._cache_get(cache_key)
            if cached_summary:
                return cached_summary
            
            # Generate summary
            summary = await self._generate_analytics_summary(timeframe)
            
            # Cache the summary
            await self._cache_set(cache_key, summary, HOUR, background_tasks)
            
            return summary
            
        except Exception as e:
            self._handle_service_error(e, f"Error getting analytics summary for {timeframe}")
    
    async def _generate_analytics_summary(self, timeframe: str) -> Dict:
        """
        Generate analytics summary for the given timeframe.
        
        Args:
            timeframe: Timeframe for analysis
            
        Returns:
            Dict: Analytics summary
        """
        try:
            if not self.db_session:
                return self._get_fallback_analytics_summary(timeframe)
            
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
            
            # Get total views
            total_views_query = select(func.sum(ContentView.view_count)).where(
                ContentView.last_viewed_at >= start_date
            )
            total_views_result = await self.db_session.execute(total_views_query)
            total_views = total_views_result.scalar() or 0
            
            # Get unique users
            unique_users_query = select(func.count(func.distinct(ContentView.user_id))).where(
                and_(
                    ContentView.last_viewed_at >= start_date,
                    ContentView.user_id.is_not(None)
                )
            )
            unique_users_result = await self.db_session.execute(unique_users_query)
            unique_users = unique_users_result.scalar() or 0
            
            # Get content type breakdown
            content_type_query = select(
                ContentView.content_type,
                func.sum(ContentView.view_count).label('total_views')
            ).where(
                ContentView.last_viewed_at >= start_date
            ).group_by(ContentView.content_type)
            
            content_type_result = await self.db_session.execute(content_type_query)
            content_breakdown = {}
            for row in content_type_result:
                content_breakdown[row.content_type] = row.total_views
            
            # Get device type breakdown
            device_type_query = select(
                ContentView.device_type,
                func.sum(ContentView.view_count).label('total_views')
            ).where(
                and_(
                    ContentView.last_viewed_at >= start_date,
                    ContentView.device_type.is_not(None)
                )
            ).group_by(ContentView.device_type)
            
            device_type_result = await self.db_session.execute(device_type_query)
            device_breakdown = {}
            for row in device_type_result:
                device_breakdown[row.device_type] = row.total_views
            
            # Get popular content
            popular_content = await self.popular_content.get_popular_content(timeframe, 10)
            
            # Get trending content
            trending_content = await self.popular_content.get_trending_content(timeframe, 5)
            
            return {
                "timeframe": timeframe,
                "period_start": start_date.isoformat(),
                "period_end": now.isoformat(),
                "metrics": {
                    "total_views": total_views,
                    "unique_users": unique_users,
                    "average_views_per_user": round(total_views / unique_users, 2) if unique_users > 0 else 0
                },
                "content_breakdown": content_breakdown,
                "device_breakdown": device_breakdown,
                "popular_content": popular_content,
                "trending_content": trending_content,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error generating analytics summary: {str(e)}")
            return self._get_fallback_analytics_summary(timeframe)
    
    def _get_fallback_analytics_summary(self, timeframe: str) -> Dict:
        """
        Get fallback analytics summary when database is unavailable.
        
        Args:
            timeframe: Timeframe for analysis
            
        Returns:
            Dict: Fallback analytics summary
        """
        return {
            "timeframe": timeframe,
            "period_start": datetime.now().isoformat(),
            "period_end": datetime.now().isoformat(),
            "metrics": {
                "total_views": 0,
                "unique_users": 0,
                "average_views_per_user": 0
            },
            "content_breakdown": {},
            "device_breakdown": {},
            "popular_content": [],
            "trending_content": [],
            "generated_at": datetime.now().isoformat(),
            "note": "Database unavailable - showing fallback data"
        }
    
    async def get_view_trends(self, content_type: Optional[str] = None,
                            content_reference: Optional[str] = None,
                            days: int = 30,
                            background_tasks: Optional[BackgroundTasks] = None) -> List[Dict]:
        """
        Get view trends over time.
        
        Args:
            content_type: Optional content type filter
            content_reference: Optional content reference filter
            days: Number of days to analyze
            background_tasks: Optional background tasks
            
        Returns:
            List[Dict]: View trends data
        """
        try:
            cache_key = self._generate_cache_key("view_trends", content_type or "all", 
                                               content_reference or "all", days)
            
            # Check cache first
            cached_trends = await self._cache_get(cache_key)
            if cached_trends:
                return cached_trends
            
            # Get trends from database
            trends = await self._get_view_trends_from_database(
                content_type, content_reference, days
            )
            
            # Cache the trends
            await self._cache_set(cache_key, trends, HOUR, background_tasks)
            
            return trends
            
        except Exception as e:
            self.logger.error(f"Error getting view trends: {str(e)}")
            return []
    
    async def _get_view_trends_from_database(self, content_type: Optional[str],
                                           content_reference: Optional[str],
                                           days: int) -> List[Dict]:
        """
        Get view trends from database.
        
        Args:
            content_type: Optional content type filter
            content_reference: Optional content reference filter
            days: Number of days to analyze
            
        Returns:
            List[Dict]: View trends data
        """
        try:
            if not self.db_session:
                return []
            
            # Calculate date range
            now = datetime.now()
            start_date = now - timedelta(days=days)
            
            # Build query for daily view trends
            query = select(
                func.date(ContentView.last_viewed_at).label('date'),
                func.sum(ContentView.view_count).label('total_views'),
                func.count(ContentView.id).label('unique_sessions')
            ).where(
                ContentView.last_viewed_at >= start_date
            ).group_by(
                func.date(ContentView.last_viewed_at)
            ).order_by(
                'date'
            )
            
            # Apply filters
            if content_type:
                query = query.where(ContentView.content_type == content_type)
            if content_reference:
                query = query.where(ContentView.content_reference == content_reference)
            
            result = await self.db_session.execute(query)
            rows = result.fetchall()
            
            trends = []
            for row in rows:
                trends.append({
                    "date": row.date.isoformat(),
                    "total_views": row.total_views,
                    "unique_sessions": row.unique_sessions
                })
            
            return trends
            
        except Exception as e:
            self.logger.error(f"Error getting view trends from database: {str(e)}")
            return []
    
    async def get_user_engagement_metrics(self, user_id: str,
                                        background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """
        Get user engagement metrics.
        
        Args:
            user_id: User ID
            background_tasks: Optional background tasks
            
        Returns:
            Dict: User engagement metrics
        """
        try:
            # Validate user ID
            user_id = self.validator.validate_user_id(user_id)
            
            cache_key = self._generate_cache_key("user_engagement", user_id)
            
            # Check cache first
            cached_metrics = await self._cache_get(cache_key)
            if cached_metrics:
                return cached_metrics
            
            # Get user view history
            view_history = await self.view_tracker.get_user_view_history(user_id, 100)
            
            # Calculate engagement metrics
            metrics = self._calculate_user_engagement_metrics(view_history)
            
            # Cache the metrics
            await self._cache_set(cache_key, metrics, HOUR, background_tasks)
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error getting user engagement metrics: {str(e)}")
            return {"error": str(e)}
    
    def _calculate_user_engagement_metrics(self, view_history: List[Dict]) -> Dict:
        """
        Calculate user engagement metrics from view history.
        
        Args:
            view_history: User view history
            
        Returns:
            Dict: Engagement metrics
        """
        try:
            if not view_history:
                return {
                    "total_views": 0,
                    "unique_content_viewed": 0,
                    "favorite_content_type": None,
                    "engagement_score": 0,
                    "last_activity": None
                }
            
            total_views = sum(view["view_count"] for view in view_history)
            unique_content = len(set(f"{view['content_type']}:{view['content_reference']}" 
                                   for view in view_history))
            
            # Calculate content type preferences
            content_type_counts = {}
            for view in view_history:
                content_type = view["content_type"]
                content_type_counts[content_type] = content_type_counts.get(content_type, 0) + view["view_count"]
            
            favorite_content_type = max(content_type_counts, key=content_type_counts.get) if content_type_counts else None
            
            # Calculate engagement score (simplified)
            engagement_score = min(100, (total_views * 2) + (unique_content * 5))
            
            # Get last activity
            last_activity = max(view["last_viewed_at"] for view in view_history) if view_history else None
            
            return {
                "total_views": total_views,
                "unique_content_viewed": unique_content,
                "favorite_content_type": favorite_content_type,
                "content_type_breakdown": content_type_counts,
                "engagement_score": engagement_score,
                "last_activity": last_activity
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating user engagement metrics: {str(e)}")
            return {"error": str(e)}
    
    async def get_content_performance_report(self, content_type: str, content_reference: str,
                                           background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """
        Get comprehensive performance report for specific content.
        
        Args:
            content_type: Type of content
            content_reference: Reference to content
            background_tasks: Optional background tasks
            
        Returns:
            Dict: Content performance report
        """
        try:
            cache_key = self._generate_cache_key("content_performance", content_type, content_reference)
            
            # Check cache first
            cached_report = await self._cache_get(cache_key)
            if cached_report:
                return cached_report
            
            # Get content analytics
            analytics = await self.view_tracker.get_content_analytics(content_type, content_reference)
            
            # Get popularity scores for different timeframes
            daily_score = await self.popular_content.get_content_popularity_score(
                content_type, content_reference, "daily"
            )
            weekly_score = await self.popular_content.get_content_popularity_score(
                content_type, content_reference, "weekly"
            )
            monthly_score = await self.popular_content.get_content_popularity_score(
                content_type, content_reference, "monthly"
            )
            
            # Get view trends
            trends = await self.get_view_trends(content_type, content_reference, 30)
            
            # Compile report
            report = {
                "content_type": content_type,
                "content_reference": content_reference,
                "analytics": analytics,
                "popularity_scores": {
                    "daily": daily_score,
                    "weekly": weekly_score,
                    "monthly": monthly_score
                },
                "view_trends": trends,
                "generated_at": datetime.now().isoformat()
            }
            
            # Cache the report
            await self._cache_set(cache_key, report, HOUR, background_tasks)
            
            return report
            
        except Exception as e:
            self.logger.error(f"Error getting content performance report: {str(e)}")
            return {"error": str(e)}
    
    async def get_search_analytics(self, timeframe: str = "daily",
                                  background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """
        Get search analytics and insights.
        
        Args:
            timeframe: Timeframe for analysis
            background_tasks: Optional background tasks
            
        Returns:
            Dict: Search analytics
        """
        try:
            cache_key = self._generate_cache_key("search_analytics", timeframe)
            
            # Check cache first
            cached_analytics = await self._cache_get(cache_key)
            if cached_analytics:
                return cached_analytics
            
            # Get popular search terms
            popular_searches = await self.popular_content.get_popular_search_terms(timeframe, 20)
            
            # Get search trends
            search_trends = await self.get_view_trends("search", None, 30)
            
            # Compile analytics
            analytics = {
                "timeframe": timeframe,
                "popular_searches": popular_searches,
                "search_trends": search_trends,
                "insights": self._generate_search_insights(popular_searches),
                "generated_at": datetime.now().isoformat()
            }
            
            # Cache the analytics
            await self._cache_set(cache_key, analytics, HOUR, background_tasks)
            
            return analytics
            
        except Exception as e:
            self.logger.error(f"Error getting search analytics: {str(e)}")
            return {"error": str(e)}
    
    def _generate_search_insights(self, popular_searches: List[Dict]) -> List[str]:
        """
        Generate insights from popular search terms.
        
        Args:
            popular_searches: Popular search terms
            
        Returns:
            List[str]: Search insights
        """
        try:
            insights = []
            
            if not popular_searches:
                return ["No search data available for analysis"]
            
            # Top search term
            top_search = popular_searches[0]
            insights.append(f"Most popular search term: '{top_search['search_term']}' with {top_search['search_count']} searches")
            
            # Search volume analysis
            total_searches = sum(search["search_count"] for search in popular_searches)
            insights.append(f"Total searches analyzed: {total_searches}")
            
            # Common themes
            legal_terms = ["rights", "freedom", "constitution", "law", "court", "government"]
            legal_searches = [s for s in popular_searches if any(term in s["search_term"].lower() for term in legal_terms)]
            
            if legal_searches:
                insights.append(f"Legal/constitutional terms make up {len(legal_searches)} of the top {len(popular_searches)} searches")
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Error generating search insights: {str(e)}")
            return ["Error generating insights"]
    
    async def generate_insights_report(self, timeframe: str = "weekly",
                                     background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """
        Generate comprehensive insights report.
        
        Args:
            timeframe: Timeframe for analysis
            background_tasks: Optional background tasks
            
        Returns:
            Dict: Insights report
        """
        try:
            cache_key = self._generate_cache_key("insights_report", timeframe)
            
            # Check cache first
            cached_report = await self._cache_get(cache_key)
            if cached_report:
                return cached_report
            
            # Get analytics summary
            analytics_summary = await self.get_analytics_summary(timeframe)
            
            # Get search analytics
            search_analytics = await self.get_search_analytics(timeframe)
            
            # Generate insights
            insights = self._generate_comprehensive_insights(analytics_summary, search_analytics)
            
            # Compile report
            report = {
                "timeframe": timeframe,
                "analytics_summary": analytics_summary,
                "search_analytics": search_analytics,
                "insights": insights,
                "generated_at": datetime.now().isoformat()
            }
            
            # Cache the report
            await self._cache_set(cache_key, report, 2 * HOUR, background_tasks)
            
            return report
            
        except Exception as e:
            self.logger.error(f"Error generating insights report: {str(e)}")
            return {"error": str(e)}
    
    def _generate_comprehensive_insights(self, analytics_summary: Dict, search_analytics: Dict) -> List[str]:
        """
        Generate comprehensive insights from analytics data.
        
        Args:
            analytics_summary: Analytics summary
            search_analytics: Search analytics
            
        Returns:
            List[str]: Comprehensive insights
        """
        try:
            insights = []
            
            # Usage insights
            metrics = analytics_summary.get("metrics", {})
            total_views = metrics.get("total_views", 0)
            unique_users = metrics.get("unique_users", 0)
            
            if total_views > 0:
                insights.append(f"Platform received {total_views} total views from {unique_users} unique users")
            
            # Content type insights
            content_breakdown = analytics_summary.get("content_breakdown", {})
            if content_breakdown:
                most_viewed_type = max(content_breakdown, key=content_breakdown.get)
                insights.append(f"Most viewed content type: {most_viewed_type} ({content_breakdown[most_viewed_type]} views)")
            
            # Popular content insights
            popular_content = analytics_summary.get("popular_content", [])
            if popular_content:
                top_content = popular_content[0]
                insights.append(f"Most popular content: {top_content.get('title', 'Unknown')} with {top_content.get('total_views', 0)} views")
            
            # Device insights
            device_breakdown = analytics_summary.get("device_breakdown", {})
            if device_breakdown:
                most_used_device = max(device_breakdown, key=device_breakdown.get)
                insights.append(f"Most used device type: {most_used_device} ({device_breakdown[most_used_device]} views)")
            
            # Search insights
            search_insights = search_analytics.get("insights", [])
            insights.extend(search_insights)
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Error generating comprehensive insights: {str(e)}")
            return ["Error generating insights"]