from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, BackgroundTasks, Body, Request
from typing import Dict, List, Optional, Any, Union
import logging
from pydantic import BaseModel, Field, UUID4
import time
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.services.reading_progress_service import ReadingProgressService, get_reading_progress_service

from ..services.constitution import ConstitutionOrchestrator
from ..utils.custom_utils import generate_response
from ..utils.cache import CacheManager, HOUR, DAY

router = APIRouter(prefix="/constitution", tags=["Constitution"])
logger = logging.getLogger(__name__)

# Dependency to get cache manager
async def get_cache_manager():
    # Get Redis client from the application settings
    from redis.asyncio import Redis
    from ..utils.cache import CacheManager
    from ..core.config import settings
    
    # Get Redis client using the URL from settings
    redis_client = Redis.from_url(settings.redis_url)
    
    # Create cache manager
    cache_manager = CacheManager(redis_client, prefix="katiba360")
    
    try:
        yield cache_manager
    finally:
        await redis_client.close()

# Dependency to get constitution service
def get_constitution_service(
    cache: CacheManager = Depends(get_cache_manager),
    db: AsyncSession = Depends(get_db)
):
    # Extract Redis client from cache manager
    redis_client = cache.redis
    return ConstitutionOrchestrator(redis_client, db)

# Pydantic models for request validation

class BookmarkRequest(BaseModel):
    bookmark_type: str = Field(..., description="Type of bookmark (chapter, article)")
    reference: str = Field(..., description="Reference (e.g., '1' for chapter 1, '1.2' for article 2 in chapter 1)")
    title: str = Field(..., description="Title of the bookmarked item")
    
class ReadingProgressRequest(BaseModel):
    item_type: str = Field(..., description="Type of item (chapter, article)")
    reference: str = Field(..., description="Reference (e.g., '1' for chapter 1, '1.2' for article 2 in chapter 1)")
    read_time_minutes: float = Field(1.0, description="Time spent reading in minutes (supports decimals)")
    is_incremental: Optional[bool] = Field(True, description="Whether this is incremental reading time")


@router.get("")
async def get_constitution_overview(
    background_tasks: BackgroundTasks,
    request: Request,
    service: ConstitutionOrchestrator = Depends(get_constitution_service)
):
    """
    Get an overview of the constitution including metadata and structure.
    """
    try:
        start_time = time.time()
        
        # Get overview with background caching
        overview = await service.get_constitution_overview(background_tasks)
        
        response_time = time.time() - start_time
        cache_status = "hit" if response_time < 0.1 else "miss"
        
        return generate_response(
            status_code=200,
            response_message="Constitution overview retrieved successfully",
            customer_message="Constitution overview retrieved successfully",
            body={
                "overview": overview,
                "metadata": {
                    "response_time_ms": round(response_time * 1000, 2),
                    "cache_status": cache_status
                }
            }
        )
    except Exception as e:
        logger.error(f"Error retrieving constitution overview: {e}")
        return generate_response(
            status_code=500,
            response_message=f"Error retrieving constitution overview: {str(e)}",
            customer_message="An error occurred while retrieving the constitution overview",
            body=None
        )


@router.get("/chapters")
async def get_all_chapters(
    background_tasks: BackgroundTasks,
    request: Request,
    limit: Optional[int] = Query(None, description="Maximum number of chapters to return"),
    offset: Optional[int] = Query(0, description="Number of chapters to skip"),
    fields: Optional[str] = Query(None, description="Comma-separated list of fields to include"),
    service: ConstitutionOrchestrator = Depends(get_constitution_service)
):
    """
    Get all chapters with pagination support.
    """
    try:
        start_time = time.time()
        
        # Parse fields if provided
        fields_list = fields.split(",") if fields else None
        
        # Get chapters with background caching
        chapters_data = await service.get_all_chapters(
            background_tasks=background_tasks,
            limit=limit, 
            offset=offset, 
            fields=fields_list
        )
        
        response_time = time.time() - start_time
        cache_status = "hit" if response_time < 0.1 else "miss"
        
        return generate_response(
            status_code=200,
            response_message="Chapters retrieved successfully",
            customer_message="Chapters retrieved successfully",
            body={
                **chapters_data,
                "metadata": {
                    "response_time_ms": round(response_time * 1000, 2),
                    "cache_status": cache_status
                }
            }
        )
    except Exception as e:
        logger.error(f"Error retrieving chapters: {e}")
        return generate_response(
            status_code=500,
            response_message=f"Error retrieving chapters: {str(e)}",
            customer_message="An error occurred while retrieving the chapters",
            body=None
        )


