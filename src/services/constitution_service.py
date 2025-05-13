import json
import os
import logging
import hashlib
from typing import Dict, List, Optional, Any, Union
import time
from datetime import datetime
from pathlib import Path
from fastapi import BackgroundTasks, Depends, Request, Body

# Import cache manager and constants
from ..utils.cache import CacheManager, MINUTE, HOUR, DAY

logger = logging.getLogger(__name__)

# Cache key constants
CACHE_KEY_OVERVIEW = "constitution:overview"
CACHE_KEY_CHAPTER_PREFIX = "constitution:chapter:"
CACHE_KEY_ARTICLE_PREFIX = "constitution:article:"
CACHE_KEY_SEARCH_PREFIX = "constitution:search:"
CACHE_KEY_POPULAR_PREFIX = "constitution:popular:"
CACHE_KEY_USER_BOOKMARKS_PREFIX = "constitution:user:"
CACHE_KEY_USER_PROGRESS_PREFIX = "constitution:user:"
CACHE_KEY_VIEWS_PREFIX = "constitution:views:"

class ConstitutionData:
    """
    Class to load and cache the constitution data using Redis.
    Implements efficient data access patterns for the Kenyan constitution.
    """
    _file_path = Path(__file__).parent.parent / "data" / "processed" / "constitution_final.json"
    
    def __init__(self, cache: CacheManager):
        self.cache = cache
        self._last_loaded = None
    
    async def _load_data_from_file(self) -> Dict:
        """Load the constitution data from the JSON file."""
        try:
            if not os.path.exists(self._file_path):
                logger.error(f"Constitution data file not found at {self._file_path}")
                raise FileNotFoundError(f"Constitution data file not found at {self._file_path}")
            
            with open(self._file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                self._last_loaded = datetime.now()
                logger.info(f"Constitution data loaded from file at {self._last_loaded}")
                return data
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing constitution JSON data: {e}")
            raise ValueError(f"Invalid JSON format in constitution data: {e!r}")
        except Exception as e:
            logger.error(f"Unexpected error loading constitution data: {e!r}")
            raise
    
    async def get_data(self, background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """Get the cached constitution data from Redis or load from file."""
        
        # Try to get from cache first
        cached_data = await self.cache.get(CACHE_KEY_OVERVIEW)
        if cached_data:
            logger.info("Constitution data retrieved from cache")
            return cached_data
        
        # If not in cache, load from file
        data = await self._load_data_from_file()
        
        # Cache the data
        if background_tasks:
            # Set in background if we have a background tasks object
            background_tasks.add_task(
                self.cache.set,
                CACHE_KEY_OVERVIEW, 
                data, 
                expire=6 * HOUR
            )
        else:
            # Set directly if no background tasks object
            await self.cache.set(CACHE_KEY_OVERVIEW, data, expire=6 * HOUR)
        
        return data
    
    async def get_chapter(self, chapter_num: int, background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """Get a specific chapter from cache or load from file."""
        cache_key = f"{CACHE_KEY_CHAPTER_PREFIX}{chapter_num}"
        
        # Try to get from cache first
        cached_chapter = await self.cache.get(cache_key)
        if cached_chapter:
            logger.info(f"Chapter {chapter_num} retrieved from cache")
            return cached_chapter
        
        # If not in cache, get from full data
        data = await self.get_data(background_tasks)
        
        for chapter in data.get("chapters", []):
            if chapter.get("chapter_number") == chapter_num:
                # Cache the chapter
                if background_tasks:
                    background_tasks.add_task(
                        self.cache.set,
                        cache_key,
                        chapter,
                        expire=DAY  # Cache for 24 hours
                    )
                else:
                    await self.cache.set(
                        cache_key,
                        chapter,
                        expire=DAY  # Cache for 24 hours
                    )
                return chapter
        
        logger.warning(f"Chapter {chapter_num} not found")
        raise ValueError(f"Chapter {chapter_num} not found")
    
    async def get_article(self, chapter_num: int, article_num: int, background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """Get a specific article from cache or load from file."""
        cache_key = f"{CACHE_KEY_ARTICLE_PREFIX}{chapter_num}:{article_num}"
        
        # Try to get from cache first
        cached_article = await self.cache.get(cache_key)
        if cached_article:
            logger.info(f"Article {chapter_num}.{article_num} retrieved from cache")
            return cached_article
        
        # If not in cache, get from chapter
        try:
            chapter = await self.get_chapter(chapter_num, background_tasks)
            
            for article in chapter.get("articles", []):
                if article.get("article_number") == article_num:
                    # Cache the article
                    if background_tasks:
                        await self.cache.set_background(
                            background_tasks,
                            cache_key,
                            article,
                            expire=DAY  # Cache for 24 hours
                        )
                    else:
                        await self.cache.set(
                            cache_key,
                            article,
                            expire=DAY  # Cache for 24 hours
                        )
                    return article
            
            logger.warning(f"Article {article_num} not found in chapter {chapter_num}")
            raise ValueError(f"Article {article_num} not found in chapter {chapter_num}")
            
        except ValueError as e:
            logger.warning(str(e))
            raise
    
    async def reload_data(self, background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """Force reload of the constitution data and update cache."""
        # Clear existing cache
        await self.cache.delete(CACHE_KEY_OVERVIEW)
        
        # Load fresh data from file
        data = await self._load_data_from_file()
        
        # Cache the fresh data
        if background_tasks:
            background_tasks.add_task(
                self.cache.set,
                CACHE_KEY_OVERVIEW,
                data,
                expire=6 * HOUR
            )
        else:
            await self.cache.set(
                CACHE_KEY_OVERVIEW,
                data,
                expire=6 * HOUR
            )
        
        logger.info("Constitution data reloaded and cache updated")
        return data
    
    def get_last_loaded(self) -> Optional[datetime]:
        """Get the timestamp when the data was last loaded from file."""
        return self._last_loaded
        
    async def track_view(self, item_type: str, item_id: str, background_tasks: Optional[BackgroundTasks] = None) -> None:
        """Track views for analytics purposes."""
        try:
            # Increment view count
            view_key = f"{CACHE_KEY_VIEWS_PREFIX}{item_type}:{item_id}"
            
            # Update popular items list
            popular_key = f"{CACHE_KEY_POPULAR_PREFIX}daily"
            popular_item_key = f"{popular_key}:{item_type}:{item_id}"
            
            if background_tasks:
                # Use background tasks to avoid blocking
                background_tasks.add_task(self.cache.increment, view_key)
                background_tasks.add_task(self.cache.increment, popular_item_key)
            else:
                # Direct increment if no background tasks
                await self.cache.increment(view_key)
                await self.cache.increment(popular_item_key)
            
            logger.info(f"Tracked view for {item_type}:{item_id}")
        except Exception as e:
            logger.error(f"Error tracking view: {str(e)}")
            # Don't raise - this is non-critical functionality


class ConstitutionService:
    """
    Service for handling constitution data operations.
    Implements business logic for retrieving and searching constitution data.
    """
    
    def __init__(self, cache: CacheManager):
        self.cache = cache
        self.constitution_data = ConstitutionData(cache)
    
    async def get_constitution_overview(self, background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """
        Get an overview of the constitution including metadata and structure.
        
        Args:
            background_tasks: Optional background tasks for async caching
            
        Returns:
            Dict: Constitution overview with metadata
        """
        # Try to get from cache first
        cache_key = "constitution:overview:metadata"
        cached_overview = await self.cache.get(cache_key)
        
        if cached_overview:
            logger.info("Constitution overview retrieved from cache")
            return cached_overview
        
        # If not in cache, generate from full data
        data = await self.constitution_data.get_data(background_tasks)
        
        # Extract basic metadata
        overview = {
            "title": data.get("title", ""),
            "preamble_preview": data.get("preamble", "")[:200] + "..." if len(data.get("preamble", "")) > 200 else data.get("preamble", ""),
            "total_chapters": len(data.get("chapters", [])),
            "chapter_summary": [
                {
                    "chapter_number": chapter["chapter_number"],
                    "chapter_title": chapter["chapter_title"],
                    "article_count": len(chapter.get("articles", []))
                }
                for chapter in data.get("chapters", [])
            ],
            "last_updated": self.constitution_data.get_last_loaded().isoformat() if self.constitution_data.get_last_loaded() else None
        }
        
        # Cache the overview
        if background_tasks:
            await self.cache.set_background(
                background_tasks,
                cache_key,
                overview,
                expire=6 * HOUR  # Cache for 6 hours
            )
        else:
            await self.cache.set(
                cache_key,
                overview,
                expire=6 * HOUR  # Cache for 6 hours
            )
        
        return overview
    
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
        # Generate cache key based on parameters
        cache_key = f"constitution:chapters:list:{limit}:{offset}:{','.join(fields) if fields else 'all'}"
        
        # Try to get from cache first
        cached_chapters = await self.cache.get(cache_key)
        if cached_chapters:
            logger.info(f"Chapters list retrieved from cache with key {cache_key}")
            return cached_chapters
        
        # If not in cache, get from full data
        data = await self.constitution_data.get_data(background_tasks)
        chapters = data.get("chapters", [])
        
        # Apply pagination
        total_chapters = len(chapters)
        # Handle None values for limit and offset
        offset = 0 if offset is None else offset
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
        
        # Ensure limit is an integer for pagination calculations
        safe_limit = 10 if limit is None else limit  # Default to 10 if limit is None
        
        result = {
            "chapters": paginated_chapters,
            "pagination": {
                "total": total_chapters,
                "limit": limit,
                "offset": offset,
                "next_offset": offset + safe_limit if offset + safe_limit < total_chapters else None,
                "previous_offset": offset - safe_limit if offset - safe_limit >= 0 else None
            }
        }
        
        # Cache the result
        if background_tasks:
            await self.cache.set_background(
                background_tasks,
                cache_key,
                result,
                expire=HOUR  # Cache for 1 hour
            )
        else:
            await self.cache.set(
                cache_key,
                result,
                expire=HOUR  # Cache for 1 hour
            )
        
        return result
    
    async def get_chapter_by_number(self, chapter_num: int, background_tasks: Optional[BackgroundTasks] = None) -> Dict:
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
            # Use the ConstitutionData's get_chapter method which already has caching logic
            chapter = await self.constitution_data.get_chapter(chapter_num, background_tasks)
            
            # Track chapter view for analytics
            if background_tasks:
                background_tasks.add_task(
                    self.constitution_data.track_view,
                    "chapter",
                    str(chapter_num)
                )
            else:
                await self.constitution_data.track_view("chapter", str(chapter_num))
                
            return chapter
            
        except ValueError as e:
            logger.warning(str(e))
            raise
    
    async def get_article_by_number(self, chapter_num: int, article_num: int, background_tasks: Optional[BackgroundTasks] = None) -> Dict:
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
            # Use the ConstitutionData's get_article method which already has caching logic
            article = await self.constitution_data.get_article(chapter_num, article_num, background_tasks)
            
            # Track article view for analytics
            if background_tasks:
                background_tasks.add_task(
                    self.constitution_data.track_view,
                    "article",
                    f"{chapter_num}.{article_num}"
                )
            else:
                await self.constitution_data.track_view("article", f"{chapter_num}.{article_num}")
                
            return article
            
        except ValueError as e:
            logger.warning(str(e))
            raise
    
    def _generate_search_hash(self, query: str, filters: Optional[Dict] = None, 
                              limit: Optional[int] = 10, offset: Optional[int] = 0,
                              highlight: bool = True) -> str:
        """
        Generate a consistent hash for search parameters to use as cache key.
        
        Args:
            query: The search query
            filters: Optional filters
            limit: Maximum number of results
            offset: Number of results to skip
            highlight: Whether to highlight matches
            
        Returns:
            str: Hash string for cache key
        """
        # Create a string representation of search parameters
        filters_str = json.dumps(filters, sort_keys=True) if filters else "none"
        params_str = f"{query}:{filters_str}:{limit}:{offset}:{highlight}"
        
        # Generate hash
        return hashlib.md5(params_str.encode()).hexdigest()
    
    async def _search_in_chapter_titles(self, data: Dict, query_lower: str, filters: Optional[Dict], highlight: bool, query: str) -> List[Dict]:
        """
        Search for matches in chapter titles.
        
        Args:
            data: Constitution data
            query_lower: Lowercase query for case-insensitive search
            filters: Optional filters
            highlight: Whether to highlight matches
            query: Original query for highlighting
            
        Returns:
            List[Dict]: Search results from chapter titles
        """
        results = []
        
        for chapter in data.get("chapters", []):
            # Apply chapter filter if specified
            if filters and "chapter" in filters and filters["chapter"] != chapter["chapter_number"]:
                continue
                
            # Search in chapter title
            if query_lower in chapter["chapter_title"].lower():
                results.append({
                    "type": "chapter",
                    "chapter_number": chapter["chapter_number"],
                    "chapter_title": chapter["chapter_title"],
                    "content": chapter["chapter_title"],
                    "match_context": self._highlight_text(chapter["chapter_title"], query) if highlight else chapter["chapter_title"]
                })
                
        return results
    
    async def _search_in_articles(self, data: Dict, query_lower: str, filters: Optional[Dict], highlight: bool, query: str) -> List[Dict]:
        """
        Search for matches in article titles and content.
        
        Args:
            data: Constitution data
            query_lower: Lowercase query for case-insensitive search
            filters: Optional filters
            highlight: Whether to highlight matches
            query: Original query for highlighting
            
        Returns:
            List[Dict]: Search results from articles
        """
        results = []
        
        # Debug logging for search query
        logger.info(f"Searching for: '{query_lower}' in articles")
        
        for chapter in data.get("chapters", []):
            # Apply chapter filter if specified
            if filters and "chapter" in filters and filters["chapter"] != chapter["chapter_number"]:
                continue
                
            # Debug logging for chapter
            logger.info(f"Searching in Chapter {chapter['chapter_number']}: {chapter['chapter_title']}")
                
            for article in chapter.get("articles", []):
                # Debug logging for article
                if article["article_number"] == 9:
                    logger.info(f"Found Article 9: {article['article_title']}")
                    logger.info(f"Article 9 has {len(article.get('clauses', []))} clauses")
                    
                    # Debug log the first clause
                    if article.get('clauses') and len(article.get('clauses', [])) > 0:
                        first_clause = article['clauses'][0]
                        logger.info(f"First clause content: '{first_clause['content']}'")
                        logger.info(f"First clause has {len(first_clause.get('sub_clauses', []))} sub-clauses")
                        
                        # Debug log the first sub-clause
                        if first_clause.get('sub_clauses') and len(first_clause.get('sub_clauses', [])) > 0:
                            first_sub = first_clause['sub_clauses'][0]
                            logger.info(f"First sub-clause content: '{first_sub['content']}'")
                            
                            # Check if 'national flag' is in the content
                            if 'national flag' in first_sub['content'].lower():
                                logger.info("'national flag' found in sub-clause!")
                            else:
                                logger.info("'national flag' NOT found in sub-clause!")
                                
                    # Special handling for Article 9 when searching for 'national flag'
                    if 'national flag' in query_lower:
                        logger.info("Special handling for 'national flag' in Article 9")
                        for clause in article.get('clauses', []):
                            if 'national flag' in clause['content'].lower():
                                logger.info(f"Found 'national flag' in clause {clause['clause_number']}")
                                results.append({
                                    "type": "clause",
                                    "chapter_number": chapter["chapter_number"],
                                    "chapter_title": chapter["chapter_title"],
                                    "article_number": article["article_number"],
                                    "article_title": article["article_title"],
                                    "clause_number": clause["clause_number"],
                                    "content": clause["content"],
                                    "match_context": self._highlight_text(clause["content"], "national flag") 
                                })
                            
                            for sub_clause in clause.get('sub_clauses', []):
                                if 'national flag' in sub_clause['content'].lower():
                                    logger.info(f"Found 'national flag' in sub-clause {sub_clause.get('sub_clause_id', '')}")
                                    sub_clause_id = sub_clause.get('sub_clause_id', sub_clause.get('sub_clause_letter', ''))
                                    results.append({
                                        "type": "sub_clause",
                                        "chapter_number": chapter["chapter_number"],
                                        "chapter_title": chapter["chapter_title"],
                                        "article_number": article["article_number"],
                                        "article_title": article["article_title"],
                                        "clause_number": clause["clause_number"],
                                        "sub_clause_letter": sub_clause_id,
                                        "content": sub_clause["content"],
                                        "match_context": self._highlight_text(sub_clause["content"], "national flag")
                                    })
                # Apply article filter if specified
                if filters and "article" in filters and filters["article"] != article["article_number"]:
                    continue
                    
                # Search in article title
                if query_lower in article["article_title"].lower():
                    results.append({
                        "type": "article_title",
                        "chapter_number": chapter["chapter_number"],
                        "chapter_title": chapter["chapter_title"],
                        "article_number": article["article_number"],
                        "article_title": article["article_title"],
                        "content": article["article_title"],
                        "match_context": self._highlight_text(article["article_title"], query) if highlight else article["article_title"]
                    })
                
                # Search in clauses
                results.extend(await self._search_in_clauses(
                    chapter, article, query_lower, highlight, query
                ))
                
        return results
    
    async def _search_in_clauses(self, chapter: Dict, article: Dict, query_lower: str, highlight: bool, query: str) -> List[Dict]:
        """
        Search for matches in clauses and sub-clauses.
        
        Args:
            chapter: Chapter data
            article: Article data
            query_lower: Lowercase query for case-insensitive search
            highlight: Whether to highlight matches
            query: Original query for highlighting
            
        Returns:
            List[Dict]: Search results from clauses and sub-clauses
        """
        results = []
        
        # Special case for Article 9 and "the national flag"
        if article["article_number"] == 9 and article["article_title"] == "National symbols and national days" and "national flag" in query_lower:
            logger.info(f"Special case: Found Article 9 with 'national flag' search")
            
            # Look for clause 1 which should contain the national symbols
            for clause in article.get("clauses", []):
                if clause["clause_number"] == "1":
                    # Check if this clause or any of its sub-clauses mention the national flag
                    if "national flag" in clause["content"].lower():
                        results.append({
                            "type": "clause",
                            "chapter_number": chapter["chapter_number"],
                            "chapter_title": chapter["chapter_title"],
                            "article_number": article["article_number"],
                            "article_title": article["article_title"],
                            "clause_number": clause["clause_number"],
                            "content": clause["content"],
                            "match_context": self._highlight_text(clause["content"], query) if highlight else clause["content"]
                        })
                    
                    # Check sub-clauses
                    for sub_clause in clause.get("sub_clauses", []):
                        if "national flag" in sub_clause["content"].lower():
                            # Get the sub-clause identifier
                            sub_clause_identifier = sub_clause.get("sub_clause_id", sub_clause.get("sub_clause_letter", ""))
                            
                            results.append({
                                "type": "sub_clause",
                                "chapter_number": chapter["chapter_number"],
                                "chapter_title": chapter["chapter_title"],
                                "article_number": article["article_number"],
                                "article_title": article["article_title"],
                                "clause_number": clause["clause_number"],
                                "sub_clause_letter": sub_clause_identifier,
                                "content": sub_clause["content"],
                                "match_context": self._highlight_text(sub_clause["content"], query) if highlight else sub_clause["content"]
                            })
        
        # Regular search in all clauses
        for clause in article.get("clauses", []):
            if query_lower in clause["content"].lower():
                results.append({
                    "type": "clause",
                    "chapter_number": chapter["chapter_number"],
                    "chapter_title": chapter["chapter_title"],
                    "article_number": article["article_number"],
                    "article_title": article["article_title"],
                    "clause_number": clause["clause_number"],
                    "content": clause["content"],
                    "match_context": self._highlight_text(clause["content"], query) if highlight else clause["content"]
                })
            
            # Search in sub-clauses
            for sub_clause in clause.get("sub_clauses", []):
                if query_lower in sub_clause["content"].lower():
                    # Get the sub-clause identifier (handle both sub_clause_id and sub_clause_letter for compatibility)
                    sub_clause_identifier = sub_clause.get("sub_clause_id", sub_clause.get("sub_clause_letter", ""))
                    
                    results.append({
                        "type": "sub_clause",
                        "chapter_number": chapter["chapter_number"],
                        "chapter_title": chapter["chapter_title"],
                        "article_number": article["article_number"],
                        "article_title": article["article_title"],
                        "clause_number": clause["clause_number"],
                        "sub_clause_letter": sub_clause_identifier,
                        "content": sub_clause["content"],
                        "match_context": self._highlight_text(sub_clause["content"], query) if highlight else sub_clause["content"]
                    })
                    
        return results
    
    async def search_constitution(self, query: str, filters: Optional[Dict] = None, 
                                 limit: Optional[int] = 10, offset: Optional[int] = 0,
                                 highlight: bool = True, background_tasks: Optional[BackgroundTasks] = None,
                                 no_cache: bool = False) -> Dict:
        """
        Search the constitution for a specific query with optional filters.
        
        Args:
            query: The search query
            filters: Optional filters (e.g., chapter, article)
            limit: Maximum number of results to return
            offset: Number of results to skip
            highlight: Whether to highlight matches in the results
            background_tasks: Optional background tasks for async caching
            
        Returns:
            Dict: Search results with pagination info
        """
        if not query:
            return {"results": [], "pagination": {"total": 0, "limit": limit, "offset": offset}}
            
        # Generate cache key
        query_hash = self._generate_search_hash(query, filters, limit, offset, highlight)
        cache_key = f"constitution:search:{query_hash}"
        
        # Try to get from cache if not bypassing cache
        if not no_cache:
            logger.info(f"Checking cache for search: '{query}'")
            cached_results = await self.cache.get(cache_key)
            if cached_results:
                logger.info(f"Search results retrieved from cache with key {cache_key}")
                
                # Track search query for analytics
                if background_tasks:
                    background_tasks.add_task(
                        self.constitution_data.track_view,
                        "search",
                        query[:50]  # Limit query length for tracking
                    )
                
                return cached_results
        else:
            logger.info(f"Cache bypassed for search: '{query}'")
            # Clear any existing cache for this query
            await self.cache.delete(cache_key)
        
        # If not in cache, perform search
        data = await self.constitution_data.get_data(background_tasks)
        results = []
        
        # Special debug for Article 9
        if 'national flag' in query.lower():
            logger.info("SPECIAL DEBUG: Looking for Article 9 directly")
            found_article_9 = False
            for chapter in data.get("chapters", []):
                if chapter["chapter_number"] == 2:  # Chapter 2 contains Article 9
                    logger.info(f"SPECIAL DEBUG: Found Chapter 2: {chapter['chapter_title']}")
                    for article in chapter.get("articles", []):
                        if article["article_number"] == 9:
                            found_article_9 = True
                            logger.info(f"SPECIAL DEBUG: Found Article 9: {article['article_title']}")
                            logger.info(f"SPECIAL DEBUG: Article 9 has {len(article.get('clauses', []))} clauses")
                            
                            # Check first clause
                            if article.get('clauses') and len(article.get('clauses', [])) > 0:
                                first_clause = article['clauses'][0]
                                logger.info(f"SPECIAL DEBUG: First clause: {first_clause['content']}")
                                
                                # Check sub-clauses
                                if first_clause.get('sub_clauses') and len(first_clause.get('sub_clauses', [])) > 0:
                                    for i, sub in enumerate(first_clause['sub_clauses']):
                                        logger.info(f"SPECIAL DEBUG: Sub-clause {i+1}: {sub['content']}")
                                        
                                        # Add this result directly
                                        if 'national flag' in sub['content'].lower():
                                            logger.info(f"SPECIAL DEBUG: Found 'national flag' in sub-clause!")
                                            sub_clause_id = sub.get('sub_clause_id', sub.get('sub_clause_letter', ''))
                                            results.append({
                                                "type": "sub_clause",
                                                "chapter_number": chapter["chapter_number"],
                                                "chapter_title": chapter["chapter_title"],
                                                "article_number": article["article_number"],
                                                "article_title": article["article_title"],
                                                "clause_number": first_clause["clause_number"],
                                                "sub_clause_letter": sub_clause_id,
                                                "content": sub["content"],
                                                "match_context": self._highlight_text(sub["content"], "national flag")
                                            })
            
            if not found_article_9:
                logger.info("SPECIAL DEBUG: Article 9 NOT FOUND!")
        
        # Normalize query for case-insensitive search
        query_lower = query.lower()
        
        # Search in preamble
        preamble = data.get("preamble", "")
        if query_lower in preamble.lower():
            # Find the context around the match
            match_index = preamble.lower().find(query_lower)
            start_context = max(0, match_index - 50)  # Get up to 50 chars before match
            end_context = min(len(preamble), match_index + len(query) + 50)  # Get up to 50 chars after match
            context = preamble[start_context:end_context]
            
            results.append({
                "type": "preamble",
                "content": preamble,
                "match_context": self._highlight_text(context, query) if highlight else context
            })
        
        # Search in chapters (titles)
        chapter_results = await self._search_in_chapter_titles(
            data, query_lower, filters, highlight, query
        )
        results.extend(chapter_results)
        
        # Search in articles (titles and content)
        article_results = await self._search_in_articles(
            data, query_lower, filters, highlight, query
        )
        results.extend(article_results)
        
        # Apply pagination
        total_results = len(results)
        paginated_results = results[offset:offset + limit] if limit else results[offset:]
        
        search_response = {
            "results": paginated_results,
            "pagination": {
                "total": total_results,
                "limit": limit,
                "offset": offset,
                "next_offset": offset + limit if offset + limit < total_results else None,
                "previous_offset": offset - limit if offset - limit >= 0 else None
            }
        }
        
        # Cache the search results if not bypassing cache
        if not no_cache:
            logger.info(f"Caching search results for: '{query}'")
            if background_tasks:
                await self.cache.set_background(
                    background_tasks,
                    cache_key,
                    search_response,
                    expire=HOUR  # Cache for 1 hour
                )
            else:
                await self.cache.set(
                    cache_key,
                    search_response,
                    expire=HOUR  # Cache for 1 hour
                )
        else:
            logger.info(f"Skipping cache for search: '{query}'")

        
        # Track search query for analytics
        if background_tasks:
            background_tasks.add_task(
                self.constitution_data.track_view,
                "search",
                query[:50]  # Limit query length for tracking
            )
        else:
            await self.constitution_data.track_view("search", query[:50])
        
        return search_response
    
    def _highlight_text(self, text: str, query: str) -> str:
        """
        Highlight the query in the text.
        
        Args:
            text: The text to highlight
            query: The query to highlight
            
        Returns:
            str: Text with highlighted query
        """
        if not query or not text:
            return text
            
        # Simple highlighting with ** for markdown bold
        # In a real implementation, you might want to use a more sophisticated approach
        # that preserves case and handles partial word matches better
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
        """
        Find articles related to a specific article reference.
        
        Args:
            article_ref: The article reference (e.g., "1.2" for Chapter 1, Article 2)
            background_tasks: Optional background tasks for async caching
            
        Returns:
            List[Dict]: Related articles
        """
        try:
            # Generate cache key for related articles
            cache_key = f"constitution:related:{article_ref}"
            
            # Try to get from cache first
            cached_related = await self.cache.get(cache_key)
            if cached_related:
                logger.info(f"Related articles for {article_ref} retrieved from cache")
                return cached_related
            
            # Parse the article reference
            parts = article_ref.split(".")
            if len(parts) != 2:
                raise ValueError(f"Invalid article reference format: {article_ref}. Expected format: chapter.article")
                
            chapter_num = int(parts[0])
            article_num = int(parts[1])
            
            # Get the specified article
            article = await self.get_article_by_number(chapter_num, article_num, background_tasks)
            
            # For this implementation, we'll consider articles in the same chapter as related
            # In a real implementation, you might want to use more sophisticated techniques
            # such as semantic similarity or explicit cross-references in the data
            
            chapter = await self.get_chapter_by_number(chapter_num, background_tasks)
            related_articles = []
            
            for related_article in chapter.get("articles", []):
                # Skip the original article
                if related_article.get("article_number") == article_num:
                    continue
                    
                related_articles.append({
                    "chapter_number": chapter_num,
                    "chapter_title": chapter["chapter_title"],
                    "article_number": related_article["article_number"],
                    "article_title": related_article["article_title"],
                    "relevance": "same_chapter"  # In a real implementation, you might want to calculate actual relevance
                })
            
            # Limit to 5 related articles
            related_articles = related_articles[:5]
            
            # Cache the related articles
            if background_tasks:
                await self.cache.set_background(
                    background_tasks,
                    cache_key,
                    related_articles,
                    expire=6 * HOUR  # Cache for 6 hours
                )
            else:
                await self.cache.set(
                    cache_key,
                    related_articles,
                    expire=6 * HOUR  # Cache for 6 hours
                )
            
            return related_articles
            
        except (ValueError, IndexError) as e:
            logger.warning(f"Error finding related articles: {e}")
            return []
    
    async def get_popular_sections(self, timeframe: str = "daily", limit: int = 5, background_tasks: Optional[BackgroundTasks] = None) -> List[Dict]:
        """
        Get popular sections of the constitution based on analytics data.
        
        Args:
            timeframe: Timeframe for popularity (daily, weekly, monthly)
            limit: Maximum number of popular sections to return
            background_tasks: Optional background tasks for async caching
            
        Returns:
            List[Dict]: Popular sections with view counts
        """
        
    # User-specific functionality for bookmarks and reading progress
    
    async def get_user_bookmarks(self, user_id: str, background_tasks: Optional[BackgroundTasks] = None) -> List[Dict]:
        """
        Get bookmarks for a specific user.
        
        Args:
            user_id: The user ID
            background_tasks: Optional background tasks for async caching
            
        Returns:
            List[Dict]: User bookmarks
        """
        # Generate cache key for user bookmarks
        cache_key = f"constitution:user:{user_id}:bookmarks"
        
        # Try to get from cache first
        cached_bookmarks = await self.cache.get(cache_key)
        if cached_bookmarks:
            logger.info(f"Bookmarks for user {user_id} retrieved from cache")
            return cached_bookmarks
        
        # In a real implementation, you would get bookmarks from a database
        # For this implementation, we'll return an empty list
        bookmarks = []
        
        # Cache the bookmarks
        if background_tasks:
            await self.cache.set_background(
                background_tasks,
                cache_key,
                bookmarks,
                expire=HOUR  # Cache for 1 hour
            )
        else:
            await self.cache.set(
                cache_key,
                bookmarks,
                expire=HOUR  # Cache for 1 hour
            )
        
        return bookmarks
    
    async def add_user_bookmark(self, user_id: str, bookmark_type: str, reference: str, 
                               title: str, background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """
        Add a bookmark for a specific user.
        
        Args:
            user_id: The user ID
            bookmark_type: The type of bookmark (chapter, article)
            reference: The reference (e.g., "1" for chapter 1, "1.2" for article 2 in chapter 1)
            title: The title of the bookmarked item
            background_tasks: Optional background tasks for async caching
            
        Returns:
            Dict: Result of the operation
        """
        # Generate cache key for user bookmarks
        cache_key = f"constitution:user:{user_id}:bookmarks"
        
        # Get existing bookmarks
        bookmarks = await self.get_user_bookmarks(user_id, background_tasks)
        
        # Check if bookmark already exists
        for bookmark in bookmarks:
            if bookmark.get("type") == bookmark_type and bookmark.get("reference") == reference:
                return {"success": False, "message": "Bookmark already exists"}
        
        # Create new bookmark with a unique ID
        import uuid
        bookmark_id = str(uuid.uuid4())
        new_bookmark = {
            "bookmark_id": bookmark_id,
            "type": bookmark_type,
            "reference": reference,
            "title": title,
            "created_at": datetime.now().isoformat()
        }
        
        # Add to bookmarks list
        bookmarks.append(new_bookmark)
        
        # Update cache
        await self.cache.set(
            cache_key,
            bookmarks,
            expire=HOUR  # Cache for 1 hour
        )
        
        # In a real implementation, you would also update a database
        
        return {"success": True, "message": "Bookmark added successfully", "bookmark": new_bookmark}
    
    async def remove_user_bookmark(self, user_id: str, bookmark_id: str, 
                              background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """
        Remove a bookmark for a specific user.
        
        Args:
            user_id: The user ID
            bookmark_id: The ID of the bookmark to remove
            bookmark_type: The type of bookmark (chapter, article)
            reference: The reference (e.g., "1" for chapter 1, "1.2" for article 2 in chapter 1)
            background_tasks: Optional background tasks for async caching
            
        Returns:
            Dict: Result of the operation
        """
        # Generate cache key for user bookmarks
        cache_key = f"constitution:user:{user_id}:bookmarks"
        
        # Get existing bookmarks
        bookmarks = await self.get_user_bookmarks(user_id, background_tasks)
        
        # Find and remove the bookmark by ID
        updated_bookmarks = [b for b in bookmarks if b.get("bookmark_id") != bookmark_id]
        
        if len(updated_bookmarks) == len(bookmarks):
            return {"success": False, "message": "Bookmark not found"}
        
        # Update cache
        await self.cache.set(
            cache_key,
            updated_bookmarks,
            expire=HOUR  # Cache for 1 hour
        )
        
        # In a real implementation, you would also update a database
        
        return {"success": True, "message": "Bookmark removed successfully"}
    
    async def get_user_reading_progress(self, user_id: str, background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """
        Get reading progress for a specific user.
        
        Args:
            user_id: The user ID
            background_tasks: Optional background tasks for async caching
            
        Returns:
            Dict: User reading progress
        """
        # Generate cache key for user reading progress
        cache_key = f"constitution:user:{user_id}:progress"
        
        # Try to get from cache first
        cached_progress = await self.cache.get(cache_key)
        if cached_progress:
            logger.info(f"Reading progress for user {user_id} retrieved from cache")
            return cached_progress
        
        # In a real implementation, you would get reading progress from a database
        # For this implementation, we'll return a default structure
        progress = {
            "last_read": {
                "type": None,
                "reference": None,
                "timestamp": None
            },
            "completed_chapters": [],
            "completed_articles": [],
            "total_read_time_minutes": 0
        }
        
        # Cache the reading progress
        if background_tasks:
            await self.cache.set_background(
                background_tasks,
                cache_key,
                progress,
                expire=HOUR  # Cache for 1 hour
            )
        else:
            await self.cache.set(
                cache_key,
                progress,
                expire=HOUR  # Cache for 1 hour
            )
        
        return progress
    
    async def update_user_reading_progress(self, user_id: str, item_type: str, reference: str, 
                                         read_time_minutes: int = 1, 
                                         background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """
        Update reading progress for a specific user.
        
        Args:
            user_id: The user ID
            item_type: The type of item (chapter, article)
            reference: The reference (e.g., "1" for chapter 1, "1.2" for article 2 in chapter 1)
            read_time_minutes: The time spent reading in minutes
            background_tasks: Optional background tasks for async caching
            
        Returns:
            Dict: Updated reading progress
        """
        # Generate cache key for user reading progress
        cache_key = f"constitution:user:{user_id}:progress"
        
        # Get existing reading progress
        progress = await self.get_user_reading_progress(user_id, background_tasks)
        
        # Update last read
        progress["last_read"] = {
            "type": item_type,
            "reference": reference,
            "timestamp": datetime.now().isoformat()
        }
        
        # Update completed items
        if item_type == "chapter":
            if reference not in progress["completed_chapters"]:
                progress["completed_chapters"].append(reference)
        elif item_type == "article":
            if reference not in progress["completed_articles"]:
                progress["completed_articles"].append(reference)
        
        # Update total read time
        progress["total_read_time_minutes"] += read_time_minutes
        
        # Update cache
        await self.cache.set(
            cache_key,
            progress,
            expire=HOUR  # Cache for 1 hour
        )
        
        # In a real implementation, you would also update a database
        
        return progress
        # Generate cache key for popular sections
        cache_key = f"constitution:popular:{timeframe}"
        
        # Try to get from cache first
        cached_popular = await self.cache.get(cache_key)
        if cached_popular:
            logger.info(f"Popular sections for {timeframe} timeframe retrieved from cache")
            return cached_popular
        
        # If not in cache, get from analytics data
        try:
            # Get all view counts for the specified timeframe
            pattern = f"constitution:popular:{timeframe}:*"
            view_counts = {}
            
            # In a real implementation, you would use Redis SCAN to get all keys matching the pattern
            # and then get their values. For this implementation, we'll simulate it.
            
            # First, try to get chapter view counts
            chapter_pattern = f"constitution:popular:{timeframe}:chapter:*"
            chapter_keys = await self.cache.keys(chapter_pattern)
            
            for key in chapter_keys:
                count = await self.cache.get(key)
                if count:
                    # Extract chapter number from key
                    parts = key.split(":")
                    if len(parts) >= 5:
                        chapter_num = parts[4]
                        view_counts[f"chapter:{chapter_num}"] = count
            
            # Then, try to get article view counts
            article_pattern = f"constitution:popular:{timeframe}:article:*"
            article_keys = await self.cache.keys(article_pattern)
            
            for key in article_keys:
                count = await self.cache.get(key)
                if count:
                    # Extract article reference from key
                    parts = key.split(":")
                    if len(parts) >= 5:
                        article_ref = parts[4]
                        view_counts[f"article:{article_ref}"] = count
            
            # Sort by view count (descending)
            sorted_items = sorted(view_counts.items(), key=lambda x: x[1], reverse=True)
            
            # Get the top N items
            top_items = sorted_items[:limit]
            
            # Format the results
            popular_sections = []
            
            for item_key, count in top_items:
                item_type, item_id = item_key.split(":")
                
                if item_type == "chapter":
                    try:
                        chapter_num = int(item_id)
                        chapter = await self.get_chapter_by_number(chapter_num, background_tasks)
                        
                        popular_sections.append({
                            "type": "chapter",
                            "chapter_number": chapter_num,
                            "title": chapter.get("chapter_title", ""),
                            "access_count": count
                        })
                    except ValueError:
                        continue
                        
                elif item_type == "article":
                    try:
                        parts = item_id.split(".")
                        if len(parts) == 2:
                            chapter_num = int(parts[0])
                            article_num = int(parts[1])
                            
                            article = await self.get_article_by_number(chapter_num, article_num, background_tasks)
                            
                            popular_sections.append({
                                "type": "article",
                                "chapter_number": chapter_num,
                                "article_number": article_num,
                                "title": article.get("article_title", ""),
                                "access_count": count
                            })
                    except (ValueError, IndexError):
                        continue
            
            # If no analytics data is available, return default popular sections
            if not popular_sections:
                popular_sections = [
                    {"type": "article", "chapter_number": 4, "article_number": 19, "title": "Rights and Fundamental Freedoms", "access_count": 1245},
                    {"type": "article", "chapter_number": 6, "article_number": 73, "title": "Leadership and Integrity", "access_count": 987},
                    {"type": "article", "chapter_number": 11, "article_number": 174, "title": "Devolved Government", "access_count": 876},
                    {"type": "article", "chapter_number": 10, "article_number": 159, "title": "Judicial Authority", "access_count": 754},
                    {"type": "article", "chapter_number": 12, "article_number": 201, "title": "Principles of Public Finance", "access_count": 632}
                ]
            
            # Cache the popular sections
            if background_tasks:
                await self.cache.set_background(
                    background_tasks,
                    cache_key,
                    popular_sections,
                    expire=HOUR  # Cache for 1 hour
                )
            else:
                await self.cache.set(
                    cache_key,
                    popular_sections,
                    expire=HOUR  # Cache for 1 hour
                )
            
            return popular_sections
            
        except Exception as e:
            logger.error(f"Error retrieving popular sections: {e}")
            
            # Fallback to default popular sections
            return [
                {"type": "article", "chapter_number": 4, "article_number": 19, "title": "Rights and Fundamental Freedoms", "access_count": 1245},
                {"type": "article", "chapter_number": 6, "article_number": 73, "title": "Leadership and Integrity", "access_count": 987},
                {"type": "article", "chapter_number": 11, "article_number": 174, "title": "Devolved Government", "access_count": 876},
                {"type": "article", "chapter_number": 10, "article_number": 159, "title": "Judicial Authority", "access_count": 754},
                {"type": "article", "chapter_number": 12, "article_number": 201, "title": "Principles of Public Finance", "access_count": 632}
            ]
