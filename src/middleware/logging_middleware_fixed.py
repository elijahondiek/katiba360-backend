import time
from typing import Callable, Dict, Any, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from src.utils.logging.error_logger import error_logger
from src.utils.logging.activity_logger import logger_instance as activity_logger
from src.services.auth_service import AuthService
from src.database import SessionFactory

# Constants
BEARER_PREFIX = "Bearer "


class ErrorLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging all errors that occur during request processing.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        try:
            # Process the request
            response = await call_next(request)
            return response
            
        except Exception as e:
            # Log the error
            user_id = await self._get_user_id(request)
            await error_logger.log_error(
                error=e,
                request=request,
                user_id=user_id,
                additional_context=await self._get_additional_context(request)
            )
            
            # Re-raise the exception to be handled by exception handlers
            raise
    
    async def _get_user_id(self, request: Request) -> Optional[str]:
        """
        Extract user ID from request if available.
        
        Args:
            request: The FastAPI request object
            
        Returns:
            User ID if found, None otherwise
        """
        # Try to get user ID from request state
        if hasattr(request.state, "user") and hasattr(request.state.user, "id"):
            return str(request.state.user.id)
        
        # Try to get user ID from authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith(BEARER_PREFIX):
            token = auth_header.replace(BEARER_PREFIX, "")
            try:
                # Create a database session
                db = SessionFactory()
                # Create an auth service
                auth_service = AuthService(db)
                # Get the user from the token
                user = await auth_service.get_current_user(token)
                # Close the database session
                await db.close()
                
                if user:
                    return str(user.id)
            except Exception:
                # If any error occurs, just return None
                pass
        
        return None
    
    async def _get_additional_context(self, request: Request) -> Dict[str, Any]:
        """
        Get additional context for error logging.
        
        Args:
            request: The FastAPI request object
            
        Returns:
            Dictionary with additional context
        """
        context = {}
        
        # Add user agent
        context["user_agent"] = request.headers.get("User-Agent")
        
        # Add referer
        context["referer"] = request.headers.get("Referer")
        
        # Add content type
        context["content_type"] = request.headers.get("Content-Type")
        
        # Add accept language
        context["accept_language"] = request.headers.get("Accept-Language")
        
        return context


class ActivityLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging all user activity in a narrative format.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        # Skip logging for certain paths
        if self._should_skip_logging(request.url.path):
            return await call_next(request)
        
        # Start timer
        start_time = time.time()
        
        # Process the request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log the activity
        await self._log_activity(request, response, process_time)
        
        return response
    
    def _should_skip_logging(self, path: str) -> bool:
        """
        Determine if logging should be skipped for this path.
        
        Args:
            path: Request path
            
        Returns:
            True if logging should be skipped, False otherwise
        """
        # Skip logging for static files
        if path.startswith("/static/"):
            return True
        
        # Skip logging for health checks
        if path == "/health":
            return True
        
        # Skip logging for docs
        if path in ["/docs", "/redoc", "/openapi.json"]:
            return True
        
        return False
    
    async def _log_activity(
        self, request: Request, response: Response, process_time: float
    ) -> None:
        """
        Log the request activity.
        
        Args:
            request: The FastAPI request object
            response: The response object
            process_time: Request processing time in seconds
        """
        # Get user ID if available
        user_id = await self._get_user_id(request)
        
        # Create a narrative description
        narrative = self._create_narrative(request, response, user_id)
        
        # Log the activity
        await activity_logger.log_activity(
            message=narrative,
            user_id=user_id,
            activity_type="api_request",
            metadata={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "process_time_ms": round(process_time * 1000, 2),
                "query_params": dict(request.query_params),
                "client_host": request.client.host if request.client else None,
                "user_agent": request.headers.get("User-Agent")
            }
        )
    
    async def _get_user_id(self, request: Request) -> Optional[str]:
        """
        Extract user ID from request if available.
        
        Args:
            request: The FastAPI request object
            
        Returns:
            User ID if found, None otherwise
        """
        # Try to get user ID from request state
        if hasattr(request.state, "user") and hasattr(request.state.user, "id"):
            return str(request.state.user.id)
        
        # Try to get user ID from authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith(BEARER_PREFIX):
            token = auth_header.replace(BEARER_PREFIX, "")
            try:
                # Create a database session
                db = SessionFactory()
                # Create an auth service
                auth_service = AuthService(db)
                # Get the user from the token
                user = await auth_service.get_current_user(token)
                # Close the database session
                await db.close()
                
                if user:
                    return str(user.id)
            except Exception:
                # If any error occurs, just return None
                pass
        
        return None
    
    def _create_narrative(
        self, request: Request, response: Response, user_id: Optional[str]
    ) -> str:
        """
        Create a narrative description of the request.
        
        Args:
            request: The FastAPI request object
            response: The response object
            user_id: User ID if available
            
        Returns:
            Narrative description
        """
        # Base narrative
        narrative = f"User made a {request.method} request to {request.url.path}"
        
        # Add user ID if available
        if user_id:
            narrative = f"User [{user_id}] made a {request.method} request to {request.url.path}"
        
        # Add query parameters if any
        if request.query_params:
            params_str = ", ".join(f"{k}={v}" for k, v in request.query_params.items())
            narrative += f" with parameters: {params_str}"
        
        # Add response status
        if 200 <= response.status_code < 300:
            narrative += f" and received a successful response ({response.status_code})"
        elif 400 <= response.status_code < 500:
            narrative += f" but had a client error ({response.status_code})"
        elif 500 <= response.status_code < 600:
            narrative += f" but encountered a server error ({response.status_code})"
        else:
            narrative += f" and received a {response.status_code} response"
        
        return narrative


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware for adding a unique request ID to each request.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        # Generate a unique request ID
        import uuid
        request_id = str(uuid.uuid4())
        
        # Add request ID to request state
        request.state.request_id = request_id
        
        # Process the request
        response = await call_next(request)
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Combined middleware for logging errors and activity.
    This middleware combines the functionality of ErrorLoggingMiddleware and ActivityLoggingMiddleware.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.error_middleware = ErrorLoggingMiddleware(app)
        self.activity_middleware = ActivityLoggingMiddleware(app)
    
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        # Start timer
        start_time = time.time()
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Skip activity logging for certain paths
            if not self.activity_middleware._should_skip_logging(request.url.path):
                # Calculate processing time
                process_time = time.time() - start_time
                # Log the activity
                await self.activity_middleware._log_activity(request, response, process_time)
            
            return response
            
        except Exception as e:
            # Log the error
            user_id = await self.error_middleware._get_user_id(request)
            await error_logger.log_error(
                error=e,
                request=request,
                user_id=user_id,
                additional_context=await self.error_middleware._get_additional_context(request)
            )
            
            # Re-raise the exception to be handled by exception handlers
            raise
