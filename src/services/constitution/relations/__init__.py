"""
Relations module for constitution services.
Handles content relationships and related article suggestions.
"""

from .content_relationships import ContentRelationships
from .article_recommender import ArticleRecommender

__all__ = [
    'ContentRelationships',
    'ArticleRecommender'
]