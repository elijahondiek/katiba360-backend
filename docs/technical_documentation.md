# Katiba360 Technical Documentation

This document provides detailed technical information about the implementation of the Katiba360 backend.

## Authentication System

### Google OAuth Implementation

The authentication system is built exclusively around Google OAuth, removing the need for password management.

#### Key Components:

1. **OAuth Flow**:
   - Frontend initiates login by redirecting to Google OAuth
   - Google returns authorization code
   - Backend exchanges code for tokens via `google_oauth_login` method
   - JWT access and refresh tokens are issued for API access

2. **Token Management**:
   - Access tokens are short-lived (default: 15 minutes)
   - Refresh tokens are longer-lived (default: 7 days)
   - Token validation middleware checks all protected routes

3. **User Creation/Update**:
   - New users are created on first login
   - Existing users are updated with latest Google profile information
   - OAuth sessions track Google tokens for API access

### JWT Implementation

```python
def _create_access_token(self, data: Dict[str, Any]) -> str:
    """
    Create a JWT access token
    
    Args:
        data: Data to encode in the token
        
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    expire = datetime.now() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
```

## Database Models

### User Model

The User model is the central entity in the system, with relationships to various user-specific data:

```python
class User(Base):
    """
    User model
    """
    __tablename__ = "tbl_users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    display_name = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    google_id = Column(String, unique=True, nullable=True)
    auth_provider = Column(String, default="google")
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    onboarding_completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    last_login_at = Column(DateTime, nullable=True)
    
    # Relationships
    preferences = relationship("UserPreference", back_populates="user", uselist=False)
    languages = relationship("UserLanguage", back_populates="user")
    interests = relationship("UserInterest", back_populates="user")
    accessibility = relationship("UserAccessibility", back_populates="user", uselist=False)
    oauth_sessions = relationship("OAuthSession", back_populates="user")
    onboarding_progress = relationship("OnboardingProgress", back_populates="user", uselist=False)
```

## Service Architecture

The application uses a service-oriented architecture with dependency injection:

### Service Factory

```python
def get_service(service_class: Type[T]) -> Callable[[AsyncSession], T]:
    """
    Factory function to create a service dependency
    
    Args:
        service_class: The service class to instantiate
        
    Returns:
        A dependency function that creates and returns a service instance
    """
    def _get_service(db: AsyncSession = Depends(get_db)) -> T:
        return service_class(db)
    
    return _get_service
```

### Auth Service

The AuthService handles all authentication-related operations:

- Google OAuth login
- Token creation and validation
- Session management

### User Service

The UserService manages user data and preferences:

- Profile management
- Preferences
- Languages
- Interests
- Accessibility settings
- Onboarding progress

## API Endpoints

### Authentication Endpoints

- `POST /auth/google`: Handle Google OAuth login
- `POST /auth/refresh`: Refresh access token
- `POST /auth/logout`: Log out user

### User Endpoints

- `GET /users/me`: Get current user profile
- `PUT /users/me`: Update user profile
- `GET /users/me/preferences`: Get user preferences
- `PUT /users/me/preferences`: Update user preferences

## Rate Limiting

The application implements a Redis-based rate limiting system to protect against DDoS attacks and API abuse.

### Rate Limiting Middleware

The `RateLimitMiddleware` provides distributed rate limiting using Redis as a backend store:

```python
class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware for rate limiting API requests using Redis
    """
    def __init__(
        self,
        app: ASGIApp,
        redis_client: Optional[Redis] = None,
        default_limit: int = 60,
        default_window: int = 60,
        path_limits: Dict[str, Tuple[int, int]] = None,
        exclude_paths: Set[str] = None
    ):
        super().__init__(app)
        self.redis_client = redis_client
        self.default_limit = default_limit  # Default requests per window
        self.default_window = default_window  # Default window in seconds
        self.path_limits = path_limits or {}
        self.exclude_paths = exclude_paths or set()
```

### Rate Limiting Configuration

The rate limiting system is configured with different limits for different endpoints:

- Auth endpoints: 30 requests per minute (to prevent brute force)
- Health check endpoint: 120 requests per minute (for monitoring systems)
- Content endpoints: 60 requests per minute
- Default for all other endpoints: 60 requests per minute

### Redis Integration

The rate limiting system uses Redis for distributed rate limiting, which allows for:

- Scalability across multiple application instances
- Persistence of rate limit counters
- Atomic increment operations

## Security Considerations

1. **No Password Storage**: By using Google OAuth exclusively, we eliminate the security risks associated with password storage and management.

2. **Token Security**: JWT tokens are signed with a secret key and have short expiration times.

3. **OAuth Best Practices**: 
   - Tokens are stored securely
   - Refresh tokens are rotated
   - Proper validation of token expiration

4. **Data Protection**:
   - User data is properly validated
   - Database queries use parameterized statements
   - Proper error handling prevents information leakage
   
5. **Rate Limiting**:
   - Prevents API abuse and DDoS attacks
   - Uses Redis for distributed rate limiting
   - Custom limits for different endpoint types

## Environment Configuration

The application uses environment variables for configuration:

```
# JWT Settings
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:3000/auth/google/callback

# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost/katiba360

# Redis (for rate limiting)
REDIS_URL=redis://localhost:6379/0

# Rate Limiting
RATE_LIMIT_DEFAULT=60  # Default requests per minute
RATE_LIMIT_AUTH=30     # Auth endpoint requests per minute
RATE_LIMIT_HEALTH=120  # Health check requests per minute
```

## Testing Strategy

1. **Unit Tests**: Test individual components in isolation
2. **Integration Tests**: Test interactions between components
3. **API Tests**: Test API endpoints with real requests
4. **Authentication Tests**: Verify OAuth flow and token handling