@router.get("/chapters/{chapter_num}")
async def get_chapter_by_number(
    background_tasks: BackgroundTasks,
    request: Request,
    chapter_num: int = Path(..., description="Chapter number to retrieve"),
    service: ConstitutionOrchestrator = Depends(get_constitution_service)
):
    """
    Get a specific chapter by its number.
    """
    try:
        start_time = time.time()
        
        # Get chapter with background caching
        chapter = await service.get_chapter_by_number(chapter_num, background_tasks)
        
        if not chapter:
            return generate_response(
                status_code=404,
                response_message=f"Chapter {chapter_num} not found",
                customer_message=f"Chapter {chapter_num} not found",
                body=None
            )
        
        response_time = time.time() - start_time
        cache_status = "hit" if response_time < 0.1 else "miss"
        
        return generate_response(
            status_code=200,
            response_message=f"Chapter {chapter_num} retrieved successfully",
            customer_message=f"Chapter {chapter_num} retrieved successfully",
            body={
                "chapter": chapter,
                "metadata": {
                    "response_time_ms": round(response_time * 1000, 2),
                    "cache_status": cache_status
                }
            }
        )
    except Exception as e:
        logger.error(f"Error retrieving chapter {chapter_num}: {e}")
        return generate_response(
            status_code=500,
            response_message=f"Error retrieving chapter: {str(e)}",
            customer_message="An error occurred while retrieving the chapter",
            body=None
        )


@router.get("/chapters/{chapter_number}/articles/{article_number}")
async def get_article_by_number(
    background_tasks: BackgroundTasks,
    request: Request,
    chapter_number: int = Path(..., description="The chapter number", ge=1),
    article_number: int = Path(..., description="The article number", ge=1),
    service: ConstitutionOrchestrator = Depends(get_constitution_service)
):
    """
    Get a specific article by its chapter and article number.
    """
    try:
        start_time = time.time()
        
        # Get article with background caching
        article = await service.get_article_by_number(chapter_number, article_number, background_tasks)
        
        if not article:
            return generate_response(
                status_code=404,
                response_message=f"Article {article_number} in Chapter {chapter_number} not found",
                customer_message=f"Article {article_number} in Chapter {chapter_number} not found",
                body=None
            )
        
        response_time = time.time() - start_time
        cache_status = "hit" if response_time < 0.1 else "miss"
        
        return generate_response(
            status_code=200,
            response_message=f"Article {article_number} in Chapter {chapter_number} retrieved successfully",
            customer_message=f"Article {article_number} in Chapter {chapter_number} retrieved successfully",
            body={
                "article": article,
                "metadata": {
                    "response_time_ms": round(response_time * 1000, 2),
                    "cache_status": cache_status
                }
            }
        )
    except Exception as e:
        logger.error(f"Error retrieving article: {e}")
        return generate_response(
            status_code=500,
            response_message=f"Error retrieving article: {str(e)}",
            customer_message="An error occurred while retrieving the article",
            body=None
        )


