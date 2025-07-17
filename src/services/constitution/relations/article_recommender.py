"""
Article recommender service for constitution content.
Handles personalized article recommendations based on user behavior.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from fastapi import BackgroundTasks

from ..base import BaseService, ConstitutionCacheManager
from ....utils.cache import HOUR
from .content_relationships import ContentRelationships
from ..content.content_retrieval import ContentRetrieval
from ..analytics.popular_content import PopularContent
from ..user.reading_progress import ReadingProgressManager
from ..user.bookmark_manager import BookmarkManager


class ArticleRecommender(BaseService):
    """
    Service for generating personalized article recommendations.
    Uses user behavior, content relationships, and popularity to suggest articles.
    """
    
    def __init__(self, cache_manager: ConstitutionCacheManager,
                 content_relationships: ContentRelationships,
                 content_retrieval: ContentRetrieval,
                 popular_content: PopularContent,
                 reading_progress_manager: ReadingProgressManager,
                 bookmark_manager: BookmarkManager):
        """
        Initialize the article recommender.
        
        Args:
            cache_manager: Cache manager instance
            content_relationships: Content relationships service
            content_retrieval: Content retrieval service
            popular_content: Popular content service
            reading_progress_manager: Reading progress manager
            bookmark_manager: Bookmark manager
        """
        super().__init__(cache_manager)
        self.content_relationships = content_relationships
        self.content_retrieval = content_retrieval
        self.popular_content = popular_content
        self.reading_progress_manager = reading_progress_manager
        self.bookmark_manager = bookmark_manager
    
    def get_service_name(self) -> str:
        """Get the service name."""
        return "article_recommender"
    
    async def get_personalized_recommendations(self, user_id: str, limit: int = 10,
                                             background_tasks: Optional[BackgroundTasks] = None) -> List[Dict]:
        """
        Get personalized article recommendations for a user.
        
        Args:
            user_id: User ID
            limit: Maximum number of recommendations
            background_tasks: Optional background tasks
            
        Returns:
            List[Dict]: Personalized recommendations
        """
        try:
            # Validate user ID
            user_id = self.validator.validate_user_id(user_id)
            
            cache_key = self._generate_cache_key("personalized_recommendations", user_id, limit)
            
            # Check cache first
            cached_recommendations = await self._cache_get(cache_key)
            if cached_recommendations:
                return cached_recommendations
            
            # Generate recommendations
            recommendations = await self._generate_personalized_recommendations(user_id, limit)
            
            # Cache the recommendations
            await self._cache_set(cache_key, recommendations, HOUR, background_tasks)
            
            return recommendations
            
        except Exception as e:
            self._handle_service_error(e, f"Error getting personalized recommendations for user {user_id}")
    
    async def _generate_personalized_recommendations(self, user_id: str, limit: int) -> List[Dict]:
        """
        Generate personalized recommendations for a user.
        
        Args:
            user_id: User ID
            limit: Maximum number of recommendations
            
        Returns:
            List[Dict]: Personalized recommendations
        """
        try:
            recommendations = []
            
            # Get user data
            reading_progress = await self.reading_progress_manager.get_user_reading_progress(user_id)
            bookmarks = await self.bookmark_manager.get_user_bookmarks(user_id)
            
            # Strategy 1: Content-based recommendations (related to read articles)
            content_based = await self._get_content_based_recommendations(
                user_id, reading_progress, bookmarks, limit // 3
            )
            recommendations.extend(content_based)
            
            # Strategy 2: Collaborative filtering (popular among similar users)
            collaborative = await self._get_collaborative_recommendations(
                user_id, reading_progress, limit // 3
            )
            recommendations.extend(collaborative)
            
            # Strategy 3: Popular content recommendations
            popular = await self._get_popular_recommendations(
                user_id, reading_progress, limit // 3
            )
            recommendations.extend(popular)
            
            # Strategy 4: Sequential recommendations (next in sequence)
            sequential = await self._get_sequential_recommendations(
                user_id, reading_progress, limit // 4
            )
            recommendations.extend(sequential)
            
            # Remove duplicates and rank
            unique_recommendations = self._deduplicate_and_rank_recommendations(recommendations)
            
            return unique_recommendations[:limit]
            
        except Exception as e:
            self.logger.error(f"Error generating personalized recommendations: {str(e)}")
            return []
    
    async def _get_content_based_recommendations(self, user_id: str, reading_progress: Dict,
                                               bookmarks: List[Dict], limit: int) -> List[Dict]:
        """
        Get content-based recommendations.
        
        Args:
            user_id: User ID
            reading_progress: User reading progress
            bookmarks: User bookmarks
            limit: Maximum recommendations
            
        Returns:
            List[Dict]: Content-based recommendations
        """
        try:
            recommendations = []
            
            # Get articles from reading progress
            completed_articles = reading_progress.get("completed_articles", [])
            
            # Get articles from bookmarks
            bookmarked_articles = [
                bookmark["reference"] for bookmark in bookmarks 
                if bookmark["type"] == "article"
            ]
            
            # Combine all user-interacted articles
            user_articles = set(completed_articles + bookmarked_articles)
            
            # Get related articles for each user article
            for article_ref in user_articles:
                try:
                    related_articles = await self.content_relationships.get_related_articles(article_ref)
                    
                    for related in related_articles:
                        related_ref = f"{related['chapter_number']}.{related['article_number']}"
                        
                        # Skip if user has already interacted with this article
                        if related_ref in user_articles:
                            continue
                        
                        recommendations.append({
                            "chapter_number": related["chapter_number"],
                            "chapter_title": related["chapter_title"],
                            "article_number": related["article_number"],
                            "article_title": related["article_title"],
                            "reference": related_ref,
                            "recommendation_type": "content_based",
                            "reason": f"Related to {article_ref}",
                            "relevance_score": related.get("relevance_score", 0.5) * 0.8,  # Slight penalty for indirect
                            "source_article": article_ref
                        })
                except Exception as e:
                    self.logger.warning(f"Error getting related articles for {article_ref}: {str(e)}")
                    continue
            
            # Sort by relevance and limit
            recommendations.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
            return recommendations[:limit]
            
        except Exception as e:
            self.logger.error(f"Error getting content-based recommendations: {str(e)}")
            return []
    
    async def _get_collaborative_recommendations(self, user_id: str, reading_progress: Dict,
                                               limit: int) -> List[Dict]:
        """
        Get collaborative filtering recommendations.
        
        Args:
            user_id: User ID
            reading_progress: User reading progress
            limit: Maximum recommendations
            
        Returns:
            List[Dict]: Collaborative recommendations
        """
        try:
            recommendations = []
            
            # This is a simplified collaborative filtering approach
            # In a real system, you'd analyze user similarity and recommend based on similar users
            
            # For now, recommend popular content that the user hasn't read
            popular_articles = await self.popular_content.get_popular_content(
                timeframe="weekly", limit=limit * 2, content_type="article"
            )
            
            completed_articles = set(reading_progress.get("completed_articles", []))
            
            for popular in popular_articles:
                article_ref = popular.get("content_reference", "")
                
                # Skip if user has already read this article
                if article_ref in completed_articles:
                    continue
                
                try:
                    # Parse article reference
                    if "." in article_ref:
                        chapter_num, article_num = map(int, article_ref.split("."))
                        
                        # Get article details
                        article = await self.content_retrieval.get_article_by_number(
                            chapter_num, article_num
                        )
                        
                        recommendations.append({
                            "chapter_number": chapter_num,
                            "chapter_title": article.get("chapter_title", ""),
                            "article_number": article_num,
                            "article_title": article.get("article_title", ""),
                            "reference": article_ref,
                            "recommendation_type": "collaborative",
                            "reason": f"Popular among users ({popular.get('total_views', 0)} views)",
                            "relevance_score": 0.7,  # Base score for popular content
                            "popularity_score": popular.get("total_views", 0)
                        })
                except Exception as e:
                    self.logger.warning(f"Error processing popular article {article_ref}: {str(e)}")
                    continue
            
            return recommendations[:limit]
            
        except Exception as e:
            self.logger.error(f"Error getting collaborative recommendations: {str(e)}")
            return []
    
    async def _get_popular_recommendations(self, user_id: str, reading_progress: Dict,
                                         limit: int) -> List[Dict]:
        """
        Get popular content recommendations.
        
        Args:
            user_id: User ID
            reading_progress: User reading progress
            limit: Maximum recommendations
            
        Returns:
            List[Dict]: Popular content recommendations
        """
        try:
            recommendations = []
            
            # Get popular content
            popular_content = await self.popular_content.get_popular_content(
                timeframe="daily", limit=limit * 2
            )
            
            completed_articles = set(reading_progress.get("completed_articles", []))
            
            for popular in popular_content:
                content_type = popular.get("content_type", "")
                content_ref = popular.get("content_reference", "")
                
                # Focus on articles
                if content_type == "article" and content_ref not in completed_articles:
                    try:
                        chapter_num, article_num = map(int, content_ref.split("."))
                        
                        recommendations.append({
                            "chapter_number": chapter_num,
                            "chapter_title": popular.get("chapter_title", ""),
                            "article_number": article_num,
                            "article_title": popular.get("title", ""),
                            "reference": content_ref,
                            "recommendation_type": "popular",
                            "reason": f"Trending ({popular.get('total_views', 0)} views)",
                            "relevance_score": 0.6,  # Base score for trending
                            "popularity_score": popular.get("total_views", 0)
                        })
                    except Exception as e:
                        self.logger.warning(f"Error processing popular content {content_ref}: {str(e)}")
                        continue
            
            return recommendations[:limit]
            
        except Exception as e:
            self.logger.error(f"Error getting popular recommendations: {str(e)}")
            return []
    
    async def _get_sequential_recommendations(self, user_id: str, reading_progress: Dict,
                                           limit: int) -> List[Dict]:
        """
        Get sequential recommendations (next articles in sequence).
        
        Args:
            user_id: User ID
            reading_progress: User reading progress
            limit: Maximum recommendations
            
        Returns:
            List[Dict]: Sequential recommendations
        """
        try:
            recommendations = []
            
            # Get last read article
            last_read = reading_progress.get("last_read", {})
            if not last_read.get("reference"):
                return recommendations
            
            try:
                # Parse last read article
                if "." in last_read["reference"]:
                    chapter_num, article_num = map(int, last_read["reference"].split("."))
                    
                    # Get chapter data
                    chapter = await self.content_retrieval.get_chapter_by_number(chapter_num)
                    
                    # Find next article in the same chapter
                    for article in chapter.get("articles", []):
                        if article.get("article_number") == article_num + 1:
                            recommendations.append({
                                "chapter_number": chapter_num,
                                "chapter_title": chapter.get("chapter_title", ""),
                                "article_number": article["article_number"],
                                "article_title": article["article_title"],
                                "reference": f"{chapter_num}.{article['article_number']}",
                                "recommendation_type": "sequential",
                                "reason": "Next article in sequence",
                                "relevance_score": 0.9,  # High score for sequential
                                "sequence_position": "next"
                            })
                            break
                    
                    # If no next article in chapter, suggest first article of next chapter
                    if not recommendations:
                        next_chapter = await self._get_next_chapter(chapter_num)
                        if next_chapter:
                            first_article = next_chapter.get("articles", [{}])[0]
                            if first_article:
                                recommendations.append({
                                    "chapter_number": next_chapter["chapter_number"],
                                    "chapter_title": next_chapter["chapter_title"],
                                    "article_number": first_article["article_number"],
                                    "article_title": first_article["article_title"],
                                    "reference": f"{next_chapter['chapter_number']}.{first_article['article_number']}",
                                    "recommendation_type": "sequential",
                                    "reason": "First article of next chapter",
                                    "relevance_score": 0.8,
                                    "sequence_position": "next_chapter"
                                })
            
            except Exception as e:
                self.logger.warning(f"Error processing sequential recommendations: {str(e)}")
            
            return recommendations[:limit]
            
        except Exception as e:
            self.logger.error(f"Error getting sequential recommendations: {str(e)}")
            return []
    
    async def _get_next_chapter(self, current_chapter_num: int) -> Optional[Dict]:
        """
        Get the next chapter in sequence.
        
        Args:
            current_chapter_num: Current chapter number
            
        Returns:
            Optional[Dict]: Next chapter data or None
        """
        try:
            # Get all chapters
            chapters_data = await self.content_retrieval.get_all_chapters()
            
            for chapter in chapters_data.get("chapters", []):
                if chapter.get("chapter_number") == current_chapter_num + 1:
                    return chapter
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting next chapter: {str(e)}")
            return None
    
    def _deduplicate_and_rank_recommendations(self, recommendations: List[Dict]) -> List[Dict]:
        """
        Remove duplicates and rank recommendations.
        
        Args:
            recommendations: List of recommendations
            
        Returns:
            List[Dict]: Deduplicated and ranked recommendations
        """
        try:
            # Remove duplicates based on article reference
            seen = set()
            unique_recommendations = []
            
            for rec in recommendations:
                ref = rec.get("reference", "")
                if ref and ref not in seen:
                    seen.add(ref)
                    unique_recommendations.append(rec)
            
            # Sort by relevance score and recommendation type priority
            type_priority = {
                "sequential": 1,
                "content_based": 2,
                "collaborative": 3,
                "popular": 4
            }
            
            def sort_key(rec):
                type_score = type_priority.get(rec.get("recommendation_type", ""), 5)
                relevance_score = rec.get("relevance_score", 0)
                return (type_score, -relevance_score)
            
            unique_recommendations.sort(key=sort_key)
            
            return unique_recommendations
            
        except Exception as e:
            self.logger.error(f"Error deduplicating recommendations: {str(e)}")
            return recommendations
    
    async def get_recommendations_for_article(self, article_ref: str, limit: int = 5,
                                            background_tasks: Optional[BackgroundTasks] = None) -> List[Dict]:
        """
        Get recommendations for users reading a specific article.
        
        Args:
            article_ref: Article reference
            limit: Maximum recommendations
            background_tasks: Optional background tasks
            
        Returns:
            List[Dict]: Article-specific recommendations
        """
        try:
            # Validate article reference
            chapter_num, article_num = self.validator.validate_article_reference(article_ref)
            
            cache_key = self._generate_cache_key("article_recommendations", article_ref, limit)
            
            # Check cache first
            cached_recommendations = await self._cache_get(cache_key)
            if cached_recommendations:
                return cached_recommendations
            
            # Get related articles
            related_articles = await self.content_relationships.get_related_articles(article_ref)
            
            # Format as recommendations
            recommendations = []
            for related in related_articles[:limit]:
                recommendations.append({
                    "chapter_number": related["chapter_number"],
                    "chapter_title": related["chapter_title"],
                    "article_number": related["article_number"],
                    "article_title": related["article_title"],
                    "reference": f"{related['chapter_number']}.{related['article_number']}",
                    "recommendation_type": "related",
                    "reason": f"Related to current article ({related.get('relevance', 'unknown')})",
                    "relevance_score": related.get("relevance_score", 0.5),
                    "relationship_type": related.get("relevance", "unknown")
                })
            
            # Cache the recommendations
            await self._cache_set(cache_key, recommendations, HOUR, background_tasks)
            
            return recommendations
            
        except Exception as e:
            self._handle_service_error(e, f"Error getting recommendations for article {article_ref}")
    
    async def get_reading_path_suggestions(self, user_id: str,
                                         background_tasks: Optional[BackgroundTasks] = None) -> List[Dict]:
        """
        Get suggested reading paths for a user.
        
        Args:
            user_id: User ID
            background_tasks: Optional background tasks
            
        Returns:
            List[Dict]: Reading path suggestions
        """
        try:
            # Validate user ID
            user_id = self.validator.validate_user_id(user_id)
            
            cache_key = self._generate_cache_key("reading_path", user_id)
            
            # Check cache first
            cached_paths = await self._cache_get(cache_key)
            if cached_paths:
                return cached_paths
            
            # Get user progress
            reading_progress = await self.reading_progress_manager.get_user_reading_progress(user_id)
            
            # Generate reading paths
            paths = await self._generate_reading_paths(reading_progress)
            
            # Cache the paths
            await self._cache_set(cache_key, paths, HOUR, background_tasks)
            
            return paths
            
        except Exception as e:
            self._handle_service_error(e, f"Error getting reading path suggestions for user {user_id}")
    
    async def _generate_reading_paths(self, reading_progress: Dict) -> List[Dict]:
        """
        Generate suggested reading paths.
        
        Args:
            reading_progress: User reading progress
            
        Returns:
            List[Dict]: Reading paths
        """
        try:
            paths = []
            
            completed_chapters = len(reading_progress.get("completed_chapters", []))
            
            # Beginner path
            if completed_chapters < 3:
                paths.append({
                    "path_id": "beginner",
                    "title": "Constitution Basics",
                    "description": "Start with fundamental concepts",
                    "difficulty": "beginner",
                    "estimated_time": "2-3 hours",
                    "articles": [
                        {"reference": "1.1", "title": "Sovereignty of the people"},
                        {"reference": "1.2", "title": "Supremacy of the Constitution"},
                        {"reference": "2.9", "title": "National symbols and national days"},
                        {"reference": "3.10", "title": "Citizenship"}
                    ]
                })
            
            # Rights and freedoms path
            if completed_chapters >= 2:
                paths.append({
                    "path_id": "rights",
                    "title": "Rights and Freedoms",
                    "description": "Explore the Bill of Rights",
                    "difficulty": "intermediate",
                    "estimated_time": "4-5 hours",
                    "articles": [
                        {"reference": "4.19", "title": "Rights and fundamental freedoms"},
                        {"reference": "4.20", "title": "Legislative authority in respect of fundamental rights"},
                        {"reference": "4.21", "title": "Enforcement of Bill of Rights"}
                    ]
                })
            
            # Governance path
            if completed_chapters >= 5:
                paths.append({
                    "path_id": "governance",
                    "title": "Government Structure",
                    "description": "Learn about Kenya's governance system",
                    "difficulty": "advanced",
                    "estimated_time": "6-8 hours",
                    "articles": [
                        {"reference": "8.93", "title": "Parliament"},
                        {"reference": "9.131", "title": "Executive authority"},
                        {"reference": "10.159", "title": "Judicial authority"}
                    ]
                })
            
            return paths
            
        except Exception as e:
            self.logger.error(f"Error generating reading paths: {str(e)}")
            return []
    
    async def get_recommendation_feedback(self, user_id: str, article_ref: str,
                                        feedback_type: str, background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """
        Process user feedback on recommendations.
        
        Args:
            user_id: User ID
            article_ref: Article reference
            feedback_type: Type of feedback (helpful, not_helpful, read)
            background_tasks: Optional background tasks
            
        Returns:
            Dict: Feedback processing result
        """
        try:
            # Validate inputs
            user_id = self.validator.validate_user_id(user_id)
            chapter_num, article_num = self.validator.validate_article_reference(article_ref)
            
            # Process feedback (in a real system, you'd store this for ML training)
            feedback_data = {
                "user_id": user_id,
                "article_ref": article_ref,
                "feedback_type": feedback_type,
                "timestamp": datetime.now().isoformat()
            }
            
            # For now, just log the feedback
            self.logger.info(f"Recommendation feedback: {feedback_data}")
            
            # Clear user recommendation cache to refresh recommendations
            await self._cache_delete(f"personalized_recommendations:{user_id}:*")
            
            return {
                "success": True,
                "message": "Feedback recorded successfully",
                "feedback": feedback_data
            }
            
        except Exception as e:
            self.logger.error(f"Error processing recommendation feedback: {str(e)}")
            return {"success": False, "message": str(e)}