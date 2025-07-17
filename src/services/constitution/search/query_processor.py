"""
Query processor for constitution search.
Handles query parsing, normalization, and hash generation.
"""

import hashlib
import json
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from ..base import BaseService, ConstitutionCacheManager


class QueryProcessor(BaseService):
    """
    Service for processing search queries.
    Handles query normalization, parsing, and hash generation.
    """
    
    def __init__(self, cache_manager: ConstitutionCacheManager):
        """
        Initialize the query processor.
        
        Args:
            cache_manager: Cache manager instance
        """
        super().__init__(cache_manager)
    
    def get_service_name(self) -> str:
        """Get the service name."""
        return "query_processor"
    
    def normalize_query(self, query: str) -> str:
        """
        Normalize a search query.
        
        Args:
            query: Raw search query
            
        Returns:
            str: Normalized query
        """
        try:
            # Validate query
            query = self.validator.validate_search_query(query)
            
            # Basic normalization
            normalized = query.strip().lower()
            
            # Remove extra whitespace
            normalized = re.sub(r'\s+', ' ', normalized)
            
            # Remove common punctuation that doesn't affect search
            normalized = re.sub(r'[^\w\s\-\']', ' ', normalized)
            
            # Handle common variations
            normalized = self._handle_common_variations(normalized)
            
            return normalized.strip()
            
        except Exception as e:
            self._handle_service_error(e, f"Error normalizing query: {query}")
    
    def _handle_common_variations(self, query: str) -> str:
        """
        Handle common variations in search queries.
        
        Args:
            query: Query to process
            
        Returns:
            str: Processed query
        """
        # Common spelling variations and synonyms
        variations = {
            'constitution': ['constitution', 'katiba'],
            'government': ['government', 'serikali'],
            'parliament': ['parliament', 'bunge'],
            'president': ['president', 'rais'],
            'rights': ['rights', 'haki'],
            'freedom': ['freedom', 'uhuru'],
            'citizen': ['citizen', 'mwananchi'],
            'law': ['law', 'sheria'],
            'court': ['court', 'mahakama'],
            'election': ['election', 'uchaguzi']
        }
        
        # Replace variations with canonical forms
        for canonical, variants in variations.items():
            for variant in variants:
                if variant in query:
                    query = query.replace(variant, canonical)
                    break
        
        return query
    
    def extract_query_terms(self, query: str) -> List[str]:
        """
        Extract individual terms from a query.
        
        Args:
            query: Normalized query
            
        Returns:
            List[str]: List of query terms
        """
        try:
            # Split on whitespace and filter out empty strings
            terms = [term.strip() for term in query.split() if term.strip()]
            
            # Remove very short terms (less than 2 characters)
            terms = [term for term in terms if len(term) >= 2]
            
            return terms
            
        except Exception as e:
            self.logger.error(f"Error extracting query terms: {str(e)}")
            return []
    
    def identify_query_type(self, query: str) -> str:
        """
        Identify the type of search query.
        
        Args:
            query: Search query
            
        Returns:
            str: Query type (exact, phrase, keyword, boolean)
        """
        try:
            # Check for exact match (quoted)
            if (query.startswith('"') and query.endswith('"')) or \
               (query.startswith("'") and query.endswith("'")):
                return "exact"
            
            # Check for phrase search (multiple words)
            if len(query.split()) > 1:
                return "phrase"
            
            # Check for boolean operators
            boolean_operators = ['AND', 'OR', 'NOT', '+', '-']
            if any(op in query.upper() for op in boolean_operators):
                return "boolean"
            
            # Default to keyword search
            return "keyword"
            
        except Exception as e:
            self.logger.error(f"Error identifying query type: {str(e)}")
            return "keyword"
    
    def parse_filters(self, filters: Optional[Dict]) -> Optional[Dict]:
        """
        Parse and validate search filters.
        
        Args:
            filters: Raw filters dictionary
            
        Returns:
            Optional[Dict]: Parsed and validated filters
        """
        try:
            if not filters:
                return None
            
            # Validate filters using the validator
            return self.validator.validate_search_filters(filters)
            
        except Exception as e:
            self.logger.error(f"Error parsing filters: {str(e)}")
            return None
    
    def generate_search_hash(self, query: str, filters: Optional[Dict] = None,
                           limit: Optional[int] = 10, offset: Optional[int] = 0,
                           highlight: bool = True) -> str:
        """
        Generate a consistent hash for search parameters.
        
        Args:
            query: Search query
            filters: Optional filters
            limit: Maximum number of results
            offset: Number of results to skip
            highlight: Whether to highlight matches
            
        Returns:
            str: Hash string for cache key
        """
        try:
            # Normalize query first
            normalized_query = self.normalize_query(query)
            
            # Create a string representation of search parameters
            filters_str = json.dumps(filters, sort_keys=True) if filters else "none"
            params_str = f"{normalized_query}:{filters_str}:{limit}:{offset}:{highlight}"
            
            # Generate hash
            return hashlib.md5(params_str.encode()).hexdigest()
            
        except Exception as e:
            self.logger.error(f"Error generating search hash: {str(e)}")
            # Return a fallback hash
            return hashlib.md5(f"{query}:{datetime.now().timestamp()}".encode()).hexdigest()
    
    def extract_article_references(self, query: str) -> List[Tuple[int, int]]:
        """
        Extract article references from a query (e.g., "Article 19", "19", "1.19").
        
        Args:
            query: Search query
            
        Returns:
            List[Tuple[int, int]]: List of (chapter_num, article_num) tuples
        """
        try:
            references = []
            
            # Pattern for "Article X" or "article X"
            article_pattern = r'\barticle\s+(\d+)\b'
            matches = re.findall(article_pattern, query, re.IGNORECASE)
            for match in matches:
                article_num = int(match)
                # For standalone article numbers, we'll need to search across all chapters
                # This is a simplified approach - in reality, you'd need context
                references.append((0, article_num))  # 0 indicates any chapter
            
            # Pattern for "Chapter X Article Y" or "X.Y"
            chapter_article_pattern = r'\b(\d+)\.(\d+)\b'
            matches = re.findall(chapter_article_pattern, query)
            for match in matches:
                chapter_num = int(match[0])
                article_num = int(match[1])
                references.append((chapter_num, article_num))
            
            # Pattern for "Chapter X"
            chapter_pattern = r'\bchapter\s+(\d+)\b'
            matches = re.findall(chapter_pattern, query, re.IGNORECASE)
            for match in matches:
                chapter_num = int(match)
                references.append((chapter_num, 0))  # 0 indicates any article in chapter
            
            return references
            
        except Exception as e:
            self.logger.error(f"Error extracting article references: {str(e)}")
            return []
    
    def extract_legal_terms(self, query: str) -> List[str]:
        """
        Extract legal terms and concepts from a query.
        
        Args:
            query: Search query
            
        Returns:
            List[str]: List of legal terms
        """
        try:
            # Common legal terms in the Kenyan constitution
            legal_terms = {
                'fundamental rights', 'bill of rights', 'human rights',
                'due process', 'equal protection', 'rule of law',
                'separation of powers', 'checks and balances',
                'judicial review', 'constitutional amendment',
                'devolution', 'county government', 'national government',
                'parliament', 'national assembly', 'senate',
                'executive', 'president', 'deputy president',
                'cabinet', 'attorney general', 'director of public prosecutions',
                'judiciary', 'chief justice', 'supreme court',
                'high court', 'court of appeal', 'subordinate courts',
                'commission', 'independent office', 'constitutional commission',
                'elections', 'electoral commission', 'constituency',
                'referendum', 'constitutional convention',
                'citizenship', 'naturalization', 'statelessness',
                'land tenure', 'compulsory acquisition', 'compensation',
                'environment', 'natural resources', 'sustainable development',
                'public finance', 'consolidated fund', 'taxation',
                'public debt', 'equitable sharing', 'revenue allocation'
            }
            
            found_terms = []
            query_lower = query.lower()
            
            for term in legal_terms:
                if term in query_lower:
                    found_terms.append(term)
            
            return found_terms
            
        except Exception as e:
            self.logger.error(f"Error extracting legal terms: {str(e)}")
            return []
    
    def suggest_query_corrections(self, query: str) -> List[str]:
        """
        Suggest corrections for a query.
        
        Args:
            query: Original query
            
        Returns:
            List[str]: List of suggested corrections
        """
        try:
            suggestions = []
            
            # Common misspellings and corrections
            corrections = {
                'constution': 'constitution',
                'constituton': 'constitution',
                'goverment': 'government',
                'govenment': 'government',
                'parliment': 'parliament',
                'parlimant': 'parliament',
                'presedent': 'president',
                'presidente': 'president',
                'rigths': 'rights',
                'rihts': 'rights',
                'citezen': 'citizen',
                'citicen': 'citizen',
                'electon': 'election',
                'elecction': 'election',
                'judical': 'judicial',
                'judicary': 'judiciary'
            }
            
            words = query.lower().split()
            corrected_words = []
            has_corrections = False
            
            for word in words:
                if word in corrections:
                    corrected_words.append(corrections[word])
                    has_corrections = True
                else:
                    corrected_words.append(word)
            
            if has_corrections:
                suggestions.append(' '.join(corrected_words))
            
            return suggestions
            
        except Exception as e:
            self.logger.error(f"Error suggesting query corrections: {str(e)}")
            return []
    
    def analyze_query_complexity(self, query: str) -> Dict:
        """
        Analyze the complexity of a search query.
        
        Args:
            query: Search query
            
        Returns:
            Dict: Query complexity analysis
        """
        try:
            analysis = {
                "length": len(query),
                "word_count": len(query.split()),
                "query_type": self.identify_query_type(query),
                "has_article_references": bool(self.extract_article_references(query)),
                "has_legal_terms": bool(self.extract_legal_terms(query)),
                "complexity_score": 0
            }
            
            # Calculate complexity score
            score = 0
            
            # Length contribution
            if analysis["length"] > 100:
                score += 2
            elif analysis["length"] > 50:
                score += 1
            
            # Word count contribution
            if analysis["word_count"] > 10:
                score += 2
            elif analysis["word_count"] > 5:
                score += 1
            
            # Query type contribution
            if analysis["query_type"] == "boolean":
                score += 3
            elif analysis["query_type"] == "phrase":
                score += 2
            elif analysis["query_type"] == "exact":
                score += 1
            
            # Special features
            if analysis["has_article_references"]:
                score += 1
            if analysis["has_legal_terms"]:
                score += 1
            
            analysis["complexity_score"] = score
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing query complexity: {str(e)}")
            return {
                "length": 0,
                "word_count": 0,
                "query_type": "keyword",
                "has_article_references": False,
                "has_legal_terms": False,
                "complexity_score": 0
            }