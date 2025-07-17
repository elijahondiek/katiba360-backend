"""
Content loader service for constitution data.
Handles loading and caching of constitution data from files.
"""

import json
import os
from typing import Dict, Optional
from datetime import datetime
from pathlib import Path
from fastapi import BackgroundTasks

from ..base import BaseService, ConstitutionCacheManager
from ....utils.cache import HOUR


class ContentLoader(BaseService):
    """
    Service for loading constitution data from files.
    Handles file I/O, caching, and data validation.
    """
    
    def __init__(self, cache_manager: ConstitutionCacheManager, 
                 data_file_path: Optional[str] = None):
        """
        Initialize the content loader.
        
        Args:
            cache_manager: Cache manager instance
            data_file_path: Optional path to constitution data file
        """
        super().__init__(cache_manager)
        
        # Set default data file path if not provided
        if data_file_path is None:
            self._file_path = Path(__file__).parent.parent.parent.parent / "data" / "processed" / "constitution_final.json"
        else:
            self._file_path = Path(data_file_path)
        
        self._last_loaded = None
        self._data_cache = None
        self._file_modified_time = None
    
    def get_service_name(self) -> str:
        """Get the service name."""
        return "content_loader"
    
    def _get_file_modified_time(self) -> float:
        """
        Get the last modified time of the constitution data file.
        
        Returns:
            float: Last modified timestamp
        """
        try:
            return os.path.getmtime(self._file_path)
        except OSError:
            return 0.0
    
    def _is_file_modified(self) -> bool:
        """
        Check if the constitution data file has been modified.
        
        Returns:
            bool: True if file has been modified since last load
        """
        current_modified_time = self._get_file_modified_time()
        return (self._file_modified_time is None or 
                current_modified_time > self._file_modified_time)
    
    async def _load_data_from_file(self) -> Dict:
        """
        Load constitution data from the JSON file.
        
        Returns:
            Dict: Constitution data
            
        Raises:
            FileNotFoundError: If data file doesn't exist
            ValueError: If JSON data is invalid
        """
        try:
            if not os.path.exists(self._file_path):
                error_msg = f"Constitution data file not found at {self._file_path}"
                self.logger.error(error_msg)
                raise FileNotFoundError(error_msg)
            
            with open(self._file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                
                # Validate basic structure
                if not isinstance(data, dict):
                    raise ValueError("Constitution data must be a dictionary")
                
                if 'chapters' not in data:
                    raise ValueError("Constitution data must contain 'chapters' key")
                
                if not isinstance(data['chapters'], list):
                    raise ValueError("Constitution chapters must be a list")
                
                # Update tracking variables
                self._last_loaded = datetime.now()
                self._file_modified_time = self._get_file_modified_time()
                self._data_cache = data
                
                self.logger.info(f"Constitution data loaded from file at {self._last_loaded}")
                return data
                
        except json.JSONDecodeError as e:
            error_msg = f"Error parsing constitution JSON data: {e}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error loading constitution data: {str(e)}"
            self.logger.error(error_msg)
            raise
    
    async def get_constitution_data(self, background_tasks: Optional[BackgroundTasks] = None,
                                  force_reload: bool = False) -> Dict:
        """
        Get the constitution data from cache or load from file.
        
        Args:
            background_tasks: Optional background tasks for async caching
            force_reload: Force reload from file, bypassing cache
            
        Returns:
            Dict: Constitution data
        """
        try:
            # Check if force reload is requested
            if force_reload:
                self.logger.info("Force reload requested, loading fresh data from file")
                data = await self._load_data_from_file()
                await self._cache_constitution_data(data, background_tasks)
                return data
            
            # Check if file has been modified
            if self._is_file_modified():
                self.logger.info("Constitution file has been modified, reloading data")
                data = await self._load_data_from_file()
                await self._cache_constitution_data(data, background_tasks)
                return data
            
            # Try to get from cache first
            cached_data = await self.cache.get_constitution_overview()
            if cached_data:
                self.logger.info("Constitution data retrieved from cache")
                return cached_data
            
            # If not in cache, load from file
            self.logger.info("Constitution data not in cache, loading from file")
            data = await self._load_data_from_file()
            await self._cache_constitution_data(data, background_tasks)
            return data
            
        except Exception as e:
            self._handle_service_error(e, "Error getting constitution data")
    
    async def _cache_constitution_data(self, data: Dict, 
                                     background_tasks: Optional[BackgroundTasks] = None):
        """
        Cache the constitution data.
        
        Args:
            data: Constitution data to cache
            background_tasks: Optional background tasks for async caching
        """
        if background_tasks:
            background_tasks.add_task(
                self.cache.set_constitution_overview,
                data,
                6 * HOUR
            )
        else:
            await self.cache.set_constitution_overview(data, 6 * HOUR)
    
    async def reload_constitution_data(self, background_tasks: Optional[BackgroundTasks] = None) -> Dict:
        """
        Force reload of constitution data and update cache.
        
        Args:
            background_tasks: Optional background tasks for async caching
            
        Returns:
            Dict: Fresh constitution data
        """
        try:
            # Clear existing cache
            await self.cache.delete("constitution:overview")
            
            # Load fresh data from file
            data = await self._load_data_from_file()
            
            # Cache the fresh data
            await self._cache_constitution_data(data, background_tasks)
            
            self.logger.info("Constitution data reloaded and cache updated")
            return data
            
        except Exception as e:
            self._handle_service_error(e, "Error reloading constitution data")
    
    def get_last_loaded_time(self) -> Optional[datetime]:
        """
        Get the timestamp when data was last loaded from file.
        
        Returns:
            Optional[datetime]: Last loaded timestamp
        """
        return self._last_loaded
    
    def get_file_path(self) -> Path:
        """
        Get the path to the constitution data file.
        
        Returns:
            Path: File path
        """
        return self._file_path
    
    def get_file_info(self) -> Dict:
        """
        Get information about the constitution data file.
        
        Returns:
            Dict: File information
        """
        try:
            file_stats = os.stat(self._file_path)
            return {
                "file_path": str(self._file_path),
                "file_size": file_stats.st_size,
                "file_modified": datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
                "file_exists": True,
                "last_loaded": self._last_loaded.isoformat() if self._last_loaded else None
            }
        except OSError as e:
            return {
                "file_path": str(self._file_path),
                "file_exists": False,
                "error": str(e)
            }
    
    async def validate_data_integrity(self) -> Dict:
        """
        Validate the integrity of the constitution data.
        
        Returns:
            Dict: Validation results
        """
        try:
            data = await self.get_constitution_data()
            
            validation_results = {
                "valid": True,
                "errors": [],
                "warnings": [],
                "stats": {}
            }
            
            # Check basic structure
            if not isinstance(data, dict):
                validation_results["valid"] = False
                validation_results["errors"].append("Data is not a dictionary")
                return validation_results
            
            # Check required fields
            required_fields = ['title', 'chapters']
            for field in required_fields:
                if field not in data:
                    validation_results["valid"] = False
                    validation_results["errors"].append(f"Missing required field: {field}")
            
            # Validate chapters
            if 'chapters' in data:
                chapters = data['chapters']
                if not isinstance(chapters, list):
                    validation_results["valid"] = False
                    validation_results["errors"].append("Chapters must be a list")
                else:
                    validation_results["stats"]["total_chapters"] = len(chapters)
                    
                    # Validate each chapter
                    total_articles = 0
                    chapter_numbers = set()
                    
                    for i, chapter in enumerate(chapters):
                        if not isinstance(chapter, dict):
                            validation_results["errors"].append(f"Chapter {i+1} is not a dictionary")
                            continue
                        
                        # Check chapter number
                        if 'chapter_number' not in chapter:
                            validation_results["errors"].append(f"Chapter {i+1} missing chapter_number")
                        else:
                            chapter_num = chapter['chapter_number']
                            if chapter_num in chapter_numbers:
                                validation_results["errors"].append(f"Duplicate chapter number: {chapter_num}")
                            chapter_numbers.add(chapter_num)
                        
                        # Check chapter title
                        if 'chapter_title' not in chapter:
                            validation_results["errors"].append(f"Chapter {i+1} missing chapter_title")
                        
                        # Check articles
                        if 'articles' in chapter:
                            articles = chapter['articles']
                            if isinstance(articles, list):
                                total_articles += len(articles)
                            else:
                                validation_results["warnings"].append(f"Chapter {i+1} articles is not a list")
                    
                    validation_results["stats"]["total_articles"] = total_articles
            
            # Set overall validity
            validation_results["valid"] = len(validation_results["errors"]) == 0
            
            self.logger.info(f"Data integrity validation completed: {validation_results['valid']}")
            return validation_results
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [str(e)],
                "warnings": [],
                "stats": {}
            }
    
    async def get_data_statistics(self) -> Dict:
        """
        Get statistics about the constitution data.
        
        Returns:
            Dict: Data statistics
        """
        try:
            data = await self.get_constitution_data()
            
            stats = {
                "file_info": self.get_file_info(),
                "structure": {
                    "total_chapters": 0,
                    "total_articles": 0,
                    "total_clauses": 0,
                    "total_sub_clauses": 0
                },
                "content": {
                    "has_preamble": "preamble" in data,
                    "preamble_length": len(data.get("preamble", "")),
                    "title": data.get("title", "")
                }
            }
            
            if "chapters" in data:
                chapters = data["chapters"]
                stats["structure"]["total_chapters"] = len(chapters)
                
                for chapter in chapters:
                    if "articles" in chapter:
                        articles = chapter["articles"]
                        stats["structure"]["total_articles"] += len(articles)
                        
                        for article in articles:
                            if "clauses" in article:
                                clauses = article["clauses"]
                                stats["structure"]["total_clauses"] += len(clauses)
                                
                                for clause in clauses:
                                    if "sub_clauses" in clause:
                                        sub_clauses = clause["sub_clauses"]
                                        stats["structure"]["total_sub_clauses"] += len(sub_clauses)
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting data statistics: {str(e)}")
            return {"error": str(e)}