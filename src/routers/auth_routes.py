from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional

from src.database import get_db
from src.services.auth_service import AuthService, get_auth_service
from src.services.user_service import UserService, get_user_service
from src.schemas.user_schemas import GoogleAuthRequest, TokenResponse, UserResponse, CompleteUserProfileResponse, RefreshTokenRequest
from src.utils.custom_utils import generate_response
from src.core.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

@router.get("/google")
async def google_oauth_init():
    """
    Initialize Google OAuth flow
    
    This endpoint redirects the user to the Google OAuth consent screen.
    """
    # Construct the Google OAuth URL
    from src.core.config import settings
    
    # Generate a state parameter for CSRF protection
    import secrets
    state = secrets.token_urlsafe(32)
    
    # Construct the authorization URL
    auth_url = (
        "https://accounts.google.com/o/oauth2/auth"
        f"?client_id={settings.google_client_id}"
        "&response_type=code"
        f"&redirect_uri={settings.google_redirect_uri}"
        "&scope=openid%20email%20profile"
        f"&state={state}"
        "&access_type=offline"
        "&prompt=consent"
    )
    
    # Redirect to the authorization URL
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=auth_url)

@router.post("/google", response_model=Dict[str, Any])
async def google_oauth_login(
    auth_data: GoogleAuthRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Authenticate with Google OAuth
    
    This endpoint handles the Google OAuth authentication flow.
    It exchanges the authorization code for tokens and creates or updates the user.
    """
    try:
        user, access_token = await auth_service.google_oauth_login(auth_data)
        
        # Create refresh token
        refresh_token = auth_service._create_refresh_token(data={"sub": str(user.id)})
        
        # Create response
        token_response = {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.access_token_expire_minutes * 60,
            "refresh_token": refresh_token,
            "user": UserResponse.from_orm(user)
        }
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="Authentication successful",
            customer_message="You have successfully logged in with Google",
            body=token_response
        )
    except HTTPException as e:
        return generate_response(
            status_code=e.status_code,
            response_message=e.detail,
            customer_message="Authentication failed",
            body=None
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=str(e),
            customer_message="An unexpected error occurred",
            body=None
        )

@router.post("/refresh-token", response_model=Dict[str, Any])
async def refresh_token(
    request: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Refresh an access token using a refresh token
    
    This endpoint refreshes an expired access token using a valid refresh token.
    """
    try:
        token_response = await auth_service.refresh_token(request.refresh_token)
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="Token refreshed successfully",
            customer_message="Your session has been refreshed",
            body=token_response.dict()
        )
    except HTTPException as e:
        return generate_response(
            status_code=e.status_code,
            response_message=e.detail,
            customer_message="Failed to refresh token",
            body=None
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=str(e),
            customer_message="An unexpected error occurred",
            body=None
        )

@router.post("/logout", response_model=Dict[str, Any])
async def logout(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Log out a user
    
    This endpoint logs out a user by invalidating their OAuth sessions.
    """
    try:
        user = request.state.user
        await auth_service.logout(user)
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="Logout successful",
            customer_message="You have been logged out successfully",
            body=None
        )
    except HTTPException as e:
        return generate_response(
            status_code=e.status_code,
            response_message=e.detail,
            customer_message="Logout failed",
            body=None
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=str(e),
            customer_message="An unexpected error occurred",
            body=None
        )

@router.get("/me", response_model=Dict[str, Any])
async def get_current_user(
    request: Request,
    user_service: UserService = Depends(get_user_service)
):
    """
    Get the current authenticated user
    
    This endpoint returns the profile of the currently authenticated user.
    """
    try:
        user = request.state.user
        user_with_profile = await user_service.get_user_complete_profile(user.id)
        
        return generate_response(
            status_code=status.HTTP_200_OK,
            response_message="User profile retrieved successfully",
            customer_message="Your profile has been retrieved",
            body=CompleteUserProfileResponse.from_orm(user_with_profile).dict()
        )
    except HTTPException as e:
        return generate_response(
            status_code=e.status_code,
            response_message=e.detail,
            customer_message="Failed to retrieve profile",
            body=None
        )
    except Exception as e:
        return generate_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            response_message=str(e),
            customer_message="An unexpected error occurred",
            body=None
        )
