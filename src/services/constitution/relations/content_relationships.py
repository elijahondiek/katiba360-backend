"""
Content relationships service for constitution content.
Handles analysis and mapping of relationships between constitution content.
"""

from typing import Dict, List, Optional, Set, Tuple
from fastapi import BackgroundTasks
import re

from ..base import BaseService, ConstitutionCacheManager
from ....utils.cache import HOUR, DAY
from ..content.content_loader import ContentLoader
from ..content.content_retrieval import ContentRetrieval


class ContentRelationships(BaseService):
    """
    Service for analyzing and managing content relationships.
    Handles relationship discovery, mapping, and caching.
    """
    
    def __init__(self, cache_manager: ConstitutionCacheManager,
                 content_loader: ContentLoader,
                 content_retrieval: ContentRetrieval):
        """
        Initialize the content relationships service.
        
        Args:
            cache_manager: Cache manager instance
            content_loader: Content loader service
            content_retrieval: Content retrieval service
        """
        super().__init__(cache_manager)
        self.content_loader = content_loader
        self.content_retrieval = content_retrieval
    
    def get_service_name(self) -> str:
        """Get the service name."""
        return "content_relationships"
    
    async def get_related_articles(self, article_ref: str,
                                 background_tasks: Optional[BackgroundTasks] = None) -> List[Dict]:
        """
        Get articles related to a specific article.
        
        Args:
            article_ref: Article reference (e.g., "1.2")
            background_tasks: Optional background tasks
            
        Returns:
            List[Dict]: Related articles
        """
        try:
            # Validate article reference
            chapter_num, article_num = self.validator.validate_article_reference(article_ref)
            
            cache_key = self._generate_cache_key("related_articles", article_ref)
            
            # Check cache first
            cached_related = await self._cache_get(cache_key)
            if cached_related:
                return cached_related
            
            # Get the article
            article = await self.content_retrieval.get_article_by_number(
                chapter_num, article_num, background_tasks
            )
            
            # Find related articles
            related_articles = await self._find_related_articles(article, chapter_num, article_num)
            
            # Cache the results
            await self._cache_set(cache_key, related_articles, 6 * HOUR, background_tasks)
            
            return related_articles
            
        except Exception as e:
            self._handle_service_error(e, f"Error getting related articles for {article_ref}")
    
    async def _find_related_articles(self, article: Dict, chapter_num: int, article_num: int) -> List[Dict]:
        """
        Find articles related to the given article.
        
        Args:
            article: Article data
            chapter_num: Chapter number
            article_num: Article number
            
        Returns:
            List[Dict]: Related articles
        """
        try:
            related_articles = []
            
            # Get all constitution data
            constitution_data = await self.content_loader.get_constitution_data()
            
            # Find relationships using multiple strategies
            
            # Strategy 1: Articles in the same chapter
            same_chapter_articles = await self._find_same_chapter_articles(
                constitution_data, chapter_num, article_num
            )
            related_articles.extend(same_chapter_articles)
            
            # Strategy 2: Articles with similar themes
            theme_related_articles = await self._find_theme_related_articles(
                constitution_data, article, chapter_num, article_num
            )
            related_articles.extend(theme_related_articles)
            
            # Strategy 3: Articles with cross-references
            cross_ref_articles = await self._find_cross_referenced_articles(
                constitution_data, article, chapter_num, article_num
            )
            related_articles.extend(cross_ref_articles)
            
            # Strategy 4: Articles with keyword overlap
            keyword_related_articles = await self._find_keyword_related_articles(
                constitution_data, article, chapter_num, article_num
            )
            related_articles.extend(keyword_related_articles)
            
            # Remove duplicates and sort by relevance
            unique_articles = self._deduplicate_and_rank(related_articles)
            
            return unique_articles[:10]  # Return top 10 related articles
            
        except Exception as e:
            self.logger.error(f"Error finding related articles: {str(e)}")
            return []
    
    async def _find_same_chapter_articles(self, constitution_data: Dict, chapter_num: int, article_num: int) -> List[Dict]:
        """
        Find articles in the same chapter.
        
        Args:
            constitution_data: Constitution data
            chapter_num: Chapter number
            article_num: Article number
            
        Returns:
            List[Dict]: Same chapter articles
        """
        try:
            related_articles = []
            
            # Find the chapter
            for chapter in constitution_data.get("chapters", []):
                if chapter.get("chapter_number") == chapter_num:
                    # Get other articles in the same chapter
                    for article in chapter.get("articles", []):
                        if article.get("article_number") != article_num:
                            related_articles.append({
                                "chapter_number": chapter_num,
                                "chapter_title": chapter["chapter_title"],
                                "article_number": article["article_number"],
                                "article_title": article["article_title"],
                                "relevance": "same_chapter",
                                "relevance_score": 0.8
                            })
                    break
            
            return related_articles
            
        except Exception as e:
            self.logger.error(f"Error finding same chapter articles: {str(e)}")
            return []
    
    async def _find_theme_related_articles(self, constitution_data: Dict, article: Dict, 
                                         chapter_num: int, article_num: int) -> List[Dict]:
        """
        Find articles with similar themes.
        
        Args:
            constitution_data: Constitution data
            article: Current article
            chapter_num: Chapter number
            article_num: Article number
            
        Returns:
            List[Dict]: Theme-related articles
        """
        try:
            related_articles = []
            
            # Extract themes from the current article
            article_themes = self._extract_themes(article)
            
            if not article_themes:
                return related_articles
            
            # Search for articles with similar themes
            for chapter in constitution_data.get("chapters", []):
                for other_article in chapter.get("articles", []):
                    # Skip the current article
                    if (chapter.get("chapter_number") == chapter_num and 
                        other_article.get("article_number") == article_num):
                        continue
                    
                    # Extract themes from the other article
                    other_themes = self._extract_themes(other_article)
                    
                    # Calculate theme similarity
                    similarity = self._calculate_theme_similarity(article_themes, other_themes)
                    
                    if similarity > 0.3:  # Threshold for theme similarity
                        related_articles.append({
                            "chapter_number": chapter["chapter_number"],
                            "chapter_title": chapter["chapter_title"],
                            "article_number": other_article["article_number"],
                            "article_title": other_article["article_title"],
                            "relevance": "theme_similarity",
                            "relevance_score": similarity
                        })
            
            return related_articles
            
        except Exception as e:
            self.logger.error(f"Error finding theme related articles: {str(e)}")
            return []
    
    def _extract_themes(self, article: Dict) -> Set[str]:
        """
        Extract themes from an article.
        
        Args:
            article: Article data
            
        Returns:
            Set[str]: Article themes
        """
        try:
            themes = set()
            
            # Define theme keywords
            theme_keywords = {
                "rights": ["rights", "freedom", "liberty", "protection", "dignity"],
                "governance": ["government", "administration", "executive", "legislative", "judicial"],
                "citizenship": ["citizen", "citizenship", "nationality", "naturalization"],
                "elections": ["election", "vote", "ballot", "constituency", "representative"],
                "devolution": ["county", "devolution", "devolved", "local government"],
                "public_finance": ["finance", "budget", "taxation", "revenue", "expenditure"],
                "land": ["land", "property", "ownership", "acquisition", "compensation"],
                "environment": ["environment", "natural resources", "conservation", "sustainability"],
                "security": ["security", "defense", "armed forces", "police", "safety"],
                "justice": ["justice", "court", "judge", "trial", "legal", "law"],
                "parliament": ["parliament", "assembly", "senate", "legislation", "bill"],
                "constitution": ["constitution", "constitutional", "amendment", "interpretation"]
            }
            
            # Extract text content from article
            text_content = ""
            text_content += article.get("article_title", "").lower()
            
            # Add clause content
            for clause in article.get("clauses", []):
                text_content += " " + clause.get("content", "").lower()
                
                # Add sub-clause content
                for sub_clause in clause.get("sub_clauses", []):
                    text_content += " " + sub_clause.get("content", "").lower()
            
            # Match themes
            for theme, keywords in theme_keywords.items():
                for keyword in keywords:
                    if keyword in text_content:
                        themes.add(theme)
                        break
            
            return themes
            
        except Exception as e:
            self.logger.error(f"Error extracting themes: {str(e)}")
            return set()
    
    def _calculate_theme_similarity(self, themes1: Set[str], themes2: Set[str]) -> float:
        """
        Calculate similarity between two sets of themes.
        
        Args:
            themes1: First set of themes
            themes2: Second set of themes
            
        Returns:
            float: Similarity score (0-1)
        """
        try:
            if not themes1 or not themes2:
                return 0.0
            
            # Calculate Jaccard similarity
            intersection = len(themes1.intersection(themes2))
            union = len(themes1.union(themes2))
            
            return intersection / union if union > 0 else 0.0
            
        except Exception as e:
            self.logger.error(f"Error calculating theme similarity: {str(e)}")
            return 0.0
    
    async def _find_cross_referenced_articles(self, constitution_data: Dict, article: Dict, 
                                            chapter_num: int, article_num: int) -> List[Dict]:
        """
        Find articles that are cross-referenced.
        
        Args:
            constitution_data: Constitution data
            article: Current article
            chapter_num: Chapter number
            article_num: Article number
            
        Returns:
            List[Dict]: Cross-referenced articles
        """
        try:
            related_articles = []
            
            # Extract cross-references from the current article
            cross_refs = self._extract_cross_references(article)
            
            if not cross_refs:
                return related_articles
            
            # Find articles that match the cross-references
            for ref in cross_refs:
                try:
                    if "." in ref:
                        # Full article reference (e.g., "1.2")
                        ref_chapter, ref_article = map(int, ref.split("."))
                    else:
                        # Chapter reference only
                        ref_chapter = int(ref)
                        ref_article = None
                    
                    # Find the referenced content
                    for chapter in constitution_data.get("chapters", []):
                        if chapter.get("chapter_number") == ref_chapter:
                            if ref_article is None:
                                # Reference to entire chapter - add first few articles
                                for i, other_article in enumerate(chapter.get("articles", [])[:3]):
                                    related_articles.append({
                                        "chapter_number": ref_chapter,
                                        "chapter_title": chapter["chapter_title"],
                                        "article_number": other_article["article_number"],
                                        "article_title": other_article["article_title"],
                                        "relevance": "cross_reference",
                                        "relevance_score": 0.9
                                    })
                            else:
                                # Reference to specific article
                                for other_article in chapter.get("articles", []):
                                    if other_article.get("article_number") == ref_article:
                                        related_articles.append({
                                            "chapter_number": ref_chapter,
                                            "chapter_title": chapter["chapter_title"],
                                            "article_number": ref_article,
                                            "article_title": other_article["article_title"],
                                            "relevance": "cross_reference",
                                            "relevance_score": 0.95
                                        })
                                        break
                            break
                except ValueError:
                    continue
            
            return related_articles
            
        except Exception as e:
            self.logger.error(f"Error finding cross-referenced articles: {str(e)}")
            return []
    
    def _extract_cross_references(self, article: Dict) -> List[str]:
        """
        Extract cross-references from an article.
        
        Args:
            article: Article data
            
        Returns:
            List[str]: Cross-references
        """
        try:
            cross_refs = []
            
            # Extract text content
            text_content = article.get("article_title", "")
            
            for clause in article.get("clauses", []):
                text_content += " " + clause.get("content", "")
                
                for sub_clause in clause.get("sub_clauses", []):
                    text_content += " " + sub_clause.get("content", "")
            
            # Patterns to match references
            patterns = [
                r'Article\s+(\d+)',
                r'article\s+(\d+)',
                r'Chapter\s+(\d+)',
                r'chapter\s+(\d+)',
                r'section\s+(\d+)',
                r'Section\s+(\d+)',
                r'(\d+)\s*\.\s*(\d+)',  # Pattern for "1.2" style references
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, text_content, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        # For patterns that capture multiple groups
                        cross_refs.append(".".join(match))
                    else:
                        # For patterns that capture single groups
                        cross_refs.append(match)
            
            return list(set(cross_refs))  # Remove duplicates
            
        except Exception as e:
            self.logger.error(f"Error extracting cross-references: {str(e)}")
            return []
    
    async def _find_keyword_related_articles(self, constitution_data: Dict, article: Dict, 
                                           chapter_num: int, article_num: int) -> List[Dict]:
        """
        Find articles with keyword overlap.
        
        Args:
            constitution_data: Constitution data
            article: Current article
            chapter_num: Chapter number
            article_num: Article number
            
        Returns:
            List[Dict]: Keyword-related articles
        """
        try:
            related_articles = []
            
            # Extract keywords from the current article
            article_keywords = self._extract_keywords(article)
            
            if not article_keywords:
                return related_articles
            
            # Search for articles with similar keywords
            for chapter in constitution_data.get("chapters", []):
                for other_article in chapter.get("articles", []):
                    # Skip the current article
                    if (chapter.get("chapter_number") == chapter_num and 
                        other_article.get("article_number") == article_num):
                        continue
                    
                    # Extract keywords from the other article
                    other_keywords = self._extract_keywords(other_article)
                    
                    # Calculate keyword similarity
                    similarity = self._calculate_keyword_similarity(article_keywords, other_keywords)
                    
                    if similarity > 0.2:  # Threshold for keyword similarity
                        related_articles.append({
                            "chapter_number": chapter["chapter_number"],
                            "chapter_title": chapter["chapter_title"],
                            "article_number": other_article["article_number"],
                            "article_title": other_article["article_title"],
                            "relevance": "keyword_similarity",
                            "relevance_score": similarity
                        })
            
            return related_articles
            
        except Exception as e:
            self.logger.error(f"Error finding keyword related articles: {str(e)}")
            return []
    
    def _extract_keywords(self, article: Dict) -> Set[str]:
        """
        Extract keywords from an article.
        
        Args:
            article: Article data
            
        Returns:
            Set[str]: Article keywords
        """
        try:
            keywords = set()
            
            # Extract text content
            text_content = ""
            text_content += article.get("article_title", "").lower()
            
            for clause in article.get("clauses", []):
                text_content += " " + clause.get("content", "").lower()
                
                for sub_clause in clause.get("sub_clauses", []):
                    text_content += " " + sub_clause.get("content", "").lower()
            
            # Extract meaningful keywords (simple approach)
            # Remove common stop words
            stop_words = {
                "the", "and", "or", "in", "on", "at", "to", "for", "of", "with", "by",
                "a", "an", "is", "are", "was", "were", "be", "been", "being", "have",
                "has", "had", "do", "does", "did", "will", "would", "could", "should",
                "may", "might", "must", "shall", "can", "this", "that", "these", "those"
            }
            
            # Split into words and filter
            words = re.findall(r'\b[a-z]+\b', text_content)
            for word in words:
                if len(word) > 3 and word not in stop_words:
                    keywords.add(word)
            
            return keywords
            
        except Exception as e:
            self.logger.error(f"Error extracting keywords: {str(e)}")
            return set()
    
    def _calculate_keyword_similarity(self, keywords1: Set[str], keywords2: Set[str]) -> float:
        """
        Calculate similarity between two sets of keywords.
        
        Args:
            keywords1: First set of keywords
            keywords2: Second set of keywords
            
        Returns:
            float: Similarity score (0-1)
        """
        try:
            if not keywords1 or not keywords2:
                return 0.0
            
            # Calculate Jaccard similarity
            intersection = len(keywords1.intersection(keywords2))
            union = len(keywords1.union(keywords2))
            
            return intersection / union if union > 0 else 0.0
            
        except Exception as e:
            self.logger.error(f"Error calculating keyword similarity: {str(e)}")
            return 0.0
    
    def _deduplicate_and_rank(self, articles: List[Dict]) -> List[Dict]:
        """
        Remove duplicates and rank articles by relevance.
        
        Args:
            articles: List of related articles
            
        Returns:
            List[Dict]: Deduplicated and ranked articles
        """
        try:
            # Remove duplicates based on article reference
            seen = set()
            unique_articles = []
            
            for article in articles:
                article_ref = f"{article['chapter_number']}.{article['article_number']}"
                if article_ref not in seen:
                    seen.add(article_ref)
                    unique_articles.append(article)
            
            # Sort by relevance score (descending)
            unique_articles.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
            
            return unique_articles
            
        except Exception as e:
            self.logger.error(f"Error deduplicating and ranking articles: {str(e)}")
            return articles
    
    async def get_content_network(self, background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """
        Get the content relationship network.
        
        Args:
            background_tasks: Optional background tasks
            
        Returns:
            Dict: Content relationship network
        """
        try:
            cache_key = self._generate_cache_key("content_network")
            
            # Check cache first
            cached_network = await self._cache_get(cache_key)
            if cached_network:
                return cached_network
            
            # Build the network
            network = await self._build_content_network()
            
            # Cache the network
            await self._cache_set(cache_key, network, DAY, background_tasks)
            
            return network
            
        except Exception as e:
            self._handle_service_error(e, "Error getting content network")
    
    async def _build_content_network(self) -> Dict:
        """
        Build the content relationship network.
        
        Returns:
            Dict: Content network
        """
        try:
            # Get all constitution data
            constitution_data = await self.content_loader.get_constitution_data()
            
            network = {
                "nodes": [],
                "edges": [],
                "statistics": {
                    "total_articles": 0,
                    "total_relationships": 0,
                    "average_connections": 0
                }
            }
            
            # Create nodes for all articles
            for chapter in constitution_data.get("chapters", []):
                for article in chapter.get("articles", []):
                    network["nodes"].append({
                        "id": f"{chapter['chapter_number']}.{article['article_number']}",
                        "chapter_number": chapter["chapter_number"],
                        "chapter_title": chapter["chapter_title"],
                        "article_number": article["article_number"],
                        "article_title": article["article_title"],
                        "type": "article"
                    })
            
            # Create edges for relationships
            relationship_count = 0
            for node in network["nodes"]:
                article_ref = node["id"]
                related_articles = await self.get_related_articles(article_ref)
                
                for related in related_articles:
                    related_ref = f"{related['chapter_number']}.{related['article_number']}"
                    
                    # Create edge
                    network["edges"].append({
                        "source": article_ref,
                        "target": related_ref,
                        "weight": related.get("relevance_score", 0.5),
                        "type": related.get("relevance", "unknown")
                    })
                    relationship_count += 1
            
            # Calculate statistics
            network["statistics"]["total_articles"] = len(network["nodes"])
            network["statistics"]["total_relationships"] = relationship_count
            network["statistics"]["average_connections"] = (
                relationship_count / len(network["nodes"]) if network["nodes"] else 0
            )
            
            return network
            
        except Exception as e:
            self.logger.error(f"Error building content network: {str(e)}")
            return {"nodes": [], "edges": [], "statistics": {}}
    
    async def get_chapter_relationships(self, chapter_num: int,
                                      background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """
        Get relationships for articles within a chapter.
        
        Args:
            chapter_num: Chapter number
            background_tasks: Optional background tasks
            
        Returns:
            Dict: Chapter relationships
        """
        try:
            # Validate chapter number
            chapter_num = self.validator.validate_chapter_number(chapter_num)
            
            cache_key = self._generate_cache_key("chapter_relationships", chapter_num)
            
            # Check cache first
            cached_relationships = await self._cache_get(cache_key)
            if cached_relationships:
                return cached_relationships
            
            # Get chapter data
            chapter = await self.content_retrieval.get_chapter_by_number(chapter_num, background_tasks)
            
            # Build relationships within the chapter
            relationships = {
                "chapter_number": chapter_num,
                "chapter_title": chapter.get("chapter_title", ""),
                "article_relationships": []
            }
            
            for article in chapter.get("articles", []):
                article_ref = f"{chapter_num}.{article['article_number']}"
                related_articles = await self.get_related_articles(article_ref, background_tasks)
                
                relationships["article_relationships"].append({
                    "article_number": article["article_number"],
                    "article_title": article["article_title"],
                    "related_articles": related_articles
                })
            
            # Cache the relationships
            await self._cache_set(cache_key, relationships, 6 * HOUR, background_tasks)
            
            return relationships
            
        except Exception as e:
            self._handle_service_error(e, f"Error getting chapter relationships for chapter {chapter_num}")
    
    async def find_content_clusters(self, background_tasks: Optional[BackgroundTasks] = None) -> List[Dict]:
        """
        Find clusters of related content.
        
        Args:
            background_tasks: Optional background tasks
            
        Returns:
            List[Dict]: Content clusters
        """
        try:
            cache_key = self._generate_cache_key("content_clusters")
            
            # Check cache first
            cached_clusters = await self._cache_get(cache_key)
            if cached_clusters:
                return cached_clusters
            
            # Get content network
            network = await self.get_content_network(background_tasks)
            
            # Simple clustering based on relationship strength
            clusters = self._identify_clusters(network)
            
            # Cache the clusters
            await self._cache_set(cache_key, clusters, DAY, background_tasks)
            
            return clusters
            
        except Exception as e:
            self._handle_service_error(e, "Error finding content clusters")
    
    def _identify_clusters(self, network: Dict) -> List[Dict]:
        """
        Identify clusters in the content network.
        
        Args:
            network: Content network
            
        Returns:
            List[Dict]: Identified clusters
        """
        try:
            # This is a simplified clustering approach
            # In a real implementation, you'd use more sophisticated clustering algorithms
            
            clusters = []
            
            # Group by chapter as a simple clustering approach
            chapter_groups = {}
            for node in network.get("nodes", []):
                chapter_num = node["chapter_number"]
                if chapter_num not in chapter_groups:
                    chapter_groups[chapter_num] = {
                        "cluster_id": f"chapter_{chapter_num}",
                        "cluster_name": node["chapter_title"],
                        "articles": [],
                        "internal_connections": 0
                    }
                
                chapter_groups[chapter_num]["articles"].append(node)
            
            # Calculate internal connections
            for edge in network.get("edges", []):
                source_chapter = int(edge["source"].split(".")[0])
                target_chapter = int(edge["target"].split(".")[0])
                
                if source_chapter == target_chapter:
                    if source_chapter in chapter_groups:
                        chapter_groups[source_chapter]["internal_connections"] += 1
            
            # Convert to list format
            for cluster_data in chapter_groups.values():
                clusters.append(cluster_data)
            
            return clusters
            
        except Exception as e:
            self.logger.error(f"Error identifying clusters: {str(e)}")
            return []