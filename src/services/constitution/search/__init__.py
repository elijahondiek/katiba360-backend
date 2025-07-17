"""
Search module for constitution services.
Handles search functionality, query processing, and result ranking.
"""

from .search_engine import SearchEngine
from .query_processor import QueryProcessor
from .result_highlighter import ResultHighlighter

__all__ = [
    'SearchEngine',
    'QueryProcessor',
    'ResultHighlighter'
]