@router.get("/search")
async def search_constitution(
    background_tasks: BackgroundTasks,
    request: Request,
    query: str = Query(..., description="The search query"),
    chapter: Optional[int] = Query(None, description="Filter by chapter number"),
    article: Optional[int] = Query(None, description="Filter by article number"),
    limit: Optional[int] = Query(10, description="Maximum number of results to return"),
    offset: Optional[int] = Query(0, description="Number of results to skip"),
    highlight: bool = Query(True, description="Whether to highlight matches in the results"),
    no_cache: bool = Query(False, description="Bypass cache for testing"),
    service: ConstitutionOrchestrator = Depends(get_constitution_service)
):
    """
    Search the constitution for a specific query with optional filters.
    """
    try:
        start_time = time.time()
        
        # Search with background caching
        # Create filters dict from chapter and article parameters
        filters = {}
        if chapter is not None:
            filters["chapter"] = chapter
        if article is not None:
            filters["article"] = article
            
        # Force a cache miss for testing
        # Force a cache miss for testing
        logger.info(f"Searching for '{query}' with no_cache={no_cache}")
        
        search_results = await service.search_constitution(
            query=query,
            filters=filters,
            limit=limit,
            offset=offset,
            highlight=highlight,
            background_tasks=background_tasks,
            no_cache=no_cache
        )
        
        response_time = time.time() - start_time
        # Always report miss if no_cache is True
        cache_status = "miss" if no_cache else ("hit" if response_time < 0.1 else "miss")
        
        return generate_response(
            status_code=200,
            response_message="Search completed successfully",
            customer_message="Search completed successfully",
            body={
                **search_results,
                "metadata": {
                    "response_time_ms": round(response_time * 1000, 2),
                    "cache_status": cache_status,
                    "query": query,
                    "filters": {
                        "chapter": chapter,
                        "article": article
                    }
                }
            }
        )
    except Exception as e:
        logger.error(f"Error performing search: {e}")
        return generate_response(
            status_code=500,
            response_message=f"Error performing search: {str(e)}",
            customer_message="An error occurred while performing the search",
            body=None
        )


# Advanced search endpoint removed


@router.get("/related/{reference}")
async def get_related_articles(
    background_tasks: BackgroundTasks,
    request: Request,
    reference: str = Path(..., description="The article reference (e.g., '1.2' for Chapter 1, Article 2)"),
    service: ConstitutionOrchestrator = Depends(get_constitution_service)
):
    # TODO: Enhance related articles functionality to use semantic similarity or explicit cross-references
    #       instead of just finding articles in the same chapter. Implement a more sophisticated relevance
    #       calculation based on content similarity rather than just "same_chapter".
    """
    Find articles related to a specific article reference.
    """
    try:
        start_time = time.time()
        
        # Get related articles with background caching
        related_articles = await service.get_related_articles(reference, background_tasks)
        
        response_time = time.time() - start_time
        cache_status = "hit" if response_time < 0.1 else "miss"
        
        return generate_response(
            status_code=200,
            response_message="Related articles retrieved successfully",
            customer_message="Related articles retrieved successfully",
            body={
                "related_articles": related_articles,
                "metadata": {
                    "response_time_ms": round(response_time * 1000, 2),
                    "cache_status": cache_status,
                    "reference": reference
                }
            }
        )
    except Exception as e:
        logger.error(f"Error retrieving related articles: {e}")
        return generate_response(
            status_code=500,
            response_message=f"Error retrieving related articles: {str(e)}",
            customer_message="An error occurred while retrieving related articles",
            body=None
        )


