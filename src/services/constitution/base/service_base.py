"""
Base service class for constitution services.
Provides common functionality and infrastructure.
"""

import logging
from typing import Optional
from abc import ABC, abstractmethod
from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from .cache_manager import ConstitutionCacheManager
from .validators import ConstitutionValidator

logger = logging.getLogger(__name__)


class BaseService(ABC):
    """
    Base class for all constitution services.
    Provides common functionality for caching, validation, and database access.
    """
    
    def __init__(self, cache_manager: ConstitutionCacheManager, 
                 db_session: Optional[AsyncSession] = None,
                 validator: Optional[ConstitutionValidator] = None):
        """
        Initialize the base service.
        
        Args:
            cache_manager: Instance of ConstitutionCacheManager
            db_session: Optional database session
            validator: Optional validator instance
        """
        self.cache = cache_manager
        self.db_session = db_session
        self.validator = validator or ConstitutionValidator()
        self.logger = logger
    
    @abstractmethod
    def get_service_name(self) -> str:
        """
        Get the service name for logging and caching.
        
        Returns:
            str: The service name
        """
        pass
    
    async def _cache_get(self, cache_key: str) -> Optional[dict]:
        """
        Get data from cache with error handling.
        
        Args:
            cache_key: The cache key to retrieve
            
        Returns:
            Optional[dict]: Cached data or None if not found
        """
        try:
            cached_data = await self.cache.get(cache_key)
            if cached_data:
                self.logger.info(f"[{self.get_service_name()}] Cache hit for key: {cache_key}")
                return cached_data
            return None
        except Exception as e:
            self.logger.error(f"[{self.get_service_name()}] Cache get error for key {cache_key}: {str(e)}")
            return None
    
    async def _cache_set(self, cache_key: str, data: dict, expire: int, 
                        background_tasks: Optional[BackgroundTasks] = None):
        """
        Set data in cache with error handling.
        
        Args:
            cache_key: The cache key
            data: The data to cache
            expire: Expiration time in seconds
            background_tasks: Optional background tasks for async caching
        """
        try:
            if background_tasks:
                await self.cache.set_background(background_tasks, cache_key, data, expire)
            else:
                await self.cache.set(cache_key, data, expire)
            self.logger.info(f"[{self.get_service_name()}] Data cached with key: {cache_key}")
        except Exception as e:
            self.logger.error(f"[{self.get_service_name()}] Cache set error for key {cache_key}: {str(e)}")
    
    async def _cache_delete(self, cache_key: str):
        """
        Delete data from cache with error handling.
        
        Args:
            cache_key: The cache key to delete
        """
        try:
            await self.cache.delete(cache_key)
            self.logger.info(f"[{self.get_service_name()}] Cache deleted for key: {cache_key}")
        except Exception as e:
            self.logger.error(f"[{self.get_service_name()}] Cache delete error for key {cache_key}: {str(e)}")
    
    async def _cache_clear_pattern(self, pattern: str):
        """
        Clear cache entries matching a pattern.
        
        Args:
            pattern: The pattern to match
        """
        try:
            count = await self.cache.clear_pattern(pattern)
            self.logger.info(f"[{self.get_service_name()}] Cleared {count} cache entries for pattern: {pattern}")
        except Exception as e:
            self.logger.error(f"[{self.get_service_name()}] Cache clear pattern error for {pattern}: {str(e)}")
    
    def _generate_cache_key(self, *args) -> str:
        """
        Generate a cache key from arguments.
        
        Args:
            *args: Arguments to use in cache key
            
        Returns:
            str: Generated cache key
        """
        service_name = self.get_service_name()
        key_parts = [service_name] + [str(arg) for arg in args]
        return ":".join(key_parts)
    
    def _validate_input(self, data: dict, required_fields: list) -> bool:
        """
        Validate input data has required fields.
        
        Args:
            data: Input data to validate
            required_fields: List of required field names
            
        Returns:
            bool: True if valid, False otherwise
        """
        try:
            return self.validator.validate_required_fields(data, required_fields)
        except Exception as e:
            self.logger.error(f"[{self.get_service_name()}] Validation error: {str(e)}")
            return False
    
    def _handle_service_error(self, error: Exception, context: str = ""):
        """
        Handle service errors with proper logging.
        
        Args:
            error: The exception that occurred
            context: Context information about the error
        """
        error_msg = f"[{self.get_service_name()}] {context}: {str(error)}"
        self.logger.error(error_msg)
        
        # Re-raise the error for upstream handling
        raise error
    
    async def health_check(self) -> dict:
        """
        Perform health check for the service.
        
        Returns:
            dict: Health check results
        """
        try:
            # Check cache connectivity
            cache_healthy = await self.cache.health_check()
            
            # Check database connectivity if available
            db_healthy = True
            if self.db_session:
                try:
                    await self.db_session.execute("SELECT 1")
                    db_healthy = True
                except Exception:
                    db_healthy = False
            
            is_healthy = cache_healthy and db_healthy
            
            return {
                "service": self.get_service_name(),
                "healthy": is_healthy,
                "cache_healthy": cache_healthy,
                "database_healthy": db_healthy
            }
        except Exception as e:
            self.logger.error(f"[{self.get_service_name()}] Health check failed: {str(e)}")
            return {
                "service": self.get_service_name(),
                "healthy": False,
                "error": str(e)
            }