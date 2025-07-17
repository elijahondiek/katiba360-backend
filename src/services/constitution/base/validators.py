"""
Validators for constitution service inputs.
Provides comprehensive validation for all constitution-related operations.
"""

import re
import uuid
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


class ConstitutionValidator:
    """
    Validator class for constitution service inputs.
    Provides validation methods for all constitution-related operations.
    """
    
    def __init__(self):
        self.logger = logger
    
    def validate_required_fields(self, data: Dict, required_fields: List[str]) -> bool:
        """
        Validate that all required fields are present in the data.
        
        Args:
            data: Data to validate
            required_fields: List of required field names
            
        Returns:
            bool: True if all required fields are present
            
        Raises:
            ValidationError: If any required field is missing
        """
        missing_fields = []
        
        for field in required_fields:
            if field not in data or data[field] is None:
                missing_fields.append(field)
        
        if missing_fields:
            error_msg = f"Missing required fields: {', '.join(missing_fields)}"
            self.logger.error(error_msg)
            raise ValidationError(error_msg)
        
        return True
    
    def validate_chapter_number(self, chapter_num: Union[int, str]) -> int:
        """
        Validate chapter number.
        
        Args:
            chapter_num: Chapter number to validate
            
        Returns:
            int: Validated chapter number
            
        Raises:
            ValidationError: If chapter number is invalid
        """
        try:
            chapter_num = int(chapter_num)
            if chapter_num < 1 or chapter_num > 20:  # Kenyan constitution has 18 chapters
                raise ValidationError(f"Chapter number must be between 1 and 20, got: {chapter_num}")
            return chapter_num
        except (ValueError, TypeError):
            raise ValidationError(f"Invalid chapter number format: {chapter_num}")
    
    def validate_article_number(self, article_num: Union[int, str]) -> int:
        """
        Validate article number.
        
        Args:
            article_num: Article number to validate
            
        Returns:
            int: Validated article number
            
        Raises:
            ValidationError: If article number is invalid
        """
        try:
            article_num = int(article_num)
            if article_num < 1 or article_num > 300:  # Reasonable upper bound
                raise ValidationError(f"Article number must be between 1 and 300, got: {article_num}")
            return article_num
        except (ValueError, TypeError):
            raise ValidationError(f"Invalid article number format: {article_num}")
    
    def validate_article_reference(self, reference: str) -> tuple:
        """
        Validate article reference format (e.g., "1.2" for Chapter 1, Article 2).
        
        Args:
            reference: Article reference string
            
        Returns:
            tuple: (chapter_num, article_num)
            
        Raises:
            ValidationError: If reference format is invalid
        """
        if not isinstance(reference, str):
            raise ValidationError(f"Article reference must be a string, got: {type(reference)}")
        
        parts = reference.split('.')
        if len(parts) != 2:
            raise ValidationError(f"Invalid article reference format. Expected 'chapter.article', got: {reference}")
        
        try:
            chapter_num = self.validate_chapter_number(parts[0])
            article_num = self.validate_article_number(parts[1])
            return (chapter_num, article_num)
        except ValidationError:
            raise ValidationError(f"Invalid article reference: {reference}")
    
    def validate_search_query(self, query: str) -> str:
        """
        Validate search query.
        
        Args:
            query: Search query to validate
            
        Returns:
            str: Validated and sanitized query
            
        Raises:
            ValidationError: If query is invalid
        """
        if not isinstance(query, str):
            raise ValidationError(f"Search query must be a string, got: {type(query)}")
        
        # Trim whitespace
        query = query.strip()
        
        # Check minimum length
        if len(query) < 2:
            raise ValidationError("Search query must be at least 2 characters long")
        
        # Check maximum length
        if len(query) > 500:
            raise ValidationError("Search query cannot exceed 500 characters")
        
        # Check for malicious patterns
        suspicious_patterns = [
            r'<script[^>]*>.*?</script>',  # Script tags
            r'javascript:',                # JavaScript URLs
            r'on\w+\s*=',                 # Event handlers
            r'eval\s*\(',                 # Eval functions
            r'document\.',                # DOM manipulation
            r'window\.',                  # Window object access
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                raise ValidationError("Search query contains potentially malicious content")
        
        return query
    
    def validate_user_id(self, user_id: Union[str, uuid.UUID]) -> str:
        """
        Validate user ID format.
        
        Args:
            user_id: User ID to validate
            
        Returns:
            str: Validated user ID as string
            
        Raises:
            ValidationError: If user ID is invalid
        """
        if isinstance(user_id, uuid.UUID):
            return str(user_id)
        
        if not isinstance(user_id, str):
            raise ValidationError(f"User ID must be a string or UUID, got: {type(user_id)}")
        
        try:
            # Validate UUID format
            uuid.UUID(user_id)
            return user_id
        except ValueError:
            raise ValidationError(f"Invalid user ID format: {user_id}")
    
    def validate_bookmark_type(self, bookmark_type: str) -> str:
        """
        Validate bookmark type.
        
        Args:
            bookmark_type: Bookmark type to validate
            
        Returns:
            str: Validated bookmark type
            
        Raises:
            ValidationError: If bookmark type is invalid
        """
        if not isinstance(bookmark_type, str):
            raise ValidationError(f"Bookmark type must be a string, got: {type(bookmark_type)}")
        
        valid_types = ['chapter', 'article', 'clause', 'sub_clause']
        if bookmark_type not in valid_types:
            raise ValidationError(f"Invalid bookmark type. Must be one of: {', '.join(valid_types)}")
        
        return bookmark_type
    
    def validate_bookmark_reference(self, reference: str, bookmark_type: str) -> str:
        """
        Validate bookmark reference based on type.
        
        Args:
            reference: Reference string
            bookmark_type: Type of bookmark
            
        Returns:
            str: Validated reference
            
        Raises:
            ValidationError: If reference is invalid for the given type
        """
        if not isinstance(reference, str):
            raise ValidationError(f"Bookmark reference must be a string, got: {type(reference)}")
        
        reference = reference.strip()
        
        if bookmark_type == 'chapter':
            # Chapter reference should be just a number
            self.validate_chapter_number(reference)
        elif bookmark_type == 'article':
            # Article reference should be "chapter.article"
            self.validate_article_reference(reference)
        elif bookmark_type in ['clause', 'sub_clause']:
            # More complex validation for clauses and sub-clauses
            # For now, just check it's not empty
            if not reference:
                raise ValidationError("Clause/sub-clause reference cannot be empty")
        
        return reference
    
    def validate_bookmark_title(self, title: str) -> str:
        """
        Validate bookmark title.
        
        Args:
            title: Title to validate
            
        Returns:
            str: Validated and sanitized title
            
        Raises:
            ValidationError: If title is invalid
        """
        if not isinstance(title, str):
            raise ValidationError(f"Bookmark title must be a string, got: {type(title)}")
        
        title = title.strip()
        
        if not title:
            raise ValidationError("Bookmark title cannot be empty")
        
        if len(title) > 500:
            raise ValidationError("Bookmark title cannot exceed 500 characters")
        
        return title
    
    def validate_pagination_params(self, limit: Optional[int], offset: Optional[int]) -> tuple:
        """
        Validate pagination parameters.
        
        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            tuple: (validated_limit, validated_offset)
            
        Raises:
            ValidationError: If pagination parameters are invalid
        """
        if limit is not None:
            if not isinstance(limit, int) or limit < 1:
                raise ValidationError("Limit must be a positive integer")
            if limit > 1000:
                raise ValidationError("Limit cannot exceed 1000")
        
        if offset is not None:
            if not isinstance(offset, int) or offset < 0:
                raise ValidationError("Offset must be a non-negative integer")
            if offset > 100000:
                raise ValidationError("Offset cannot exceed 100000")
        
        return (limit, offset or 0)
    
    def validate_timeframe(self, timeframe: str) -> str:
        """
        Validate timeframe parameter.
        
        Args:
            timeframe: Timeframe to validate
            
        Returns:
            str: Validated timeframe
            
        Raises:
            ValidationError: If timeframe is invalid
        """
        if not isinstance(timeframe, str):
            raise ValidationError(f"Timeframe must be a string, got: {type(timeframe)}")
        
        valid_timeframes = ['daily', 'weekly', 'monthly', 'yearly']
        if timeframe not in valid_timeframes:
            raise ValidationError(f"Invalid timeframe. Must be one of: {', '.join(valid_timeframes)}")
        
        return timeframe
    
    def validate_reading_time(self, read_time_minutes: Union[int, float]) -> float:
        """
        Validate reading time in minutes.
        
        Args:
            read_time_minutes: Reading time to validate
            
        Returns:
            float: Validated reading time
            
        Raises:
            ValidationError: If reading time is invalid
        """
        try:
            read_time_minutes = float(read_time_minutes)
            if read_time_minutes < 0:
                raise ValidationError("Reading time cannot be negative")
            if read_time_minutes > 1440:  # 24 hours
                raise ValidationError("Reading time cannot exceed 24 hours")
            return read_time_minutes
        except (ValueError, TypeError):
            raise ValidationError(f"Invalid reading time format: {read_time_minutes}")
    
    def validate_content_type(self, content_type: str) -> str:
        """
        Validate content type.
        
        Args:
            content_type: Content type to validate
            
        Returns:
            str: Validated content type
            
        Raises:
            ValidationError: If content type is invalid
        """
        if not isinstance(content_type, str):
            raise ValidationError(f"Content type must be a string, got: {type(content_type)}")
        
        valid_types = ['chapter', 'article', 'clause', 'sub_clause', 'preamble', 'search']
        if content_type not in valid_types:
            raise ValidationError(f"Invalid content type. Must be one of: {', '.join(valid_types)}")
        
        return content_type
    
    def validate_search_filters(self, filters: Optional[Dict]) -> Optional[Dict]:
        """
        Validate search filters.
        
        Args:
            filters: Filters to validate
            
        Returns:
            Optional[Dict]: Validated filters
            
        Raises:
            ValidationError: If filters are invalid
        """
        if filters is None:
            return None
        
        if not isinstance(filters, dict):
            raise ValidationError(f"Filters must be a dictionary, got: {type(filters)}")
        
        validated_filters = {}
        
        # Validate chapter filter
        if 'chapter' in filters:
            validated_filters['chapter'] = self.validate_chapter_number(filters['chapter'])
        
        # Validate article filter
        if 'article' in filters:
            validated_filters['article'] = self.validate_article_number(filters['article'])
        
        # Validate content type filter
        if 'content_type' in filters:
            validated_filters['content_type'] = self.validate_content_type(filters['content_type'])
        
        return validated_filters if validated_filters else None
    
    def sanitize_html(self, text: str) -> str:
        """
        Sanitize HTML content by removing potentially dangerous tags.
        
        Args:
            text: Text to sanitize
            
        Returns:
            str: Sanitized text
        """
        if not isinstance(text, str):
            return str(text)
        
        # Remove script tags and their content
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove other dangerous tags
        dangerous_tags = ['iframe', 'object', 'embed', 'link', 'style', 'meta']
        for tag in dangerous_tags:
            text = re.sub(f'<{tag}[^>]*>.*?</{tag}>', '', text, flags=re.IGNORECASE | re.DOTALL)
            text = re.sub(f'<{tag}[^>]*/?>', '', text, flags=re.IGNORECASE)
        
        # Remove event handlers
        text = re.sub(r'on\w+\s*=\s*["\'][^"\']*["\']', '', text, flags=re.IGNORECASE)
        
        # Remove javascript: URLs
        text = re.sub(r'javascript:[^"\']*', '', text, flags=re.IGNORECASE)
        
        return text