@router.get("/popular")
async def get_popular_sections(
    background_tasks: BackgroundTasks,
    request: Request,
    timeframe: str = Query("week", description="Timeframe for popularity (day, week, month, all)"),
    service: ConstitutionOrchestrator = Depends(get_constitution_service)
):
    """
    Get popular/trending sections of the constitution.
    """
    try:
        start_time = time.time()
        
        # Get popular sections with background caching
        popular_sections = await service.get_popular_sections(timeframe, 5, background_tasks)
        
        response_time = time.time() - start_time
        cache_status = "hit" if response_time < 0.1 else "miss"
        
        return generate_response(
            status_code=200,
            response_message="Popular sections retrieved successfully",
            customer_message="Popular sections retrieved successfully",
            body={
                "popular_sections": popular_sections,
                "metadata": {
                    "response_time_ms": round(response_time * 1000, 2),
                    "cache_status": cache_status,
                    "timeframe": timeframe,
                    "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                }
            }
        )
    except Exception as e:
        logger.error(f"Error retrieving popular sections: {e}")
        return generate_response(
            status_code=500,
            response_message=f"Error retrieving popular sections: {str(e)}",
            customer_message="An error occurred while retrieving popular sections",
            body=None
        )


@router.post("/reload")
# TODO: Add proper authentication to this endpoint to restrict access to admin users only
async def reload_constitution_data(
    background_tasks: BackgroundTasks,
    request: Request,
    service: ConstitutionOrchestrator = Depends(get_constitution_service)
):
    """
    Force reload of the constitution data and clear cache.
    This endpoint would typically be protected by admin authentication.
    """
    try:
        start_time = time.time()
        
        # Force reload of the constitution data and clear cache
        await service.reload_constitution_data(background_tasks)
        
        response_time = time.time() - start_time
        
        return generate_response(
            status_code=200,
            response_message="Constitution data reloaded and cache cleared successfully",
            customer_message="Constitution data reloaded and cache cleared successfully",
            body={
                "metadata": {
                    "response_time_ms": round(response_time * 1000, 2),
                    "reloaded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                }
            }
        )
    except Exception as e:
        logger.error(f"Error reloading constitution data: {e}")
        return generate_response(
            status_code=500,
            response_message=f"Error reloading constitution data: {str(e)}",
            customer_message="An error occurred while reloading the constitution data",
            body=None
        )


# User-specific routes
@router.get("/user/{user_id}/bookmarks")
async def get_user_bookmarks(
    background_tasks: BackgroundTasks,
    request: Request,
    user_id: UUID4 = Path(..., description="User ID"),
    service: ConstitutionOrchestrator = Depends(get_constitution_service)
):
    """
    Get a user's bookmarks.
    """
    try:
        start_time = time.time()
        
        # Get bookmarks with background caching
        bookmarks = await service.get_user_bookmarks(str(user_id), background_tasks)
        
        response_time = time.time() - start_time
        cache_status = "hit" if response_time < 0.1 else "miss"
        
        return generate_response(
            status_code=200,
            response_message="User bookmarks retrieved successfully",
            customer_message="Your bookmarks were retrieved successfully",
            body={
                "bookmarks": bookmarks,
                "metadata": {
                    "response_time_ms": round(response_time * 1000, 2),
                    "cache_status": cache_status,
                    "user_id": str(user_id)
                }
            }
        )
    except Exception as e:
        logger.error(f"Error retrieving user bookmarks: {e}")
        return generate_response(
            status_code=500,
            response_message=f"Error retrieving user bookmarks: {str(e)}",
            customer_message="An error occurred while retrieving your bookmarks",
            body=None
        )


@router.post("/user/{user_id}/bookmarks")
async def add_user_bookmark(
    background_tasks: BackgroundTasks,
    request: Request,
    user_id: UUID4 = Path(..., description="User ID"),
    bookmark: BookmarkRequest = Body(...),
    service: ConstitutionOrchestrator = Depends(get_constitution_service)
):
    """
    Add a bookmark for a user.
    """
    try:
        start_time = time.time()
        
        # Add bookmark with background caching
        result = await service.add_user_bookmark(
            str(user_id), 
            bookmark.bookmark_type,
            bookmark.reference,
            bookmark.title,
            background_tasks
        )
        
        response_time = time.time() - start_time
        
        # Check if bookmark already exists
        if not result.get("success") and result.get("message") == "Bookmark already exists":
            return generate_response(
                status_code=409,  # Conflict status code
                response_message="Bookmark already exists",
                customer_message="This bookmark already exists in your collection",
                body={
                    "metadata": {
                        "response_time_ms": round(response_time * 1000, 2),
                        "user_id": str(user_id),
                        "bookmark_type": bookmark.bookmark_type,
                        "reference": bookmark.reference
                    }
                }
            )
        
        return generate_response(
            status_code=200,
            response_message="Bookmark added successfully",
            customer_message="Bookmark added successfully",
            body={
                "bookmark": result.get("bookmark"),
                "metadata": {
                    "response_time_ms": round(response_time * 1000, 2),
                    "user_id": str(user_id)
                }
            }
        )
    except Exception as e:
        logger.error(f"Error adding user bookmark: {e}")
        return generate_response(
            status_code=500,
            response_message=f"Error adding user bookmark: {str(e)}",
            customer_message="An error occurred while adding your bookmark",
            body=None
        )


@router.delete("/user/{user_id}/bookmarks/{bookmark_id}")
async def remove_user_bookmark(
    background_tasks: BackgroundTasks,
    request: Request,
    user_id: UUID4 = Path(..., description="User ID"),
    bookmark_id: str = Path(..., description="Bookmark ID"),
    service: ConstitutionOrchestrator = Depends(get_constitution_service)
):
    """
    Remove a bookmark for a user.
    """
    try:
        start_time = time.time()
        
        # Remove bookmark with background caching
        result = await service.remove_user_bookmark(str(user_id), bookmark_id, background_tasks)
        
        response_time = time.time() - start_time
        
        # Check if bookmark was found and removed
        if not result.get("success"):
            return generate_response(
                status_code=404,
                response_message="Bookmark not found",
                customer_message="The bookmark you tried to remove could not be found",
                body=None
            )
        
        return generate_response(
            status_code=200,
            response_message="Bookmark removed successfully",
            customer_message="Bookmark removed successfully",
            body={
                "metadata": {
                    "response_time_ms": round(response_time * 1000, 2),
                    "user_id": str(user_id),
                    "bookmark_id": bookmark_id
                }
            }
        )
    except Exception as e:
        logger.error(f"Error removing user bookmark: {e}")
        return generate_response(
            status_code=500,
            response_message=f"Error removing user bookmark: {str(e)}",
            customer_message="An error occurred while removing your bookmark",
            body=None
        )


@router.get("/user/{user_id}/progress")
async def get_user_reading_progress(
    background_tasks: BackgroundTasks,
    request: Request,
    user_id: UUID4 = Path(..., description="User ID"),
    reading_service: ReadingProgressService = Depends(get_reading_progress_service)
):
    """
    Get a user's reading progress.
    """
    try:
        start_time = time.time()
        
        # Get reading progress with background caching
        progress = await reading_service.get_user_reading_progress(str(user_id), background_tasks)
        
        response_time = time.time() - start_time
        cache_status = "hit" if response_time < 0.1 else "miss"
        
        return generate_response(
            status_code=200,
            response_message="Reading progress retrieved successfully",
            customer_message="Your reading progress was retrieved successfully",
            body={
                "progress": progress,
                "metadata": {
                    "response_time_ms": round(response_time * 1000, 2),
                    "cache_status": cache_status,
                    "user_id": str(user_id)
                }
            }
        )
    except Exception as e:
        logger.error(f"Error retrieving user reading progress: {e}")
        return generate_response(
            status_code=500,
            response_message=f"Error retrieving user reading progress: {str(e)}",
            customer_message="An error occurred while retrieving your reading progress",
            body=None
        )


@router.post("/user/{user_id}/progress")
async def update_user_reading_progress(
    background_tasks: BackgroundTasks,
    request: Request,
    user_id: UUID4 = Path(..., description="User ID"),
    progress: ReadingProgressRequest = Body(...),
    reading_service: ReadingProgressService = Depends(get_reading_progress_service)
):
    """
    Update a user's reading progress.
    """
    try:
        start_time = time.time()
        
        # Update reading progress with background caching
        result = await reading_service.update_user_reading_progress(
            str(user_id),
            progress.item_type,
            progress.reference,
            progress.read_time_minutes,
            background_tasks
        )
        
        response_time = time.time() - start_time
        
        return generate_response(
            status_code=200,
            response_message="Reading progress updated successfully",
            customer_message="Your reading progress was updated successfully",
            body={
                "progress": result,
                "metadata": {
                    "response_time_ms": round(response_time * 1000, 2),
                    "user_id": str(user_id)
                }
            }
        )
    except Exception as e:
        logger.error(f"Error updating user reading progress: {e}")
        return generate_response(
            status_code=500,
            response_message=f"Error updating user reading progress: {str(e)}",
            customer_message="An error occurred while updating your reading progress",
            body=None
        )
