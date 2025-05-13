import time
import logging
from typing import Callable, Dict, Optional, Tuple
from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from redis.asyncio import Redis
from fastapi.responses import JSONResponse

# Configure logging
logger = logging.getLogger(__name__)

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware for rate limiting API requests.
    
    This middleware implements a sliding window rate limiting algorithm
    with support for both Redis and in-memory storage.
    """
    
    def __init__(
        self, 
        app: ASGIApp,
        redis_client: Optional[Redis] = None,
        default_limit: int = 60,
        default_window: int = 60,
        path_limits: Optional[Dict[str, Tuple[int, int]]] = None,
        exclude_paths: Optional[set] = None
    ):
        """
        Initialize the rate limit middleware.
        
        Args:
            app: The ASGI application
            redis_client: Redis client for distributed rate limiting
            default_limit: Default requests per window
            default_window: Default time window in seconds
            path_limits: Dict mapping paths to (limit, window) tuples
            exclude_paths: Set of paths to exclude from rate limiting
        """
        super().__init__(app)
        self.redis = redis_client
        self.default_limit = default_limit
        self.default_window = default_window
        self.path_limits = path_limits or {}
        self.exclude_paths = exclude_paths or set()
        self.request_history = {}  # For in-memory rate limiting
        
        # Log configuration
        if self.redis:
            logger.info("Rate limiting middleware initialized with Redis backend")
        else:
            logger.info("Rate limiting middleware initialized with in-memory backend")
        
        logger.info(f"Default rate limit: {default_limit} requests per {default_window} seconds")
        for path, (limit, window) in self.path_limits.items():
            logger.info(f"Custom rate limit for {path}: {limit} requests per {window} seconds")
    
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        # Skip rate limiting for excluded paths
        path = request.url.path
        if self._should_skip(path):
            return await call_next(request)
        
        # Get client identifier (IP address or user ID if authenticated)
        client_id = self._get_client_id(request)
        
        # Get rate limit for this path
        limit, window = self._get_limits_for_path(path)
        
        # Check if rate limited
        is_limited, remaining = await self._check_rate_limit(client_id, path, limit, window)
        
        if is_limited:
            # Return rate limit exceeded response
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded. Please try again later."
                },
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + window)
                }
            )
        
        # Process the request
        response = await call_next(request)
        
        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + window)
        
        return response
    
    def _should_skip(self, path: str) -> bool:
        """Check if rate limiting should be skipped for this path"""
        return path in self.exclude_paths
    
    def _get_client_id(self, request: Request) -> str:
        """Get a unique identifier for the client"""
        # Use user ID if authenticated
        if hasattr(request.state, "user") and hasattr(request.state.user, "id"):
            return f"user:{request.state.user.id}"
        
        # Otherwise use IP address
        return f"ip:{request.client.host if request.client else 'unknown'}"
    
    def _get_limits_for_path(self, path: str) -> Tuple[int, int]:
        """Get rate limit and window for a specific path"""
        # Check for exact path match
        if path in self.path_limits:
            return self.path_limits[path]
        
        # Check for path prefix match
        for prefix, limits in self.path_limits.items():
            if prefix.endswith("*") and path.startswith(prefix[:-1]):
                return limits
        
        # Use default limits
        return self.default_limit, self.default_window
    
    async def _check_rate_limit(
        self, client_id: str, path: str, limit: int, window: int
    ) -> Tuple[bool, int]:
        """
        Check if a request is rate limited.
        
        Returns:
            Tuple of (is_limited, remaining_requests)
        """
        # Create a unique key for this client and path
        rate_key = f"ratelimit:{client_id}:{path}"
        
        if self.redis:
            # Use Redis for distributed rate limiting
            return await self._check_redis_rate_limit(rate_key, limit, window)
        else:
            # Use in-memory rate limiting
            return await self._check_memory_rate_limit(rate_key, limit, window)
    
    async def _check_redis_rate_limit(
        self, key: str, limit: int, window: int
    ) -> Tuple[bool, int]:
        """Check rate limit using Redis sliding window"""
        current_time = int(time.time())
        
        try:
            # Use Redis pipeline for atomic operations
            async with self.redis.pipeline() as pipe:
                # Add current timestamp to sorted set
                await pipe.zadd(key, {str(current_time): current_time})
                
                # Remove timestamps outside the window
                await pipe.zremrangebyscore(key, 0, current_time - window)
                
                # Count requests in the current window
                await pipe.zcard(key)
                
                # Set expiration on the key
                await pipe.expire(key, window * 2)
                
                # Execute pipeline
                results = await pipe.execute()
                
                # Get request count from results
                request_count = results[2]
                
                # Calculate remaining requests
                remaining = max(0, limit - request_count)
                
                # Check if rate limited
                return request_count > limit, remaining
                
        except Exception as e:
            logger.error(f"Redis rate limiting error: {str(e)}")
            # Fail open on Redis errors
            return False, limit
    
    async def _check_memory_rate_limit(
        self, key: str, limit: int, window: int
    ) -> Tuple[bool, int]:
        """Check rate limit using in-memory sliding window"""
        current_time = time.time()
        
        # Initialize history for this key if it doesn't exist
        if key not in self.request_history:
            self.request_history[key] = []
        
        # Clean up old entries for this key
        self.request_history[key] = [
            t for t in self.request_history[key] if current_time - t < window
        ]
        
        # Get current request count
        request_count = len(self.request_history[key])
        
        # Calculate remaining requests
        remaining = max(0, limit - request_count)
        
        # Check if rate limited
        if request_count >= limit:
            return True, 0
        
        # Add current timestamp to history
        self.request_history[key].append(current_time)
        
        return False, remaining - 1  # -1 because we just used one request
