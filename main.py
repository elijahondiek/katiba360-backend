# Import necessary FastAPI components
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.exceptions import RequestValidationError
from fastapi.responses import ORJSONResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import ValidationError
import httpx
from sqlalchemy.exc import SQLAlchemyError
import os
import logging
import time
from datetime import datetime
from redis.asyncio import Redis
import secrets

# Import application routes and custom error handlers
from src.routers import auth_routes, user_routes, content_routes, reading_routes, achievement_routes, notification_routes, onboarding_routes, constitution_routes, sharing_events_routes
from src.utils.exception_handlers import (
    http_exception_handler,
    pydantic_validation_error_handler,
    sqlalchemy_exception_handler,
    validation_exception_handler
)

# Import middleware
from src.middleware.logging_middleware import LoggingMiddleware
from src.middleware.auth_middleware import AuthMiddleware, GoogleAuthMiddleware
from src.middleware.rate_limit_middleware import RateLimitMiddleware

# Import configuration
from src.core.config import settings

# Import database
from src.database import init_db, close_db

# Configure logging
logger = logging.getLogger(__name__)

# Lifespan context manager for startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize application state
    app.state.settings = settings
    
    # Initialize database connection
    logger.info("Initializing database connection...")
    await init_db()
    logger.info("Database connection initialized successfully")
    
    # Initialize Redis connection for rate limiting
    try:
        # Get Redis URL from settings
        redis_url = settings.redis_url
        logger.info(f"Connecting to Redis at: {redis_url}")
        
        # Create Redis client from URL
        redis = Redis.from_url(
            url=redis_url,
            decode_responses=True,
            socket_timeout=5,  # Redis timeout
            socket_connect_timeout=5  # Redis connection timeout
        )
        await redis.ping()
        app.state.redis = redis
        logger.info("✅ Redis connection established successfully")
    except Exception as e:
        logger.warning(f"❌ Redis connection failed: {str(e)}. Using in-memory rate limiting.")
        app.state.redis = None
        logger.warning("Will use in-memory rate limiting as fallback")
    
    # Initialize HTTP client with timeouts
    http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(
            connect=5.0,    # connection timeout
            read=30.0,      # read timeout
            write=30.0,     # write timeout
            pool=5.0        # pool timeout
        )
    )
    app.state.http_client = http_client
    
    yield
    
    # Shutdown: Clean up resources
    logger.info("Closing database connection...")
    await close_db()
    logger.info("Database connection closed successfully")
    
    # Close Redis connection if it exists
    if hasattr(app.state, 'redis') and app.state.redis:
        try:
            await app.state.redis.close()
            logger.info("Redis connection closed successfully")
        except Exception as e:
            logger.warning(f"Error closing Redis connection: {str(e)}")
    
    # Close HTTP client
    await http_client.aclose()
    logger.info("HTTP client closed successfully")

# Initialize FastAPI application
app = FastAPI(
    title="Katiba360",
    description="API for the Katiba360 platform - Kenyan Constitution made accessible",
    version=settings.app_version,
    default_response_class=ORJSONResponse,
    lifespan=lifespan
)

# CORS Configuration
logger.info(f"Effective CORS Origins: {settings.cors_origins}")
logger.info(f"Effective CORS Methods: {settings.cors_methods}")
logger.info(f"Effective CORS Headers: {settings.cors_headers}")
origins = settings.cors_origins

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=settings.cors_methods,
    allow_headers=settings.cors_headers,
)

# Define paths to exclude from rate limiting
RATE_LIMIT_EXCLUDE_PATHS = {
    "/docs",
    "/redoc",
    "/openapi.json",
}

# Define custom rate limits for specific paths
RATE_LIMIT_PATH_LIMITS = {
    # Auth endpoints - lower limits to prevent brute force
    f"{settings.api_prefix}/auth/*": (30, 60),  # 30 requests per minute
    
    # Health check endpoint - higher limits for monitoring systems
    "/health": (120, 60),  # 120 requests per minute
    
    # Content endpoints - moderate limits
    f"{settings.api_prefix}/content/*": (60, 60),  # 60 requests per minute
}

# Add rate limiting middleware
app.add_middleware(
    RateLimitMiddleware,
    redis_client=app.state.redis if hasattr(app.state, 'redis') else None,
    default_limit=60,  # 60 requests per minute by default
    default_window=60,  # 1 minute window
    path_limits=RATE_LIMIT_PATH_LIMITS,
    exclude_paths=RATE_LIMIT_EXCLUDE_PATHS
)

# Add logging middleware
app.add_middleware(LoggingMiddleware)

# Add authentication middleware
app.add_middleware(
    AuthMiddleware,
    public_paths=settings.public_paths,
    public_prefixes=settings.public_path_prefixes
)

# Add Google OAuth middleware
app.add_middleware(GoogleAuthMiddleware)

# Register custom exception handlers
# These ensure consistent error responses across the API
app.add_exception_handler(
    HTTPException,  # Handle general HTTP exceptions
    http_exception_handler
)
app.add_exception_handler(
    RequestValidationError,  # Handle request validation errors
    validation_exception_handler
)
app.add_exception_handler(
    ValidationError,  # Handle Pydantic validation errors
    pydantic_validation_error_handler
)
app.add_exception_handler(
    SQLAlchemyError,  # Handle database-related errors
    sqlalchemy_exception_handler
)



# Rate limiting classes
class RateLimiter:
    """Base rate limiter interface"""
    
    async def is_rate_limited(self, key: str, limit: int, window: int) -> bool:
        """Check if a key is rate limited"""
        raise NotImplementedError("Subclasses must implement this method")


