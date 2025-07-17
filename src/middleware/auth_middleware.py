from typing import Callable, Dict, Any, Optional, List
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from src.services.auth_service import AuthService
from src.database import SessionFactory
from src.utils.logging.activity_logger import logger_instance as activity_logger
from src.utils.logging.error_logger import error_logger
from src.models.user_models import User


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware for handling authentication.
    """
    
    def __init__(
        self, 
        app: ASGIApp, 
        public_paths: Optional[List[str]] = None,
        public_prefixes: Optional[List[str]] = None
    ):
        super().__init__(app)
        self.public_paths = public_paths or []
        self.public_prefixes = public_prefixes or []
    
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        # Skip authentication for public paths
        if self._is_public_path(request.url.path):
            return await call_next(request)
        
        # Skip authentication for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Get authorization header
        auth_header = request.headers.get("Authorization")
        
        # If no authorization header, return 401
        if not auth_header or not auth_header.startswith("Bearer "):
            return self._unauthorized_response("Missing or invalid authorization header")
        
        # Extract token
        token = auth_header.replace("Bearer ", "")
        
        try:
            # Create a database session
            db = SessionFactory()
            
            # Create an auth service
            auth_service = AuthService(db)
            
            # Validate token and get user
            user = await auth_service.get_current_user(token)
            
            # Add user to request state
            request.state.user = user
            
            # Process the request
            response = await call_next(request)
            
            # Close the database session
            await db.close()
            
            return response
            
        except HTTPException as e:
            # Close the database session if it exists
            if 'db' in locals():
                await db.close()
            
            # Log the authentication error
            await activity_logger.log_activity(
                message=f"Authentication failed: {e.detail}",
                activity_type="auth_failure",
                metadata={
                    "path": request.url.path,
                    "method": request.method,
                    "status_code": e.status_code,
                    "detail": e.detail
                }
            )
            
            # Return the appropriate error response
            return self._unauthorized_response(e.detail)
            
        except Exception as e:
            # Close the database session if it exists
            if 'db' in locals():
                await db.close()
            
            # Log the error
            await error_logger.log_error(
                error=e,
                request=request,
                additional_context={"middleware": "AuthMiddleware"}
            )
            
            # Return a generic error response
            return Response(
                content='{"detail":"An internal server error occurred"}',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                media_type="application/json"
            )
    
    def _is_public_path(self, path: str) -> bool:
        """
        Check if a path is public (doesn't require authentication).
        
        Args:
            path: Request path
            
        Returns:
            True if the path is public, False otherwise
        """
        # Check exact path matches
        if path in self.public_paths:
            return True
        
        # Check path prefixes
        for prefix in self.public_prefixes:
            if path.startswith(prefix):
                return True
        
        return False
    
    def _unauthorized_response(self, detail: str) -> Response:
        """
        Create an unauthorized response.
        
        Args:
            detail: Error detail
            
        Returns:
            Response object
        """
        return Response(
            content=f'{{"detail":"{detail}"}}',
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={
                "WWW-Authenticate": "Bearer",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization",
                "Access-Control-Allow-Credentials": "true"
            },
            media_type="application/json"
        )


class GoogleAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware for refreshing Google OAuth tokens when needed.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        # Process the request first
        response = await call_next(request)
        
        # Check if user is authenticated and using Google OAuth
        if hasattr(request.state, "user") and request.state.user:
            user = request.state.user
            
            # Only proceed for Google OAuth users
            if user.auth_provider == "google":
                # Create a new database session to avoid detached instance errors
                db = SessionFactory()
                
                # Get a fresh instance of the user with relationships loaded
                query = select(User).options(
                    selectinload(User.oauth_sessions)
                ).where(User.id == user.id)
                
                result = await db.execute(query)
                fresh_user = result.scalars().first()
                
                # Check if user has an active OAuth session
                if fresh_user and fresh_user.oauth_sessions and any(s.is_active for s in fresh_user.oauth_sessions):
                    # Get the active session
                    active_session = next((s for s in fresh_user.oauth_sessions if s.is_active), None)
                    
                    if active_session:
                        # Check if token is about to expire (within 5 minutes)
                        from datetime import datetime, timedelta, timezone
                        
                        if (active_session.token_expires_at and 
                            active_session.token_expires_at <= datetime.now(timezone.utc) + timedelta(minutes=5)):
                            try:
                                # Create a database session
                                db = SessionFactory()
                                
                                # Create an auth service
                                auth_service = AuthService(db)
                                
                                # Refresh the token
                                await auth_service.refresh_google_token(active_session)
                                
                                # Close the database session
                                await db.close()
                                
                                # Log the refresh
                                await activity_logger.log_activity(
                                    message=f"Refreshed Google OAuth token for user",
                                    user_id=str(user.id),
                                    activity_type="token_refresh",
                                    metadata={
                                        "provider": "google",
                                        "session_id": str(active_session.id)
                                    }
                                )
                                
                            except Exception as e:
                                # Close the database session if it exists
                                if 'db' in locals():
                                    await db.close()
                                
                                # Log the error
                                await error_logger.log_error(
                                    error=e,
                                    request=request,
                                    user_id=str(user.id),
                                    additional_context={
                                        "middleware": "GoogleAuthMiddleware",
                                        "action": "token_refresh"
                                    }
                                )
        
        return response
