"""
Search engine for constitution content.
Handles search operations, result ranking, and search optimization.
"""

from typing import Dict, List, Optional, Tuple
from fastapi import BackgroundTasks

from ..base import BaseService, ConstitutionCacheManager
from ....utils.cache import HOUR
from ..content.content_loader import ContentLoader
from .query_processor import QueryProcessor
from .result_highlighter import ResultHighlighter


class SearchEngine(BaseService):
    """
    Main search engine for constitution content.
    Handles search operations, result ranking, and caching.
    """
    
    def __init__(self, cache_manager: ConstitutionCacheManager,
                 content_loader: ContentLoader,
                 query_processor: QueryProcessor,
                 result_highlighter: ResultHighlighter):
        """
        Initialize the search engine.
        
        Args:
            cache_manager: Cache manager instance
            content_loader: Content loader instance
            query_processor: Query processor instance
            result_highlighter: Result highlighter instance
        """
        super().__init__(cache_manager)
        self.content_loader = content_loader
        self.query_processor = query_processor
        self.result_highlighter = result_highlighter
    
    def get_service_name(self) -> str:
        """Get the service name."""
        return "search_engine"
    
    async def search_constitution(self, query: str, filters: Optional[Dict] = None,
                                 limit: Optional[int] = 10, offset: Optional[int] = 0,
                                 highlight: bool = True,
                                 background_tasks: Optional[BackgroundTasks] = None,
                                 no_cache: bool = False) -> Dict:
        """
        Search the constitution for a specific query.
        
        Args:
            query: Search query
            filters: Optional filters
            limit: Maximum number of results
            offset: Number of results to skip
            highlight: Whether to highlight matches
            background_tasks: Optional background tasks
            no_cache: Whether to bypass cache
            
        Returns:
            Dict: Search results with pagination info
        """
        try:
            # Validate and process query
            if not query:
                return self._empty_search_result(limit, offset)
            
            normalized_query = self.query_processor.normalize_query(query)
            processed_filters = self.query_processor.parse_filters(filters)
            
            # Generate cache key
            query_hash = self.query_processor.generate_search_hash(
                normalized_query, processed_filters, limit, offset, highlight
            )
            cache_key = f"constitution:search:{query_hash}"
            
            # Check cache if not bypassing
            if not no_cache:
                cached_results = await self._cache_get(cache_key)
                if cached_results:
                    return cached_results
            
            # Perform search
            search_results = await self._perform_search(
                normalized_query, processed_filters, query
            )
            
            # Rank results
            ranked_results = self._rank_results(search_results, normalized_query)
            
            # Apply pagination
            total_results = len(ranked_results)
            paginated_results = ranked_results[offset:offset + limit] if limit else ranked_results[offset:]
            
            # Highlight results if requested
            if highlight:
                paginated_results = self.result_highlighter.highlight_search_results(
                    paginated_results, query
                )
            
            # Build response
            search_response = {
                "query": query,
                "normalized_query": normalized_query,
                "filters": processed_filters,
                "results": paginated_results,
                "pagination": {
                    "total": total_results,
                    "limit": limit,
                    "offset": offset,
                    "has_next": offset + (limit or 10) < total_results,
                    "has_previous": offset > 0,
                    "next_offset": offset + (limit or 10) if offset + (limit or 10) < total_results else None,
                    "previous_offset": offset - (limit or 10) if offset - (limit or 10) >= 0 else None
                },
                "query_info": {
                    "query_type": self.query_processor.identify_query_type(query),
                    "suggestions": self.query_processor.suggest_query_corrections(query),
                    "complexity": self.query_processor.analyze_query_complexity(query)
                }
            }
            
            # Cache results if not bypassing
            if not no_cache:
                await self._cache_set(cache_key, search_response, HOUR, background_tasks)
            
            return search_response
            
        except Exception as e:
            self._handle_service_error(e, f"Error searching constitution with query: {query}")
    
    def _empty_search_result(self, limit: Optional[int], offset: Optional[int]) -> Dict:
        """
        Return empty search results.
        
        Args:
            limit: Results limit
            offset: Results offset
            
        Returns:
            Dict: Empty search results
        """
        return {
            "query": "",
            "normalized_query": "",
            "filters": None,
            "results": [],
            "pagination": {
                "total": 0,
                "limit": limit,
                "offset": offset,
                "has_next": False,
                "has_previous": False,
                "next_offset": None,
                "previous_offset": None
            },
            "query_info": {
                "query_type": "empty",
                "suggestions": [],
                "complexity": {"complexity_score": 0}
            }
        }
    
    async def _perform_search(self, query: str, filters: Optional[Dict], 
                            original_query: str) -> List[Dict]:
        """
        Perform the actual search operation.
        
        Args:
            query: Normalized query
            filters: Processed filters
            original_query: Original query for highlighting
            
        Returns:
            List[Dict]: Search results
        """
        try:
            # Get constitution data
            data = await self.content_loader.get_constitution_data()
            results = []
            
            # Search in preamble
            preamble_results = await self._search_in_preamble(data, query, original_query)
            results.extend(preamble_results)
            
            # Search in chapters
            chapter_results = await self._search_in_chapters(data, query, filters, original_query)
            results.extend(chapter_results)
            
            # Search in parts
            part_results = await self._search_in_parts(data, query, filters, original_query)
            results.extend(part_results)
            
            # Search in articles
            article_results = await self._search_in_articles(data, query, filters, original_query)
            results.extend(article_results)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error performing search: {str(e)}")
            return []
    
    async def _search_in_preamble(self, data: Dict, query: str, original_query: str) -> List[Dict]:
        """
        Search in the constitution preamble.
        
        Args:
            data: Constitution data
            query: Search query
            original_query: Original query
            
        Returns:
            List[Dict]: Preamble search results
        """
        try:
            results = []
            preamble = data.get("preamble", "")
            
            if query.lower() in preamble.lower():
                result = {
                    "type": "preamble",
                    "content": preamble,
                    "match_context": self.result_highlighter.extract_context(preamble, original_query),
                    "relevance_score": self._calculate_relevance_score(preamble, query, "preamble")
                }
                results.append(result)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error searching in preamble: {str(e)}")
            return []
    
    async def _search_in_chapters(self, data: Dict, query: str, filters: Optional[Dict], 
                                original_query: str) -> List[Dict]:
        """
        Search in chapter titles.
        
        Args:
            data: Constitution data
            query: Search query
            filters: Search filters
            original_query: Original query
            
        Returns:
            List[Dict]: Chapter search results
        """
        try:
            results = []
            
            for chapter in data.get("chapters", []):
                # Apply chapter filter
                if filters and "chapter" in filters and filters["chapter"] != chapter["chapter_number"]:
                    continue
                
                chapter_title = chapter.get("chapter_title", "")
                if query.lower() in chapter_title.lower():
                    result = {
                        "type": "chapter",
                        "chapter_number": chapter["chapter_number"],
                        "chapter_title": chapter_title,
                        "content": chapter_title,
                        "match_context": self.result_highlighter.highlight_text(chapter_title, original_query),
                        "relevance_score": self._calculate_relevance_score(chapter_title, query, "chapter")
                    }
                    results.append(result)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error searching in chapters: {str(e)}")
            return []
    
    async def _search_in_parts(self, data: Dict, query: str, filters: Optional[Dict], 
                              original_query: str) -> List[Dict]:
        """
        Search in part titles within chapters.
        
        Args:
            data: Constitution data
            query: Search query
            filters: Search filters
            original_query: Original query
            
        Returns:
            List[Dict]: Part search results
        """
        try:
            results = []
            
            for chapter in data.get("chapters", []):
                # Apply chapter filter
                if filters and "chapter" in filters and filters["chapter"] != chapter["chapter_number"]:
                    continue
                
                # Search in parts if they exist
                for part in chapter.get("parts", []):
                    part_title = part.get("part_title", "")
                    if query.lower() in part_title.lower():
                        result = {
                            "type": "part",
                            "chapter_number": chapter["chapter_number"],
                            "chapter_title": chapter["chapter_title"],
                            "part_number": part["part_number"],
                            "part_title": part_title,
                            "content": part_title,
                            "match_context": self.result_highlighter.highlight_text(part_title, original_query),
                            "relevance_score": self._calculate_relevance_score(part_title, query, "part")
                        }
                        results.append(result)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error searching in parts: {str(e)}")
            return []
    
    async def _search_in_articles(self, data: Dict, query: str, filters: Optional[Dict], 
                                original_query: str) -> List[Dict]:
        """
        Search in articles, clauses, and sub-clauses.
        
        Args:
            data: Constitution data
            query: Search query
            filters: Search filters
            original_query: Original query
            
        Returns:
            List[Dict]: Article search results
        """
        try:
            results = []
            
            for chapter in data.get("chapters", []):
                # Apply chapter filter
                if filters and "chapter" in filters and filters["chapter"] != chapter["chapter_number"]:
                    continue
                
                # Search in direct articles (chapters without parts)
                for article in chapter.get("articles", []):
                    # Apply article filter
                    if filters and "article" in filters and filters["article"] != article["article_number"]:
                        continue
                    
                    # Search in article title
                    article_title = article.get("article_title", "")
                    if query.lower() in article_title.lower():
                        result = {
                            "type": "article_title",
                            "chapter_number": chapter["chapter_number"],
                            "chapter_title": chapter["chapter_title"],
                            "article_number": article["article_number"],
                            "article_title": article_title,
                            "content": article_title,
                            "match_context": self.result_highlighter.highlight_text(article_title, original_query),
                            "relevance_score": self._calculate_relevance_score(article_title, query, "article_title")
                        }
                        results.append(result)
                    
                    # Search in clauses
                    clause_results = await self._search_in_clauses(
                        chapter, article, query, original_query
                    )
                    results.extend(clause_results)
                
                # Search in articles within parts (chapters with parts structure)
                for part in chapter.get("parts", []):
                    for article in part.get("articles", []):
                        # Apply article filter
                        if filters and "article" in filters and filters["article"] != article["article_number"]:
                            continue
                        
                        # Search in article title
                        article_title = article.get("article_title", "")
                        if query.lower() in article_title.lower():
                            result = {
                                "type": "article_title",
                                "chapter_number": chapter["chapter_number"],
                                "chapter_title": chapter["chapter_title"],
                                "part_number": part["part_number"],
                                "part_title": part["part_title"],
                                "article_number": article["article_number"],
                                "article_title": article_title,
                                "content": article_title,
                                "match_context": self.result_highlighter.highlight_text(article_title, original_query),
                                "relevance_score": self._calculate_relevance_score(article_title, query, "article_title")
                            }
                            results.append(result)
                        
                        # Search in clauses
                        clause_results = await self._search_in_clauses(
                            chapter, article, query, original_query, part
                        )
                        results.extend(clause_results)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error searching in articles: {str(e)}")
            return []
    
    async def _search_in_clauses(self, chapter: Dict, article: Dict, query: str, 
                               original_query: str, part: Optional[Dict] = None) -> List[Dict]:
        """
        Search in clauses and sub-clauses.
        
        Args:
            chapter: Chapter data
            article: Article data
            query: Search query
            original_query: Original query
            part: Optional part data
            
        Returns:
            List[Dict]: Clause search results
        """
        try:
            results = []
            
            for clause in article.get("clauses", []):
                clause_content = clause.get("content", "")
                
                # Search in clause content
                if query.lower() in clause_content.lower():
                    result = {
                        "type": "clause",
                        "chapter_number": chapter["chapter_number"],
                        "chapter_title": chapter["chapter_title"],
                        "article_number": article["article_number"],
                        "article_title": article["article_title"],
                        "clause_number": clause["clause_number"],
                        "content": clause_content,
                        "match_context": self.result_highlighter.extract_context(clause_content, original_query),
                        "relevance_score": self._calculate_relevance_score(clause_content, query, "clause")
                    }
                    
                    # Add part information if available
                    if part:
                        result["part_number"] = part["part_number"]
                        result["part_title"] = part["part_title"]
                    
                    results.append(result)
                
                # Search in sub-clauses
                for sub_clause in clause.get("sub_clauses", []):
                    sub_clause_content = sub_clause.get("content", "")
                    
                    if query.lower() in sub_clause_content.lower():
                        sub_clause_id = sub_clause.get("sub_clause_id", sub_clause.get("sub_clause_letter", ""))
                        
                        result = {
                            "type": "sub_clause",
                            "chapter_number": chapter["chapter_number"],
                            "chapter_title": chapter["chapter_title"],
                            "article_number": article["article_number"],
                            "article_title": article["article_title"],
                            "clause_number": clause["clause_number"],
                            "sub_clause_letter": sub_clause_id,
                            "content": sub_clause_content,
                            "match_context": self.result_highlighter.extract_context(sub_clause_content, original_query),
                            "relevance_score": self._calculate_relevance_score(sub_clause_content, query, "sub_clause")
                        }
                        
                        # Add part information if available
                        if part:
                            result["part_number"] = part["part_number"]
                            result["part_title"] = part["part_title"]
                        
                        results.append(result)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error searching in clauses: {str(e)}")
            return []
    
    def _calculate_relevance_score(self, content: str, query: str, content_type: str) -> float:
        """
        Calculate relevance score for a search result.
        
        Args:
            content: Content text
            query: Search query
            content_type: Type of content
            
        Returns:
            float: Relevance score (0-1)
        """
        try:
            if not content or not query:
                return 0.0
            
            score = 0.0
            content_lower = content.lower()
            query_lower = query.lower()
            
            # Exact match bonus
            if query_lower in content_lower:
                score += 0.5
            
            # Word match scoring
            query_terms = query.split()
            content_words = content_lower.split()
            
            matched_terms = 0
            for term in query_terms:
                if term.lower() in content_words:
                    matched_terms += 1
            
            if query_terms:
                score += (matched_terms / len(query_terms)) * 0.3
            
            # Content type scoring
            type_weights = {
                "preamble": 0.8,
                "chapter": 0.9,
                "part": 0.85,
                "article_title": 0.95,
                "clause": 0.7,
                "sub_clause": 0.6
            }
            
            score *= type_weights.get(content_type, 0.5)
            
            # Length penalty for very long content
            if len(content) > 1000:
                score *= 0.9
            
            return min(1.0, score)
            
        except Exception as e:
            self.logger.error(f"Error calculating relevance score: {str(e)}")
            return 0.0
    
    def _rank_results(self, results: List[Dict], query: str) -> List[Dict]:
        """
        Rank search results by relevance.
        
        Args:
            results: Search results
            query: Search query
            
        Returns:
            List[Dict]: Ranked results
        """
        try:
            # Sort by relevance score (descending) and then by type priority
            type_priority = {
                "article_title": 1,
                "chapter": 2,
                "part": 3,
                "preamble": 4,
                "clause": 5,
                "sub_clause": 6
            }
            
            def sort_key(result):
                relevance_score = result.get("relevance_score", 0)
                type_priority_score = type_priority.get(result.get("type", ""), 10)
                return (-relevance_score, type_priority_score)
            
            return sorted(results, key=sort_key)
            
        except Exception as e:
            self.logger.error(f"Error ranking results: {str(e)}")
            return results
    
    async def search_suggestions(self, query: str, limit: int = 5) -> List[str]:
        """
        Get search suggestions based on query.
        
        Args:
            query: Partial query
            limit: Maximum number of suggestions
            
        Returns:
            List[str]: Search suggestions
        """
        try:
            suggestions = []
            
            # Get query corrections
            corrections = self.query_processor.suggest_query_corrections(query)
            suggestions.extend(corrections)
            
            # Add common search terms
            if len(query) >= 2:
                common_terms = [
                    "fundamental rights",
                    "bill of rights",
                    "national assembly",
                    "president",
                    "supreme court",
                    "devolution",
                    "county government",
                    "citizenship",
                    "elections",
                    "parliament"
                ]
                
                query_lower = query.lower()
                for term in common_terms:
                    if query_lower in term.lower() and term not in suggestions:
                        suggestions.append(term)
            
            return suggestions[:limit]
            
        except Exception as e:
            self.logger.error(f"Error getting search suggestions: {str(e)}")
            return []
    
    async def get_search_statistics(self) -> Dict:
        """
        Get search engine statistics.
        
        Returns:
            Dict: Search statistics
        """
        try:
            # This would typically query analytics data
            # For now, return basic statistics
            return {
                "total_searches": 0,  # Would be populated from analytics
                "popular_queries": [],  # Would be populated from analytics
                "average_results_per_query": 0,
                "cache_hit_rate": 0.0
            }
            
        except Exception as e:
            self.logger.error(f"Error getting search statistics: {str(e)}")
            return {}