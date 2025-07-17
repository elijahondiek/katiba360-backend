"""
Content retrieval service for constitution data.
Handles retrieval of specific constitution content like chapters and articles.
"""

from typing import Dict, List, Optional
from fastapi import BackgroundTasks

from ..base import BaseService, ConstitutionCacheManager
from ....utils.cache import HOUR, DAY
from .content_loader import ContentLoader


class ContentRetrieval(BaseService):
    """
    Service for retrieving specific constitution content.
    Handles chapters, articles, and related content retrieval with caching.
    """
    
    def __init__(self, cache_manager: ConstitutionCacheManager, 
                 content_loader: ContentLoader):
        """
        Initialize the content retrieval service.
        
        Args:
            cache_manager: Cache manager instance
            content_loader: Content loader instance
        """
        super().__init__(cache_manager)
        self.content_loader = content_loader
    
    def get_service_name(self) -> str:
        """Get the service name."""
        return "content_retrieval"
    
    async def get_all_chapters(self, background_tasks: Optional[BackgroundTasks] = None,
                              limit: Optional[int] = None, offset: Optional[int] = 0,
                              fields: Optional[List[str]] = None) -> Dict:
        """
        Get all chapters with pagination support.
        
        Args:
            background_tasks: Optional background tasks for async caching
            limit: Maximum number of chapters to return
            offset: Number of chapters to skip
            fields: Specific fields to include in the response
            
        Returns:
            Dict: Chapters data with pagination info
        """
        try:
            # Validate parameters
            if limit is not None:
                limit = max(1, min(limit, 100))  # Limit between 1-100
            offset = max(0, offset or 0)
            
            # Generate cache key based on parameters
            cache_key = self._generate_cache_key(
                "chapters", "list", limit, offset, ",".join(fields) if fields else "all"
            )
            
            # Try to get from cache first
            cached_chapters = await self._cache_get(cache_key)
            if cached_chapters:
                return cached_chapters
            
            # Get constitution data
            data = await self.content_loader.get_constitution_data(background_tasks)
            chapters = data.get("chapters", [])
            
            # Apply pagination
            total_chapters = len(chapters)
            if limit is not None:
                paginated_chapters = chapters[offset:offset + limit]
            else:
                paginated_chapters = chapters[offset:]
            
            # Apply field filtering if specified
            if fields:
                filtered_chapters = []
                for chapter in paginated_chapters:
                    filtered_chapter = {}
                    for field in fields:
                        if field in chapter:
                            filtered_chapter[field] = chapter[field]
                    filtered_chapters.append(filtered_chapter)
                paginated_chapters = filtered_chapters
            
            # Calculate pagination info
            safe_limit = limit or 10
            result = {
                "chapters": paginated_chapters,
                "pagination": {
                    "total": total_chapters,
                    "limit": limit,
                    "offset": offset,
                    "has_next": offset + safe_limit < total_chapters,
                    "has_previous": offset > 0,
                    "next_offset": offset + safe_limit if offset + safe_limit < total_chapters else None,
                    "previous_offset": offset - safe_limit if offset - safe_limit >= 0 else None
                }
            }
            
            # Cache the result
            await self._cache_set(cache_key, result, HOUR, background_tasks)
            
            return result
            
        except Exception as e:
            self._handle_service_error(e, "Error getting all chapters")
    
    async def get_chapter_by_number(self, chapter_num: int, 
                                   background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """
        Get a specific chapter by its number.
        
        Args:
            chapter_num: The chapter number to retrieve
            background_tasks: Optional background tasks for async caching
            
        Returns:
            Dict: Chapter data
            
        Raises:
            ValueError: If chapter not found
        """
        try:
            # Validate chapter number
            chapter_num = self.validator.validate_chapter_number(chapter_num)
            
            # Try to get from cache first
            cached_chapter = await self.cache.get_chapter(chapter_num)
            if cached_chapter:
                return cached_chapter
            
            # Get constitution data
            data = await self.content_loader.get_constitution_data(background_tasks)
            
            # Find the chapter
            for chapter in data.get("chapters", []):
                if chapter.get("chapter_number") == chapter_num:
                    # Cache the chapter
                    await self.cache.set_chapter(chapter_num, chapter, DAY)
                    return chapter
            
            # Chapter not found
            error_msg = f"Chapter {chapter_num} not found"
            self.logger.warning(error_msg)
            raise ValueError(error_msg)
            
        except ValueError:
            raise
        except Exception as e:
            self._handle_service_error(e, f"Error getting chapter {chapter_num}")
    
    async def get_article_by_number(self, chapter_num: int, article_num: int,
                                   background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """
        Get a specific article by its chapter and article number.
        
        Args:
            chapter_num: The chapter number
            article_num: The article number
            background_tasks: Optional background tasks for async caching
            
        Returns:
            Dict: Article data
            
        Raises:
            ValueError: If chapter or article not found
        """
        try:
            # Validate parameters
            chapter_num = self.validator.validate_chapter_number(chapter_num)
            article_num = self.validator.validate_article_number(article_num)
            
            # Try to get from cache first
            cached_article = await self.cache.get_article(chapter_num, article_num)
            if cached_article:
                return cached_article
            
            # Get the chapter first
            chapter = await self.get_chapter_by_number(chapter_num, background_tasks)
            
            # Find the article
            for article in chapter.get("articles", []):
                if article.get("article_number") == article_num:
                    # Cache the article
                    await self.cache.set_article(chapter_num, article_num, article, DAY)
                    return article
            
            # Article not found
            error_msg = f"Article {article_num} not found in chapter {chapter_num}"
            self.logger.warning(error_msg)
            raise ValueError(error_msg)
            
        except ValueError:
            raise
        except Exception as e:
            self._handle_service_error(e, f"Error getting article {chapter_num}.{article_num}")
    
    async def get_article_by_reference(self, reference: str,
                                     background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """
        Get an article by its reference (e.g., "1.2" for Chapter 1, Article 2).
        
        Args:
            reference: Article reference string
            background_tasks: Optional background tasks for async caching
            
        Returns:
            Dict: Article data
            
        Raises:
            ValueError: If reference format is invalid or article not found
        """
        try:
            # Validate and parse reference
            chapter_num, article_num = self.validator.validate_article_reference(reference)
            
            # Get the article
            return await self.get_article_by_number(chapter_num, article_num, background_tasks)
            
        except ValueError:
            raise
        except Exception as e:
            self._handle_service_error(e, f"Error getting article by reference {reference}")
    
    async def get_chapters_summary(self, background_tasks: Optional[BackgroundTasks] = None) -> List[Dict]:
        """
        Get a summary of all chapters with basic information.
        
        Args:
            background_tasks: Optional background tasks for async caching
            
        Returns:
            List[Dict]: List of chapter summaries
        """
        try:
            cache_key = self._generate_cache_key("chapters", "summary")
            
            # Try to get from cache first
            cached_summary = await self._cache_get(cache_key)
            if cached_summary:
                return cached_summary
            
            # Get constitution data
            data = await self.content_loader.get_constitution_data(background_tasks)
            
            # Create chapter summaries
            summaries = []
            for chapter in data.get("chapters", []):
                summary = {
                    "chapter_number": chapter.get("chapter_number"),
                    "chapter_title": chapter.get("chapter_title"),
                    "article_count": len(chapter.get("articles", [])),
                    "articles": [
                        {
                            "article_number": article.get("article_number"),
                            "article_title": article.get("article_title")
                        }
                        for article in chapter.get("articles", [])
                    ]
                }
                summaries.append(summary)
            
            # Cache the summary
            await self._cache_set(cache_key, summaries, 6 * HOUR, background_tasks)
            
            return summaries
            
        except Exception as e:
            self._handle_service_error(e, "Error getting chapters summary")
    
    async def get_article_content(self, chapter_num: int, article_num: int,
                                 include_clauses: bool = True,
                                 background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """
        Get detailed article content with optional clause inclusion.
        
        Args:
            chapter_num: Chapter number
            article_num: Article number
            include_clauses: Whether to include clauses and sub-clauses
            background_tasks: Optional background tasks for async caching
            
        Returns:
            Dict: Detailed article content
        """
        try:
            # Get the article
            article = await self.get_article_by_number(chapter_num, article_num, background_tasks)
            
            # If clauses are not requested, remove them
            if not include_clauses and "clauses" in article:
                article = article.copy()
                del article["clauses"]
            
            return article
            
        except Exception as e:
            self._handle_service_error(e, f"Error getting article content {chapter_num}.{article_num}")
    
    async def get_chapter_articles(self, chapter_num: int,
                                  background_tasks: Optional[BackgroundTasks] = None) -> List[Dict]:
        """
        Get all articles in a specific chapter.
        
        Args:
            chapter_num: Chapter number
            background_tasks: Optional background tasks for async caching
            
        Returns:
            List[Dict]: List of articles in the chapter
        """
        try:
            # Get the chapter
            chapter = await self.get_chapter_by_number(chapter_num, background_tasks)
            
            # Return articles
            return chapter.get("articles", [])
            
        except Exception as e:
            self._handle_service_error(e, f"Error getting articles for chapter {chapter_num}")
    
    async def get_preamble(self, background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """
        Get the constitution preamble.
        
        Args:
            background_tasks: Optional background tasks for async caching
            
        Returns:
            Dict: Preamble data
        """
        try:
            cache_key = self._generate_cache_key("preamble")
            
            # Try to get from cache first
            cached_preamble = await self._cache_get(cache_key)
            if cached_preamble:
                return cached_preamble
            
            # Get constitution data
            data = await self.content_loader.get_constitution_data(background_tasks)
            
            # Extract preamble
            preamble_data = {
                "content": data.get("preamble", ""),
                "title": data.get("title", ""),
                "type": "preamble"
            }
            
            # Cache the preamble
            await self._cache_set(cache_key, preamble_data, 6 * HOUR, background_tasks)
            
            return preamble_data
            
        except Exception as e:
            self._handle_service_error(e, "Error getting preamble")
    
    async def get_content_by_path(self, path: str,
                                 background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """
        Get content by a path-like string (e.g., "chapter/1", "article/1.2").
        
        Args:
            path: Path string to identify content
            background_tasks: Optional background tasks for async caching
            
        Returns:
            Dict: Content data
            
        Raises:
            ValueError: If path format is invalid
        """
        try:
            # Parse path
            path_parts = path.strip("/").split("/")
            
            if len(path_parts) < 2:
                raise ValueError(f"Invalid path format: {path}")
            
            content_type = path_parts[0].lower()
            identifier = path_parts[1]
            
            if content_type == "chapter":
                chapter_num = int(identifier)
                return await self.get_chapter_by_number(chapter_num, background_tasks)
            
            elif content_type == "article":
                return await self.get_article_by_reference(identifier, background_tasks)
            
            elif content_type == "preamble":
                return await self.get_preamble(background_tasks)
            
            else:
                raise ValueError(f"Unknown content type: {content_type}")
                
        except ValueError:
            raise
        except Exception as e:
            self._handle_service_error(e, f"Error getting content by path {path}")
    
    async def get_content_tree(self, background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """
        Get the full content tree structure.
        
        Args:
            background_tasks: Optional background tasks for async caching
            
        Returns:
            Dict: Complete content tree
        """
        try:
            cache_key = self._generate_cache_key("content", "tree")
            
            # Try to get from cache first
            cached_tree = await self._cache_get(cache_key)
            if cached_tree:
                return cached_tree
            
            # Get constitution data
            data = await self.content_loader.get_constitution_data(background_tasks)
            
            # Build content tree
            tree = {
                "title": data.get("title", ""),
                "preamble": {
                    "content": data.get("preamble", ""),
                    "type": "preamble"
                },
                "chapters": []
            }
            
            for chapter in data.get("chapters", []):
                chapter_node = {
                    "chapter_number": chapter.get("chapter_number"),
                    "chapter_title": chapter.get("chapter_title"),
                    "articles": []
                }
                
                for article in chapter.get("articles", []):
                    article_node = {
                        "article_number": article.get("article_number"),
                        "article_title": article.get("article_title"),
                        "clause_count": len(article.get("clauses", []))
                    }
                    chapter_node["articles"].append(article_node)
                
                tree["chapters"].append(chapter_node)
            
            # Cache the tree
            await self._cache_set(cache_key, tree, 6 * HOUR, background_tasks)
            
            return tree
            
        except Exception as e:
            self._handle_service_error(e, "Error getting content tree")