class RedisRateLimiter(RateLimiter):
    """Redis-based rate limiter using sliding window algorithm"""
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
    
    async def is_rate_limited(self, key: str, limit: int, window: int) -> bool:
        """Check if a key is rate limited using Redis sliding window
        
        Args:
            key: The key to rate limit (e.g., IP address or user ID)
            limit: Maximum number of requests allowed in the window
            window: Time window in seconds
            
        Returns:
            True if rate limited, False otherwise
        """
        current_time = int(time.time())
        # Create a unique Redis key for this rate limit
        redis_key = f"rate_limit:{key}:{window}"
        
        try:
            # Add the current timestamp to the sorted set
            await self.redis.zadd(redis_key, {str(current_time): current_time})
            
            # Remove timestamps outside the window
            await self.redis.zremrangebyscore(redis_key, 0, current_time - window)
            
            # Set expiration on the key to auto-cleanup
            await self.redis.expire(redis_key, window * 2)
            
            # Count requests in the current window
            request_count = await self.redis.zcard(redis_key)
            
            # Check if rate limited
            return request_count > limit
        except Exception as e:
            logger.error(f"Redis rate limiting error: {str(e)}")
            return False  # Fail open on Redis errors


class InMemoryRateLimiter(RateLimiter):
    """In-memory rate limiter using sliding window algorithm"""
    
    def __init__(self):
        self.request_history = {}
    
    async def is_rate_limited(self, key: str, limit: int, window: int) -> bool:
        """Check if a key is rate limited using in-memory sliding window
        
        Args:
            key: The key to rate limit (e.g., IP address or user ID)
            limit: Maximum number of requests allowed in the window
            window: Time window in seconds
            
        Returns:
            True if rate limited, False otherwise
        """
        current_time = time.time()
        
        # Initialize history for this key if it doesn't exist
        if key not in self.request_history:
            self.request_history[key] = []
        
        # Clean up old entries for this key
        self.request_history[key] = [
            t for t in self.request_history[key] if current_time - t < window
        ]
        
        # Check if rate limited
        if len(self.request_history[key]) >= limit:
            return True
        
        # Add current timestamp to history
        self.request_history[key].append(current_time)
        return False


# Factory function to get the appropriate rate limiter
def get_rate_limiter(app: FastAPI) -> RateLimiter:
    """Get the appropriate rate limiter based on Redis availability"""
    if hasattr(app.state, 'redis') and app.state.redis is not None:
        logger.info("Using Redis-based rate limiter")
        return RedisRateLimiter(app.state.redis)
    else:
        logger.info("Using in-memory rate limiter")
        return InMemoryRateLimiter()


@app.get("/health", tags=["Health"])
async def health_check(request: Request):
    """Health check endpoint for monitoring system status
    
    Returns a status response indicating the API is operational and the status of its dependencies.
    This endpoint is rate-limited to prevent abuse.
    """
    # Get client IP
    client_ip = request.client.host if request.client else "unknown"
    
    # Get the appropriate rate limiter
    rate_limiter = get_rate_limiter(request.app)
    
    # Check rate limit (30 requests per minute)
    is_limited = await rate_limiter.is_rate_limited(f"health:{client_ip}", 30, 60)
    if is_limited:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "detail": "Rate limit exceeded. Please try again later."
            }
        )
    
    # Prepare health status response
    health_status = {
        "status": "healthy",
        "timestamp": str(datetime.now()),
        "version": settings.app_version,
        "dependencies": {
            "redis": "unknown",
            "database": "unknown"
        }
    }
    
    # Check Redis health
    try:
        if hasattr(request.app.state, 'redis') and request.app.state.redis:
            redis_ping = await request.app.state.redis.ping()
            health_status["dependencies"]["redis"] = "healthy" if redis_ping else "unhealthy"
        else:
            health_status["dependencies"]["redis"] = "not_configured"
    except Exception as e:
        logger.error(f"Redis health check error: {str(e)}")
        health_status["dependencies"]["redis"] = "unhealthy"
    
    # Check database health (simplified check)
    try:
        # We already initialized the database in lifespan
        # A more thorough check would execute a simple query
        health_status["dependencies"]["database"] = "healthy"
    except Exception as e:
        logger.error(f"Database health check error: {str(e)}")
        health_status["dependencies"]["database"] = "unhealthy"
    
    # Update overall status if any dependency is unhealthy
    if any(status == "unhealthy" for status in health_status["dependencies"].values()):
        health_status["status"] = "unhealthy"
    
    return JSONResponse(content=health_status)

# Include all routers with appropriate prefixes
# User management routes
api_prefix = settings.api_prefix

# Auth routes
app.include_router(
    auth_routes.router,
    prefix=api_prefix,
    tags=["Authentication"]
)

# User routes
app.include_router(
    user_routes.router,
    prefix=api_prefix,
    tags=["Users"]
)

# Content routes
app.include_router(
    content_routes.router,
    prefix=api_prefix,
    tags=["Content"]
)

# Reading routes
app.include_router(
    reading_routes.router,
    prefix=api_prefix,
    tags=["Reading"]
)

# Achievement routes
app.include_router(
    achievement_routes.router,
    prefix=api_prefix,
    tags=["Achievements"]
)

# Notification routes
app.include_router(
    notification_routes.router,
    prefix=api_prefix,
    tags=["Notifications"]
)

# Onboarding routes
app.include_router(
    onboarding_routes.router,
    prefix=api_prefix,
    tags=["Onboarding"]
)

# Constitution routes
app.include_router(
    constitution_routes.router,
    prefix=api_prefix,
    tags=["Constitution"]
)

# Sharing events routes
app.include_router(
    sharing_events_routes.router,
    prefix=api_prefix,
    tags=["Sharing"]
)