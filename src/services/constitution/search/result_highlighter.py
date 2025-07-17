"""
Result highlighter for constitution search.
Handles highlighting of search terms in results.
"""

import re
from typing import List, Dict, Optional, Tuple

from ..base import BaseService, ConstitutionCacheManager


class ResultHighlighter(BaseService):
    """
    Service for highlighting search terms in results.
    Handles text highlighting, context extraction, and formatting.
    """
    
    def __init__(self, cache_manager: ConstitutionCacheManager):
        """
        Initialize the result highlighter.
        
        Args:
            cache_manager: Cache manager instance
        """
        super().__init__(cache_manager)
        self.default_highlight_tag = "**"
        self.default_context_length = 200
    
    def get_service_name(self) -> str:
        """Get the service name."""
        return "result_highlighter"
    
    def highlight_text(self, text: str, query: str, 
                      highlight_tag: str = None,
                      case_sensitive: bool = False) -> str:
        """
        Highlight search terms in text.
        
        Args:
            text: Text to highlight
            query: Search query
            highlight_tag: Tag to use for highlighting (default: **)
            case_sensitive: Whether to perform case-sensitive highlighting
            
        Returns:
            str: Text with highlighted terms
        """
        try:
            if not query or not text:
                return text
            
            highlight_tag = highlight_tag or self.default_highlight_tag
            
            # Normalize query for highlighting
            query_terms = self._extract_highlight_terms(query)
            
            if not query_terms:
                return text
            
            # Sort terms by length (longest first) to avoid partial matches
            query_terms.sort(key=len, reverse=True)
            
            highlighted_text = text
            
            for term in query_terms:
                if not term:
                    continue
                
                # Create regex pattern
                flags = 0 if case_sensitive else re.IGNORECASE
                pattern = re.escape(term)
                
                # Find all matches
                matches = list(re.finditer(pattern, highlighted_text, flags))
                
                # Highlight matches in reverse order to maintain positions
                for match in reversed(matches):
                    start, end = match.span()
                    original_term = highlighted_text[start:end]
                    
                    # Skip if already highlighted
                    if highlighted_text[max(0, start-len(highlight_tag)):start] == highlight_tag:
                        continue
                    
                    highlighted_term = f"{highlight_tag}{original_term}{highlight_tag}"
                    highlighted_text = (
                        highlighted_text[:start] + 
                        highlighted_term + 
                        highlighted_text[end:]
                    )
            
            return highlighted_text
            
        except Exception as e:
            self.logger.error(f"Error highlighting text: {str(e)}")
            return text
    
    def _extract_highlight_terms(self, query: str) -> List[str]:
        """
        Extract terms from query for highlighting.
        
        Args:
            query: Search query
            
        Returns:
            List[str]: List of terms to highlight
        """
        try:
            # Remove quotes for exact matches
            if (query.startswith('"') and query.endswith('"')) or \
               (query.startswith("'") and query.endswith("'")):
                return [query[1:-1]]
            
            # Split on whitespace and filter
            terms = [term.strip() for term in query.split() if term.strip()]
            
            # Remove very short terms and common words
            stop_words = {'the', 'and', 'or', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
            terms = [term for term in terms if len(term) >= 2 and term.lower() not in stop_words]
            
            return terms
            
        except Exception as e:
            self.logger.error(f"Error extracting highlight terms: {str(e)}")
            return []
    
    def extract_context(self, text: str, query: str, 
                       context_length: int = None) -> str:
        """
        Extract context around search terms.
        
        Args:
            text: Full text
            query: Search query
            context_length: Length of context to extract
            
        Returns:
            str: Context with highlighted terms
        """
        try:
            if not query or not text:
                return text
            
            context_length = context_length or self.default_context_length
            
            # Find the first occurrence of any query term
            query_terms = self._extract_highlight_terms(query)
            if not query_terms:
                return text[:context_length] + ("..." if len(text) > context_length else "")
            
            # Find the earliest match
            earliest_match = None
            earliest_position = len(text)
            
            for term in query_terms:
                match = re.search(re.escape(term), text, re.IGNORECASE)
                if match and match.start() < earliest_position:
                    earliest_match = match
                    earliest_position = match.start()
            
            if not earliest_match:
                return text[:context_length] + ("..." if len(text) > context_length else "")
            
            # Calculate context boundaries
            match_start = earliest_match.start()
            match_end = earliest_match.end()
            
            # Try to center the match in the context
            context_start = max(0, match_start - context_length // 2)
            context_end = min(len(text), context_start + context_length)
            
            # Adjust start if we're at the end of the text
            if context_end == len(text):
                context_start = max(0, context_end - context_length)
            
            # Extract context
            context = text[context_start:context_end]
            
            # Add ellipsis if needed
            if context_start > 0:
                context = "..." + context
            if context_end < len(text):
                context = context + "..."
            
            # Highlight the context
            highlighted_context = self.highlight_text(context, query)
            
            return highlighted_context
            
        except Exception as e:
            self.logger.error(f"Error extracting context: {str(e)}")
            return text[:context_length] + ("..." if len(text) > context_length else "")
    
    def highlight_search_results(self, results: List[Dict], query: str,
                               highlight_fields: List[str] = None) -> List[Dict]:
        """
        Highlight search terms in multiple search results.
        
        Args:
            results: List of search results
            query: Search query
            highlight_fields: Fields to highlight (default: ['content', 'match_context'])
            
        Returns:
            List[Dict]: Results with highlighted terms
        """
        try:
            if not results or not query:
                return results
            
            highlight_fields = highlight_fields or ['content', 'match_context']
            highlighted_results = []
            
            for result in results:
                highlighted_result = result.copy()
                
                for field in highlight_fields:
                    if field in result and result[field]:
                        highlighted_result[field] = self.highlight_text(
                            result[field], query
                        )
                
                # Generate context if not present
                if 'match_context' not in highlighted_result and 'content' in result:
                    highlighted_result['match_context'] = self.extract_context(
                        result['content'], query
                    )
                
                highlighted_results.append(highlighted_result)
            
            return highlighted_results
            
        except Exception as e:
            self.logger.error(f"Error highlighting search results: {str(e)}")
            return results
    
    def get_snippet(self, text: str, query: str, 
                   snippet_length: int = 150) -> str:
        """
        Get a snippet of text around search terms.
        
        Args:
            text: Full text
            query: Search query
            snippet_length: Length of snippet
            
        Returns:
            str: Text snippet with highlighted terms
        """
        try:
            if not query or not text:
                return text[:snippet_length] + ("..." if len(text) > snippet_length else "")
            
            # Extract context around the query
            context = self.extract_context(text, query, snippet_length)
            
            return context
            
        except Exception as e:
            self.logger.error(f"Error getting snippet: {str(e)}")
            return text[:snippet_length] + ("..." if len(text) > snippet_length else "")
    
    def highlight_article_title(self, title: str, query: str) -> str:
        """
        Highlight search terms in article title.
        
        Args:
            title: Article title
            query: Search query
            
        Returns:
            str: Title with highlighted terms
        """
        try:
            return self.highlight_text(title, query)
            
        except Exception as e:
            self.logger.error(f"Error highlighting article title: {str(e)}")
            return title
    
    def highlight_chapter_title(self, title: str, query: str) -> str:
        """
        Highlight search terms in chapter title.
        
        Args:
            title: Chapter title
            query: Search query
            
        Returns:
            str: Title with highlighted terms
        """
        try:
            return self.highlight_text(title, query)
            
        except Exception as e:
            self.logger.error(f"Error highlighting chapter title: {str(e)}")
            return title
    
    def create_highlighted_result(self, result_type: str, content: str, 
                                 query: str, metadata: Dict = None) -> Dict:
        """
        Create a highlighted search result.
        
        Args:
            result_type: Type of result (chapter, article, clause, etc.)
            content: Content to highlight
            query: Search query
            metadata: Additional metadata
            
        Returns:
            Dict: Highlighted search result
        """
        try:
            metadata = metadata or {}
            
            highlighted_result = {
                "type": result_type,
                "content": content,
                "highlighted_content": self.highlight_text(content, query),
                "match_context": self.extract_context(content, query),
                "snippet": self.get_snippet(content, query),
                **metadata
            }
            
            return highlighted_result
            
        except Exception as e:
            self.logger.error(f"Error creating highlighted result: {str(e)}")
            return {
                "type": result_type,
                "content": content,
                "highlighted_content": content,
                "match_context": content,
                "snippet": content[:150] + ("..." if len(content) > 150 else ""),
                **metadata
            }
    
    def get_highlight_statistics(self, text: str, query: str) -> Dict:
        """
        Get statistics about highlighting in text.
        
        Args:
            text: Text to analyze
            query: Search query
            
        Returns:
            Dict: Highlighting statistics
        """
        try:
            query_terms = self._extract_highlight_terms(query)
            
            stats = {
                "total_matches": 0,
                "unique_terms_matched": 0,
                "term_frequencies": {},
                "match_positions": []
            }
            
            for term in query_terms:
                if not term:
                    continue
                
                matches = list(re.finditer(re.escape(term), text, re.IGNORECASE))
                if matches:
                    stats["unique_terms_matched"] += 1
                    stats["term_frequencies"][term] = len(matches)
                    stats["total_matches"] += len(matches)
                    
                    # Store match positions
                    for match in matches:
                        stats["match_positions"].append({
                            "term": term,
                            "start": match.start(),
                            "end": match.end(),
                            "matched_text": match.group()
                        })
            
            # Sort match positions by start position
            stats["match_positions"].sort(key=lambda x: x["start"])
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting highlight statistics: {str(e)}")
            return {
                "total_matches": 0,
                "unique_terms_matched": 0,
                "term_frequencies": {},
                "match_positions": []
            }