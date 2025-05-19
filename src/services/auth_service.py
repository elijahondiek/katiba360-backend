from typing import Optional, Dict, Any, Tuple
import uuid
from datetime import datetime, timedelta
import jwt
from jwt.exceptions import PyJWTError, ExpiredSignatureError
from fastapi import HTTPException, status, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import httpx
from src.database import get_db
from src.models.user_models import User, OAuthSession, UserPreference, OnboardingProgress
from src.schemas.user_schemas import UserCreate, GoogleAuthRequest, TokenResponse
from src.core.config import settings
from src.utils.logging.activity_logger import logger_instance

class AuthService:
    """
    Service for handling authentication-related operations
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.activity_logger = logger_instance
    
    # Direct user registration removed as we're using Google OAuth exclusively
    
    # Direct user authentication removed as we're using Google OAuth exclusively
    
    async def google_oauth_login(self, auth_data: GoogleAuthRequest) -> Tuple[User, str]:
        """
        Handle Google OAuth authentication
        
        Args:
            auth_data: Google auth data with code and redirect_uri
            
        Returns:
            Tuple of (user, access_token)
            
        Raises:
            HTTPException: If Google authentication fails
        """
        try:
            # Exchange code for tokens with improved security
            token_data = await self._exchange_google_code(
                code=auth_data.code, 
                redirect_uri=auth_data.redirect_uri,
                state=auth_data.state
            )
            
            if not token_data.get("access_token"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid token response from Google"
                )
            
            # Get user info from Google
            user_info = await self._get_google_user_info(token_data["access_token"])
            
            # Validate required user info
            if not user_info.get("id") or not user_info.get("email"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Incomplete user information from Google"
                )
            
            # Verify email is verified (Google security requirement)
            if not user_info.get("verified_email", False):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email address not verified with Google"
                )
            
            # Upsert user with Google data
            user = await self._upsert_google_user(
                google_id=user_info["id"],
                email=user_info["email"],
                display_name=user_info.get("name"),
                avatar_url=user_info.get("picture"),
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token"),
                token_expires_at=datetime.now() + timedelta(seconds=token_data["expires_in"])
            )
            
            # Generate access token
            access_token = self._create_access_token(data={"sub": str(user.id)})
            
            # Log activity
            await self.activity_logger.log_activity(
                f"User {user.email} authenticated via Google OAuth",
                user_id=str(user.id),
                activity_type="user_oauth_login",
                metadata={
                    "auth_provider": "google",
                    "is_new_user": user.last_login_at is None
                }
            )
            
            return user, access_token
            
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            # Log and convert other exceptions to HTTP exceptions
            await self.activity_logger.log_error(
                f"Google OAuth login error: {str(e)}",
                error_type="oauth_error"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication failed due to an internal error"
            )
    
    async def refresh_token(self, refresh_token: str) -> TokenResponse:
        """
        Refresh an access token using a refresh token
        
        Args:
            refresh_token: The refresh token
            
        Returns:
            New token response with refreshed access token
            
        Raises:
            HTTPException: If refresh token is invalid
        """
        try:
            # Verify the refresh token
            payload = jwt.decode(
                refresh_token, 
                settings.jwt_secret_key, 
                algorithms=[settings.jwt_algorithm]
            )
            user_id = payload.get("sub")
            
            if user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Get user
            query = select(User).where(User.id == user_id)
            result = await self.db.execute(query)
            user = result.scalars().first()
            
            if not user or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found or inactive",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Create new access token
            access_token = self._create_access_token(data={"sub": str(user.id)})
            
            # Create new refresh token
            new_refresh_token = self._create_refresh_token(data={"sub": str(user.id)})
            
            # Log activity
            await self.activity_logger.log_activity(
                f"User {user.email} refreshed their token",
                user_id=str(user.id),
                activity_type="token_refresh"
            )
            
            return TokenResponse(
                access_token=access_token,
                refresh_token=new_refresh_token,
                token_type="bearer"
            )
            
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    async def get_current_user(self, token: str) -> User:
        """
        Get the current user from a JWT token
        
        Args:
            token: JWT token
            
        Returns:
            The current user
            
        Raises:
            HTTPException: If token is invalid or user not found
        """
        try:
            # Verify the token
            payload = jwt.decode(
                token, 
                settings.jwt_secret_key, 
                algorithms=[settings.jwt_algorithm]
            )
            user_id = payload.get("sub")
            
            if user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Get user with relationships
            query = select(User).where(
                User.id == user_id,
                User.is_active == True
            ).options(
                selectinload(User.preferences),
                selectinload(User.languages),
                selectinload(User.interests),
                selectinload(User.accessibility),
                selectinload(User.onboarding_progress)
            )
            
            result = await self.db.execute(query)
            user = result.scalars().first()
            
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found",
                    headers={"WWW-Authenticate": "Bearer"},
                )
                
            return user
            
        except (PyJWTError, ExpiredSignatureError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    async def logout(self, user: User) -> bool:
        """
        Log out a user by invalidating their OAuth sessions if any
        
        Args:
            user: The user to log out
            
        Returns:
            True if successful
        """
        try:
            # Get all active OAuth sessions for the user
            query = select(OAuthSession).where(
                OAuthSession.user_id == user.id,
                OAuthSession.is_active == True
            )
            
            result = await self.db.execute(query)
            sessions = result.scalars().all()
            
            # Invalidate all sessions
            for session in sessions:
                session.is_active = False
                session.revoked_at = datetime.now()
            
            # Log activity
            await self.activity_logger.log_activity(
                f"User logged out",
                user_id=str(user.id),
                activity_type="user_logout"
            )
            
            await self.db.commit()
            return True
        except Exception as e:
            # Log the error
            await self.activity_logger.log_error(
                f"Error during logout: {str(e)}",
                error_type="logout_error"
            )
            # Rollback the transaction
            await self.db.rollback()
            raise
    
    async def _upsert_google_user(
        self,
        google_id: str,
        email: str,
        display_name: Optional[str],
        avatar_url: Optional[str],
        access_token: str,
        refresh_token: Optional[str],
        token_expires_at: datetime
    ) -> User:
        """
        Create or update a user from Google OAuth data
        
        Args:
            google_id: Google account ID
            email: User email
            display_name: User display name
            avatar_url: User avatar URL
            access_token: Google access token
            refresh_token: Google refresh token
            token_expires_at: Token expiration time
            
        Returns:
            User object
        """
        # Check if user exists by Google ID
        query = select(User).where(User.google_id == google_id)
        result = await self.db.execute(query)
        user = result.scalars().first()
        
        if not user:
            # Check if user exists by email
            query = select(User).where(User.email == email)
            result = await self.db.execute(query)
            user = result.scalars().first()
            
            if not user:
                # Create new user
                user = User(
                    id=uuid.uuid4(),
                    email=email,
                    google_id=google_id,
                    display_name=display_name,
                    avatar_url=avatar_url,
                    auth_provider="google",
                    is_active=True,
                    email_verified=True,  # Google accounts are pre-verified
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    last_login_at=datetime.now()
                )
                self.db.add(user)
                await self.db.flush()
                
                # Create default user preferences
                preferences = UserPreference(
                    user_id=user.id,
                    theme_preference="light",
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                self.db.add(preferences)
                
                # Create onboarding progress
                onboarding = OnboardingProgress(
                    user_id=user.id,
                    current_step=1,
                    progress_percentage=0,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                self.db.add(onboarding)
            else:
                # Update existing user with Google info
                user.google_id = google_id
                user.auth_provider = "google"
                user.email_verified = True
                user.updated_at = datetime.now()
                user.last_login_at = datetime.now()
                
                if display_name and not user.display_name:
                    user.display_name = display_name
                    
                if avatar_url and not user.avatar_url:
                    user.avatar_url = avatar_url
        else:
            # Update login timestamp
            user.last_login_at = datetime.now()
            user.updated_at = datetime.now()
            
            # Update user info if needed
            if display_name and not user.display_name:
                user.display_name = display_name
                
            if avatar_url and not user.avatar_url:
                user.avatar_url = avatar_url
        
        # Create or update OAuth session
        query = select(OAuthSession).where(
            OAuthSession.user_id == user.id,
            OAuthSession.provider == "google",
            OAuthSession.is_active == True
        )
        result = await self.db.execute(query)
        oauth_session = result.scalars().first()
        
        if not oauth_session:
            oauth_session = OAuthSession(
                user_id=user.id,
                provider="google",
                access_token=access_token,
                refresh_token=refresh_token,
                token_expires_at=token_expires_at,
                is_active=True,
                created_at=datetime.now(),
                last_refreshed_at=datetime.now()
            )
            self.db.add(oauth_session)
        else:
            oauth_session.access_token = access_token
            if refresh_token:
                oauth_session.refresh_token = refresh_token
            oauth_session.token_expires_at = token_expires_at
            oauth_session.last_refreshed_at = datetime.now()
        
        await self.db.commit()
        return user
    
    async def _exchange_google_code(self, code: str, redirect_uri: str, state: Optional[str] = None) -> Dict[str, Any]:
        """
        Exchange Google authorization code for tokens
        
        Args:
            code: Authorization code
            redirect_uri: Redirect URI used for authorization
            state: Optional state parameter for CSRF protection
            
        Returns:
            Token data including access_token, refresh_token, and expires_in
            
        Raises:
            HTTPException: If token exchange fails
        """
        token_url = "https://oauth2.googleapis.com/token"
        
        # Prepare token exchange data
        data = {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code"
        }
        
        # Add headers for better security and compliance
        headers = {
            "Accept": "application/json",
            "User-Agent": f"{settings.app_name}/{settings.app_version}"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    token_url, 
                    data=data, 
                    headers=headers,
                    timeout=10.0  # Add timeout for security
                )
                
                response_data = response.json()
                
                if response.status_code != 200:
                    error_detail = response_data.get("error_description", response_data.get("error", "Unknown error"))
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Failed to exchange Google code: {error_detail}"
                    )
                
                return response_data
                
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Error communicating with Google OAuth service: {str(e)}"
            )
    
    async def _get_google_user_info(self, access_token: str) -> Dict[str, Any]:
        """
        Get user info from Google using access token
        
        Args:
            access_token: Google access token
            
        Returns:
            User info from Google
            
        Raises:
            HTTPException: If getting user info fails
        """
        # Use v2 userinfo endpoint for more comprehensive data
        user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        
        # Set secure headers
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "User-Agent": f"{settings.app_name}/{settings.app_version}"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    user_info_url,
                    headers=headers,
                    timeout=10.0  # Add timeout for security
                )
                
                response_data = response.json()
                
                if response.status_code != 200:
                    error_detail = response_data.get("error", {}).get("message", "Unknown error")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Failed to get Google user info: {error_detail}"
                    )
                
                # Validate the response contains required fields
                if not response_data.get("id") or not response_data.get("email"):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Incomplete user profile from Google"
                    )
                
                return response_data
                
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Error communicating with Google API: {str(e)}"
            )
    
    async def refresh_google_token(self, oauth_session: OAuthSession) -> bool:
        """
        Refresh a Google OAuth token
        
        Args:
            oauth_session: The OAuth session to refresh
            
        Returns:
            True if successful, False otherwise
        """
        if not oauth_session.refresh_token:
            return False
        
        token_url = "https://oauth2.googleapis.com/token"
        
        # Prepare token refresh data
        data = {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "refresh_token": oauth_session.refresh_token,
            "grant_type": "refresh_token"
        }
        
        # Set secure headers
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": f"{settings.app_name}/{settings.app_version}"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    token_url, 
                    data=data, 
                    headers=headers,
                    timeout=10.0  # Add timeout for security
                )
                
                if response.status_code != 200:
                    # Log the error but don't expose details in return value
                    await self.activity_logger.log_error(
                        f"Failed to refresh Google token: {response.text}",
                        error_type="oauth_refresh_error"
                    )
                    return False
                
                token_data = response.json()
                
                if not token_data.get("access_token") or not token_data.get("expires_in"):
                    await self.activity_logger.log_error(
                        "Invalid token refresh response from Google",
                        error_type="oauth_refresh_error"
                    )
                    return False
                
                # Update session
                oauth_session.access_token = token_data["access_token"]
                oauth_session.token_expires_at = datetime.now() + timedelta(seconds=token_data["expires_in"])
                oauth_session.last_refreshed_at = datetime.now()
                
                await self.db.commit()
                return True
                
        except Exception as e:
            # Log the error but don't expose details in return value
            await self.activity_logger.log_error(
                f"Error refreshing Google token: {str(e)}",
                error_type="oauth_refresh_error"
            )
            return False
    
    # Password verification and hashing methods removed as we're using Google OAuth exclusively
    
    def _create_access_token(self, data: Dict[str, Any]) -> str:
        """
        Create a JWT access token
        
        Args:
            data: Data to encode in the token
            
        Returns:
            JWT token string
        """
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
        to_encode.update({"exp": expire})
        
        return jwt.encode(
            to_encode, 
            settings.jwt_secret_key, 
            algorithm=settings.jwt_algorithm
        )
    
    def _create_refresh_token(self, data: Dict[str, Any]) -> str:
        """
        Create a JWT refresh token
        
        Args:
            data: Data to encode in the token
            
        Returns:
            JWT token string
        """
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
        to_encode.update({"exp": expire})
        
        return jwt.encode(
            to_encode, 
            settings.jwt_secret_key, 
            algorithm=settings.jwt_algorithm
        )


# Dependency to get AuthService
async def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    """
    Dependency to get AuthService instance
    
    Args:
        db: Database session
        
    Returns:
        AuthService instance
    """
    return AuthService(db)
