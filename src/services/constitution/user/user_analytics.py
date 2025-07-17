"""
User analytics service for constitution content.
Handles user-specific analytics and insights.
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from fastapi import BackgroundTasks

from ..base import BaseService, ConstitutionCacheManager
from ....utils.cache import HOUR
from .bookmark_manager import BookmarkManager
from .reading_progress import ReadingProgressManager
from ..analytics.view_tracker import ViewTracker


class UserAnalytics(BaseService):
    """
    Service for user-specific analytics and insights.
    Combines user data to provide comprehensive analytics.
    """
    
    def __init__(self, cache_manager: ConstitutionCacheManager,
                 bookmark_manager: BookmarkManager,
                 reading_progress_manager: ReadingProgressManager,
                 view_tracker: ViewTracker):
        """
        Initialize the user analytics service.
        
        Args:
            cache_manager: Cache manager instance
            bookmark_manager: Bookmark manager service
            reading_progress_manager: Reading progress manager service
            view_tracker: View tracker service
        """
        super().__init__(cache_manager)
        self.bookmark_manager = bookmark_manager
        self.reading_progress_manager = reading_progress_manager
        self.view_tracker = view_tracker
    
    def get_service_name(self) -> str:
        """Get the service name."""
        return "user_analytics"
    
    async def get_user_dashboard(self, user_id: str,
                               background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """
        Get comprehensive user dashboard data.
        
        Args:
            user_id: User ID
            background_tasks: Optional background tasks
            
        Returns:
            Dict: User dashboard data
        """
        try:
            # Validate user ID
            user_id = self.validator.validate_user_id(user_id)
            
            cache_key = self._generate_cache_key("user_dashboard", user_id)
            
            # Check cache first
            cached_dashboard = await self._cache_get(cache_key)
            if cached_dashboard:
                return cached_dashboard
            
            # Gather user data
            dashboard = await self._compile_user_dashboard(user_id)
            
            # Cache the dashboard
            await self._cache_set(cache_key, dashboard, HOUR, background_tasks)
            
            return dashboard
            
        except Exception as e:
            self._handle_service_error(e, f"Error getting user dashboard for user {user_id}")
    
    async def _compile_user_dashboard(self, user_id: str) -> Dict:
        """
        Compile user dashboard data from various sources.
        
        Args:
            user_id: User ID
            
        Returns:
            Dict: Dashboard data
        """
        try:
            # Get reading progress
            reading_progress = await self.reading_progress_manager.get_user_reading_progress(user_id)
            
            # Get bookmarks
            bookmarks = await self.bookmark_manager.get_user_bookmarks(user_id)
            
            # Get view history
            view_history = await self.view_tracker.get_user_view_history(user_id, 50)
            
            # Get reading statistics
            reading_stats = await self.reading_progress_manager.get_reading_statistics(user_id)
            
            # Get bookmark statistics
            bookmark_stats = await self.bookmark_manager.get_bookmark_statistics(user_id)
            
            # Compile dashboard
            dashboard = {
                "user_id": user_id,
                "reading_progress": reading_progress,
                "bookmarks": {
                    "total": len(bookmarks),
                    "recent": bookmarks[:5],  # Recent 5 bookmarks
                    "statistics": bookmark_stats
                },
                "reading_statistics": reading_stats,
                "activity_summary": self._generate_activity_summary(view_history, reading_progress),
                "achievements": await self._calculate_achievements(user_id, reading_stats, bookmark_stats),
                "recommendations": await self._generate_recommendations(user_id, reading_progress, bookmarks),
                "generated_at": datetime.now().isoformat()
            }
            
            return dashboard
            
        except Exception as e:
            self.logger.error(f"Error compiling user dashboard: {str(e)}")
            return {"error": str(e)}
    
    def _generate_activity_summary(self, view_history: List[Dict], reading_progress: Dict) -> Dict:
        """
        Generate activity summary from view history and reading progress.
        
        Args:
            view_history: User view history
            reading_progress: User reading progress
            
        Returns:
            Dict: Activity summary
        """
        try:
            # Calculate recent activity
            recent_activity = []
            for view in view_history[:10]:  # Last 10 activities
                recent_activity.append({
                    "type": "view",
                    "content_type": view["content_type"],
                    "content_reference": view["content_reference"],
                    "timestamp": view["last_viewed_at"]
                })
            
            # Calculate activity metrics
            total_views = sum(view["view_count"] for view in view_history)
            unique_content = len(set(f"{view['content_type']}:{view['content_reference']}" for view in view_history))
            
            return {
                "total_views": total_views,
                "unique_content_viewed": unique_content,
                "recent_activity": recent_activity,
                "last_activity": view_history[0]["last_viewed_at"] if view_history else None,
                "total_read_time": reading_progress.get("total_read_time_minutes", 0)
            }
            
        except Exception as e:
            self.logger.error(f"Error generating activity summary: {str(e)}")
            return {"error": str(e)}
    
    async def _calculate_achievements(self, user_id: str, reading_stats: Dict, bookmark_stats: Dict) -> List[Dict]:
        """
        Calculate user achievements based on activity.
        
        Args:
            user_id: User ID
            reading_stats: Reading statistics
            bookmark_stats: Bookmark statistics
            
        Returns:
            List[Dict]: User achievements
        """
        try:
            achievements = []
            
            # Reading achievements
            completed_chapters = reading_stats.get("completed_chapters", 0)
            completed_articles = reading_stats.get("completed_articles", 0)
            total_read_time = reading_stats.get("total_read_time_minutes", 0)
            
            # Chapter reading achievements
            if completed_chapters >= 1:
                achievements.append({
                    "type": "reading",
                    "title": "First Chapter",
                    "description": "Completed your first chapter",
                    "icon": "📖",
                    "earned_at": datetime.now().isoformat()
                })
            
            if completed_chapters >= 5:
                achievements.append({
                    "type": "reading",
                    "title": "Chapter Explorer",
                    "description": "Completed 5 chapters",
                    "icon": "🗺️",
                    "earned_at": datetime.now().isoformat()
                })
            
            # Article reading achievements
            if completed_articles >= 10:
                achievements.append({
                    "type": "reading",
                    "title": "Article Enthusiast",
                    "description": "Completed 10 articles",
                    "icon": "📚",
                    "earned_at": datetime.now().isoformat()
                })
            
            # Time-based achievements
            if total_read_time >= 60:  # 1 hour
                achievements.append({
                    "type": "time",
                    "title": "Dedicated Reader",
                    "description": "Spent 1 hour reading",
                    "icon": "⏰",
                    "earned_at": datetime.now().isoformat()
                })
            
            # Bookmark achievements
            total_bookmarks = bookmark_stats.get("total_bookmarks", 0)
            if total_bookmarks >= 5:
                achievements.append({
                    "type": "bookmark",
                    "title": "Bookmark Collector",
                    "description": "Created 5 bookmarks",
                    "icon": "🔖",
                    "earned_at": datetime.now().isoformat()
                })
            
            return achievements
            
        except Exception as e:
            self.logger.error(f"Error calculating achievements: {str(e)}")
            return []
    
    async def _generate_recommendations(self, user_id: str, reading_progress: Dict, bookmarks: List[Dict]) -> List[Dict]:
        """
        Generate personalized recommendations for the user.
        
        Args:
            user_id: User ID
            reading_progress: User reading progress
            bookmarks: User bookmarks
            
        Returns:
            List[Dict]: Personalized recommendations
        """
        try:
            recommendations = []
            
            # Analyze user preferences
            completed_chapters = reading_progress.get("completed_chapters", [])
            completed_articles = reading_progress.get("completed_articles", [])
            
            # Recommend completing started content
            if len(completed_chapters) < 5:
                recommendations.append({
                    "type": "chapter",
                    "title": "Continue Reading Chapters",
                    "description": "You've completed some chapters. Continue exploring!",
                    "priority": "high",
                    "content_reference": None
                })
            
            # Recommend based on bookmarks
            if bookmarks:
                bookmark_types = [b["type"] for b in bookmarks]
                if "article" in bookmark_types:
                    recommendations.append({
                        "type": "article",
                        "title": "Explore Related Articles",
                        "description": "Based on your bookmarks, you might enjoy these articles",
                        "priority": "medium",
                        "content_reference": None
                    })
            
            # Recommend popular content
            recommendations.append({
                "type": "popular",
                "title": "Popular Content",
                "description": "Check out what other users are reading",
                "priority": "low",
                "content_reference": None
            })
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error generating recommendations: {str(e)}")
            return []
    
    async def get_user_insights(self, user_id: str,
                              background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """
        Get personalized insights for the user.
        
        Args:
            user_id: User ID
            background_tasks: Optional background tasks
            
        Returns:
            Dict: User insights
        """
        try:
            # Validate user ID
            user_id = self.validator.validate_user_id(user_id)
            
            cache_key = self._generate_cache_key("user_insights", user_id)
            
            # Check cache first
            cached_insights = await self._cache_get(cache_key)
            if cached_insights:
                return cached_insights
            
            # Generate insights
            insights = await self._generate_user_insights(user_id)
            
            # Cache the insights
            await self._cache_set(cache_key, insights, HOUR, background_tasks)
            
            return insights
            
        except Exception as e:
            self._handle_service_error(e, f"Error getting user insights for user {user_id}")
    
    async def _generate_user_insights(self, user_id: str) -> Dict:
        """
        Generate personalized insights for the user.
        
        Args:
            user_id: User ID
            
        Returns:
            Dict: User insights
        """
        try:
            # Get user data
            reading_stats = await self.reading_progress_manager.get_reading_statistics(user_id)
            bookmark_stats = await self.bookmark_manager.get_bookmark_statistics(user_id)
            view_history = await self.view_tracker.get_user_view_history(user_id, 100)
            
            # Generate insights
            insights = {
                "reading_insights": self._generate_reading_insights(reading_stats),
                "bookmark_insights": self._generate_bookmark_insights(bookmark_stats),
                "engagement_insights": self._generate_engagement_insights(view_history),
                "learning_path": self._suggest_learning_path(reading_stats, bookmark_stats),
                "generated_at": datetime.now().isoformat()
            }
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Error generating user insights: {str(e)}")
            return {"error": str(e)}
    
    def _generate_reading_insights(self, reading_stats: Dict) -> List[str]:
        """
        Generate reading insights from statistics.
        
        Args:
            reading_stats: Reading statistics
            
        Returns:
            List[str]: Reading insights
        """
        try:
            insights = []
            
            total_time = reading_stats.get("total_read_time_minutes", 0)
            completed_chapters = reading_stats.get("completed_chapters", 0)
            completed_articles = reading_stats.get("completed_articles", 0)
            
            if total_time > 0:
                insights.append(f"You've spent {total_time:.1f} minutes reading the constitution")
            
            if completed_chapters > 0:
                insights.append(f"You've completed {completed_chapters} chapters")
            
            if completed_articles > 0:
                insights.append(f"You've read {completed_articles} articles")
            
            # Engagement insights
            if total_time > 60:
                insights.append("You're a dedicated reader! Keep up the great work.")
            elif total_time > 30:
                insights.append("You're making good progress. Try reading for longer sessions.")
            else:
                insights.append("Consider spending more time reading to improve comprehension.")
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Error generating reading insights: {str(e)}")
            return []
    
    def _generate_bookmark_insights(self, bookmark_stats: Dict) -> List[str]:
        """
        Generate bookmark insights from statistics.
        
        Args:
            bookmark_stats: Bookmark statistics
            
        Returns:
            List[str]: Bookmark insights
        """
        try:
            insights = []
            
            total_bookmarks = bookmark_stats.get("total_bookmarks", 0)
            bookmarks_by_type = bookmark_stats.get("bookmarks_by_type", {})
            
            if total_bookmarks > 0:
                insights.append(f"You have {total_bookmarks} bookmarks")
                
                # Most bookmarked type
                if bookmarks_by_type:
                    most_bookmarked = max(bookmarks_by_type, key=bookmarks_by_type.get)
                    insights.append(f"You bookmark {most_bookmarked}s most frequently")
            else:
                insights.append("Try bookmarking important sections for easy reference later")
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Error generating bookmark insights: {str(e)}")
            return []
    
    def _generate_engagement_insights(self, view_history: List[Dict]) -> List[str]:
        """
        Generate engagement insights from view history.
        
        Args:
            view_history: View history
            
        Returns:
            List[str]: Engagement insights
        """
        try:
            insights = []
            
            if not view_history:
                insights.append("Start exploring the constitution to track your progress")
                return insights
            
            total_views = sum(view["view_count"] for view in view_history)
            unique_content = len(set(f"{view['content_type']}:{view['content_reference']}" for view in view_history))
            
            insights.append(f"You've viewed {total_views} pieces of content")
            insights.append(f"You've explored {unique_content} unique sections")
            
            # Engagement pattern
            if total_views > unique_content * 2:
                insights.append("You tend to revisit content - great for retention!")
            else:
                insights.append("You explore diverse content - excellent for comprehensive learning!")
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Error generating engagement insights: {str(e)}")
            return []
    
    def _suggest_learning_path(self, reading_stats: Dict, bookmark_stats: Dict) -> List[Dict]:
        """
        Suggest a learning path based on user data.
        
        Args:
            reading_stats: Reading statistics
            bookmark_stats: Bookmark statistics
            
        Returns:
            List[Dict]: Learning path suggestions
        """
        try:
            path = []
            
            completed_chapters = reading_stats.get("completed_chapters", 0)
            
            # Beginner path
            if completed_chapters < 3:
                path.append({
                    "step": 1,
                    "title": "Start with Fundamentals",
                    "description": "Read the preamble and first few chapters",
                    "content_references": ["preamble", "chapter/1", "chapter/2"]
                })
            
            # Intermediate path
            if completed_chapters >= 3 and completed_chapters < 8:
                path.append({
                    "step": 2,
                    "title": "Explore Rights and Freedoms",
                    "description": "Focus on the Bill of Rights",
                    "content_references": ["chapter/4", "chapter/5"]
                })
            
            # Advanced path
            if completed_chapters >= 8:
                path.append({
                    "step": 3,
                    "title": "Understand Governance",
                    "description": "Learn about government structure",
                    "content_references": ["chapter/8", "chapter/9", "chapter/10"]
                })
            
            return path
            
        except Exception as e:
            self.logger.error(f"Error suggesting learning path: {str(e)}")
            return []
    
    async def get_user_activity_timeline(self, user_id: str, days: int = 30) -> List[Dict]:
        """
        Get user activity timeline.
        
        Args:
            user_id: User ID
            days: Number of days to include
            
        Returns:
            List[Dict]: Activity timeline
        """
        try:
            # Validate user ID
            user_id = self.validator.validate_user_id(user_id)
            
            # Get view history
            view_history = await self.view_tracker.get_user_view_history(user_id, days * 10)
            
            # Get reading history
            reading_history = await self.reading_progress_manager.get_reading_history(user_id, days * 10)
            
            # Get recent bookmarks
            bookmarks = await self.bookmark_manager.get_user_bookmarks(user_id)
            
            # Combine and sort timeline
            timeline = []
            
            # Add view activities
            for view in view_history:
                timeline.append({
                    "type": "view",
                    "timestamp": view["last_viewed_at"],
                    "content_type": view["content_type"],
                    "content_reference": view["content_reference"],
                    "details": f"Viewed {view['content_type']} {view['content_reference']}"
                })
            
            # Add reading activities
            for reading in reading_history:
                timeline.append({
                    "type": "reading",
                    "timestamp": reading["last_read_at"],
                    "content_type": reading["item_type"],
                    "content_reference": reading["reference"],
                    "details": f"Read {reading['item_type']} {reading['reference']} for {reading['read_time_minutes']:.1f} minutes"
                })
            
            # Add bookmark activities
            for bookmark in bookmarks:
                timeline.append({
                    "type": "bookmark",
                    "timestamp": bookmark["created_at"],
                    "content_type": bookmark["type"],
                    "content_reference": bookmark["reference"],
                    "details": f"Bookmarked {bookmark['type']} {bookmark['reference']}"
                })
            
            # Sort by timestamp (most recent first)
            timeline.sort(key=lambda x: x["timestamp"], reverse=True)
            
            # Filter to requested days
            cutoff_date = datetime.now() - timedelta(days=days)
            filtered_timeline = [
                activity for activity in timeline
                if datetime.fromisoformat(activity["timestamp"].replace("Z", "+00:00")) >= cutoff_date
            ]
            
            return filtered_timeline[:100]  # Limit to 100 activities
            
        except Exception as e:
            self.logger.error(f"Error getting user activity timeline: {str(e)}")
            return []
    
    async def get_user_progress_report(self, user_id: str) -> Dict:
        """
        Get comprehensive progress report for the user.
        
        Args:
            user_id: User ID
            
        Returns:
            Dict: Progress report
        """
        try:
            # Validate user ID
            user_id = self.validator.validate_user_id(user_id)
            
            # Get dashboard data
            dashboard = await self.get_user_dashboard(user_id)
            
            # Get insights
            insights = await self.get_user_insights(user_id)
            
            # Get activity timeline
            timeline = await self.get_user_activity_timeline(user_id, 30)
            
            # Compile report
            report = {
                "user_id": user_id,
                "dashboard": dashboard,
                "insights": insights,
                "recent_activity": timeline[:20],  # Last 20 activities
                "report_summary": self._generate_report_summary(dashboard, insights),
                "generated_at": datetime.now().isoformat()
            }
            
            return report
            
        except Exception as e:
            self.logger.error(f"Error getting user progress report: {str(e)}")
            return {"error": str(e)}
    
    def _generate_report_summary(self, dashboard: Dict, insights: Dict) -> Dict:
        """
        Generate a summary of the progress report.
        
        Args:
            dashboard: Dashboard data
            insights: User insights
            
        Returns:
            Dict: Report summary
        """
        try:
            reading_stats = dashboard.get("reading_statistics", {})
            bookmark_stats = dashboard.get("bookmarks", {}).get("statistics", {})
            
            summary = {
                "overall_progress": "beginner",  # beginner, intermediate, advanced
                "strengths": [],
                "areas_for_improvement": [],
                "next_steps": []
            }
            
            # Determine overall progress
            completed_chapters = reading_stats.get("completed_chapters", 0)
            total_read_time = reading_stats.get("total_read_time_minutes", 0)
            
            if completed_chapters >= 10 and total_read_time >= 120:
                summary["overall_progress"] = "advanced"
            elif completed_chapters >= 5 and total_read_time >= 60:
                summary["overall_progress"] = "intermediate"
            
            # Identify strengths
            if reading_stats.get("reading_streak", 0) > 7:
                summary["strengths"].append("Consistent reading habit")
            
            if bookmark_stats.get("total_bookmarks", 0) > 10:
                summary["strengths"].append("Good at identifying important content")
            
            # Areas for improvement
            if total_read_time < 30:
                summary["areas_for_improvement"].append("Increase reading time")
            
            if completed_chapters < 3:
                summary["areas_for_improvement"].append("Complete more chapters")
            
            # Next steps
            if summary["overall_progress"] == "beginner":
                summary["next_steps"].append("Focus on reading the first 3 chapters")
            elif summary["overall_progress"] == "intermediate":
                summary["next_steps"].append("Explore the Bill of Rights in detail")
            else:
                summary["next_steps"].append("Study governance and public finance sections")
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error generating report summary: {str(e)}")
            return {"error": str(e)}