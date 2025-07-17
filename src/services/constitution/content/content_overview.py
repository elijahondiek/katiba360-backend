"""
Content overview service for constitution data.
Handles generation of overviews, summaries, and metadata.
"""

from typing import Dict, List, Optional
from datetime import datetime
from fastapi import BackgroundTasks

from ..base import BaseService, ConstitutionCacheManager
from ....utils.cache import HOUR
from .content_loader import ContentLoader


class ContentOverview(BaseService):
    """
    Service for generating constitution content overviews and summaries.
    Handles metadata extraction, overview generation, and summary creation.
    """
    
    def __init__(self, cache_manager: ConstitutionCacheManager, 
                 content_loader: ContentLoader):
        """
        Initialize the content overview service.
        
        Args:
            cache_manager: Cache manager instance
            content_loader: Content loader instance
        """
        super().__init__(cache_manager)
        self.content_loader = content_loader
    
    def get_service_name(self) -> str:
        """Get the service name."""
        return "content_overview"
    
    async def get_constitution_overview(self, background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """
        Get a comprehensive overview of the constitution.
        
        Args:
            background_tasks: Optional background tasks for async caching
            
        Returns:
            Dict: Constitution overview with metadata
        """
        try:
            cache_key = self._generate_cache_key("overview", "metadata")
            
            # Try to get from cache first
            cached_overview = await self._cache_get(cache_key)
            if cached_overview:
                return cached_overview
            
            # Get constitution data
            data = await self.content_loader.get_constitution_data(background_tasks)
            
            # Generate overview
            overview = {
                "title": data.get("title", ""),
                "preamble_preview": self._generate_preamble_preview(data.get("preamble", "")),
                "total_chapters": len(data.get("chapters", [])),
                "structure": await self._generate_structure_overview(data),
                "statistics": await self._generate_statistics(data),
                "metadata": {
                    "last_updated": self.content_loader.get_last_loaded_time().isoformat() 
                                  if self.content_loader.get_last_loaded_time() else None,
                    "data_source": str(self.content_loader.get_file_path()),
                    "generated_at": datetime.now().isoformat()
                }
            }
            
            # Cache the overview
            await self._cache_set(cache_key, overview, 6 * HOUR, background_tasks)
            
            return overview
            
        except Exception as e:
            self._handle_service_error(e, "Error getting constitution overview")
    
    def _generate_preamble_preview(self, preamble: str, max_length: int = 200) -> str:
        """
        Generate a preview of the preamble.
        
        Args:
            preamble: Full preamble text
            max_length: Maximum length of preview
            
        Returns:
            str: Preamble preview
        """
        if not preamble:
            return ""
        
        if len(preamble) <= max_length:
            return preamble
        
        # Find the last complete sentence within the limit
        preview = preamble[:max_length]
        last_sentence_end = max(
            preview.rfind('.'),
            preview.rfind('!'),
            preview.rfind('?')
        )
        
        if last_sentence_end > 0:
            preview = preview[:last_sentence_end + 1]
        else:
            preview = preview.rstrip() + "..."
        
        return preview
    
    async def _generate_structure_overview(self, data: Dict) -> Dict:
        """
        Generate structural overview of the constitution.
        
        Args:
            data: Constitution data
            
        Returns:
            Dict: Structure overview
        """
        chapters = data.get("chapters", [])
        
        structure = {
            "chapters": [],
            "total_articles": 0,
            "total_clauses": 0,
            "total_sub_clauses": 0
        }
        
        for chapter in chapters:
            articles = chapter.get("articles", [])
            chapter_clauses = 0
            chapter_sub_clauses = 0
            
            # Count clauses and sub-clauses in this chapter
            for article in articles:
                clauses = article.get("clauses", [])
                chapter_clauses += len(clauses)
                
                for clause in clauses:
                    sub_clauses = clause.get("sub_clauses", [])
                    chapter_sub_clauses += len(sub_clauses)
            
            chapter_info = {
                "chapter_number": chapter.get("chapter_number"),
                "chapter_title": chapter.get("chapter_title"),
                "article_count": len(articles),
                "clause_count": chapter_clauses,
                "sub_clause_count": chapter_sub_clauses,
                "articles": [
                    {
                        "article_number": article.get("article_number"),
                        "article_title": article.get("article_title"),
                        "clause_count": len(article.get("clauses", []))
                    }
                    for article in articles
                ]
            }
            
            structure["chapters"].append(chapter_info)
            structure["total_articles"] += len(articles)
            structure["total_clauses"] += chapter_clauses
            structure["total_sub_clauses"] += chapter_sub_clauses
        
        return structure
    
    async def _generate_statistics(self, data: Dict) -> Dict:
        """
        Generate statistics about the constitution content.
        
        Args:
            data: Constitution data
            
        Returns:
            Dict: Content statistics
        """
        statistics = {
            "content_length": {
                "preamble_chars": len(data.get("preamble", "")),
                "total_text_chars": 0,
                "average_article_length": 0
            },
            "structure": {
                "chapters": len(data.get("chapters", [])),
                "articles": 0,
                "clauses": 0,
                "sub_clauses": 0
            },
            "distribution": {
                "articles_per_chapter": {},
                "clauses_per_article": {},
                "largest_chapter": None,
                "smallest_chapter": None
            }
        }
        
        chapters = data.get("chapters", [])
        total_text_length = len(data.get("preamble", ""))
        article_lengths = []
        chapter_sizes = []
        
        for chapter in chapters:
            articles = chapter.get("articles", [])
            chapter_article_count = len(articles)
            chapter_text_length = 0
            
            for article in articles:
                # Calculate article text length
                article_text = article.get("article_title", "")
                clauses = article.get("clauses", [])
                
                for clause in clauses:
                    article_text += clause.get("content", "")
                    statistics["structure"]["clauses"] += 1
                    
                    for sub_clause in clause.get("sub_clauses", []):
                        article_text += sub_clause.get("content", "")
                        statistics["structure"]["sub_clauses"] += 1
                
                article_lengths.append(len(article_text))
                chapter_text_length += len(article_text)
            
            statistics["structure"]["articles"] += chapter_article_count
            total_text_length += chapter_text_length
            chapter_sizes.append({
                "chapter_number": chapter.get("chapter_number"),
                "chapter_title": chapter.get("chapter_title"),
                "article_count": chapter_article_count,
                "text_length": chapter_text_length
            })
            
            # Track articles per chapter
            statistics["distribution"]["articles_per_chapter"][str(chapter.get("chapter_number"))] = chapter_article_count
        
        # Calculate averages and extremes
        statistics["content_length"]["total_text_chars"] = total_text_length
        statistics["content_length"]["average_article_length"] = (
            sum(article_lengths) / len(article_lengths) if article_lengths else 0
        )
        
        # Find largest and smallest chapters
        if chapter_sizes:
            largest_chapter = max(chapter_sizes, key=lambda x: x["article_count"])
            smallest_chapter = min(chapter_sizes, key=lambda x: x["article_count"])
            
            statistics["distribution"]["largest_chapter"] = {
                "chapter_number": largest_chapter["chapter_number"],
                "chapter_title": largest_chapter["chapter_title"],
                "article_count": largest_chapter["article_count"]
            }
            
            statistics["distribution"]["smallest_chapter"] = {
                "chapter_number": smallest_chapter["chapter_number"],
                "chapter_title": smallest_chapter["chapter_title"],
                "article_count": smallest_chapter["article_count"]
            }
        
        return statistics
    
    async def get_chapter_overview(self, chapter_num: int, 
                                  background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """
        Get an overview of a specific chapter.
        
        Args:
            chapter_num: Chapter number
            background_tasks: Optional background tasks for async caching
            
        Returns:
            Dict: Chapter overview
        """
        try:
            # Validate chapter number
            chapter_num = self.validator.validate_chapter_number(chapter_num)
            
            cache_key = self._generate_cache_key("chapter", chapter_num, "overview")
            
            # Try to get from cache first
            cached_overview = await self._cache_get(cache_key)
            if cached_overview:
                return cached_overview
            
            # Get constitution data
            data = await self.content_loader.get_constitution_data(background_tasks)
            
            # Find the chapter
            chapter = None
            for ch in data.get("chapters", []):
                if ch.get("chapter_number") == chapter_num:
                    chapter = ch
                    break
            
            if not chapter:
                raise ValueError(f"Chapter {chapter_num} not found")
            
            # Generate chapter overview
            articles = chapter.get("articles", [])
            overview = {
                "chapter_number": chapter.get("chapter_number"),
                "chapter_title": chapter.get("chapter_title"),
                "total_articles": len(articles),
                "articles": [
                    {
                        "article_number": article.get("article_number"),
                        "article_title": article.get("article_title"),
                        "clause_count": len(article.get("clauses", [])),
                        "preview": self._generate_article_preview(article)
                    }
                    for article in articles
                ],
                "statistics": {
                    "total_clauses": sum(len(article.get("clauses", [])) for article in articles),
                    "total_sub_clauses": sum(
                        len(clause.get("sub_clauses", [])) 
                        for article in articles 
                        for clause in article.get("clauses", [])
                    ),
                    "average_clauses_per_article": (
                        sum(len(article.get("clauses", [])) for article in articles) / len(articles)
                        if articles else 0
                    )
                }
            }
            
            # Cache the overview
            await self._cache_set(cache_key, overview, 6 * HOUR, background_tasks)
            
            return overview
            
        except ValueError:
            raise
        except Exception as e:
            self._handle_service_error(e, f"Error getting chapter {chapter_num} overview")
    
    def _generate_article_preview(self, article: Dict, max_length: int = 150) -> str:
        """
        Generate a preview of an article.
        
        Args:
            article: Article data
            max_length: Maximum length of preview
            
        Returns:
            str: Article preview
        """
        # Start with article title
        preview = article.get("article_title", "")
        
        # Add content from first clause if available
        clauses = article.get("clauses", [])
        if clauses:
            first_clause = clauses[0]
            clause_content = first_clause.get("content", "")
            
            if clause_content:
                if preview:
                    preview += " - " + clause_content
                else:
                    preview = clause_content
        
        # Truncate if too long
        if len(preview) > max_length:
            preview = preview[:max_length].rstrip() + "..."
        
        return preview
    
    async def get_content_summary(self, background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """
        Get a comprehensive summary of the constitution content.
        
        Args:
            background_tasks: Optional background tasks for async caching
            
        Returns:
            Dict: Content summary
        """
        try:
            cache_key = self._generate_cache_key("content", "summary")
            
            # Try to get from cache first
            cached_summary = await self._cache_get(cache_key)
            if cached_summary:
                return cached_summary
            
            # Get constitution data
            data = await self.content_loader.get_constitution_data(background_tasks)
            
            # Generate summary
            summary = {
                "title": data.get("title", ""),
                "overview": await self.get_constitution_overview(background_tasks),
                "chapter_summaries": [],
                "key_themes": await self._extract_key_themes(data),
                "generated_at": datetime.now().isoformat()
            }
            
            # Generate chapter summaries
            for chapter in data.get("chapters", []):
                chapter_summary = {
                    "chapter_number": chapter.get("chapter_number"),
                    "chapter_title": chapter.get("chapter_title"),
                    "article_count": len(chapter.get("articles", [])),
                    "key_articles": [
                        {
                            "article_number": article.get("article_number"),
                            "article_title": article.get("article_title")
                        }
                        for article in chapter.get("articles", [])[:3]  # First 3 articles
                    ]
                }
                summary["chapter_summaries"].append(chapter_summary)
            
            # Cache the summary
            await self._cache_set(cache_key, summary, 6 * HOUR, background_tasks)
            
            return summary
            
        except Exception as e:
            self._handle_service_error(e, "Error getting content summary")
    
    async def _extract_key_themes(self, data: Dict) -> List[Dict]:
        """
        Extract key themes from the constitution.
        
        Args:
            data: Constitution data
            
        Returns:
            List[Dict]: Key themes
        """
        # This is a simplified implementation
        # In a real application, you might use NLP techniques
        
        themes = [
            {
                "theme": "Rights and Freedoms",
                "description": "Fundamental rights and freedoms of citizens",
                "related_chapters": [4, 5]
            },
            {
                "theme": "Governance Structure",
                "description": "Structure and organization of government",
                "related_chapters": [8, 9, 10]
            },
            {
                "theme": "Devolution",
                "description": "Devolved government and county governance",
                "related_chapters": [11]
            },
            {
                "theme": "Public Finance",
                "description": "Management of public finances",
                "related_chapters": [12]
            },
            {
                "theme": "Land and Environment",
                "description": "Land tenure and environmental conservation",
                "related_chapters": [5]
            }
        ]
        
        return themes
    
    async def get_navigation_structure(self, background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """
        Get a navigation-friendly structure of the constitution.
        
        Args:
            background_tasks: Optional background tasks for async caching
            
        Returns:
            Dict: Navigation structure
        """
        try:
            cache_key = self._generate_cache_key("navigation", "structure")
            
            # Try to get from cache first
            cached_structure = await self._cache_get(cache_key)
            if cached_structure:
                return cached_structure
            
            # Get constitution data
            data = await self.content_loader.get_constitution_data(background_tasks)
            
            # Build navigation structure
            structure = {
                "preamble": {
                    "title": "Preamble",
                    "path": "/preamble",
                    "type": "preamble"
                },
                "chapters": []
            }
            
            for chapter in data.get("chapters", []):
                chapter_node = {
                    "chapter_number": chapter.get("chapter_number"),
                    "chapter_title": chapter.get("chapter_title"),
                    "path": f"/chapter/{chapter.get('chapter_number')}",
                    "type": "chapter",
                    "articles": []
                }
                
                for article in chapter.get("articles", []):
                    article_node = {
                        "article_number": article.get("article_number"),
                        "article_title": article.get("article_title"),
                        "path": f"/article/{chapter.get('chapter_number')}.{article.get('article_number')}",
                        "type": "article",
                        "reference": f"{chapter.get('chapter_number')}.{article.get('article_number')}"
                    }
                    chapter_node["articles"].append(article_node)
                
                structure["chapters"].append(chapter_node)
            
            # Cache the structure
            await self._cache_set(cache_key, structure, 6 * HOUR, background_tasks)
            
            return structure
            
        except Exception as e:
            self._handle_service_error(e, "Error getting navigation structure")