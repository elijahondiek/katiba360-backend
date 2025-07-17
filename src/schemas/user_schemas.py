from typing import Optional, List, Dict, Any, Union
from datetime import datetime, date
from pydantic import BaseModel, EmailStr, Field, validator, root_validator
import uuid
from enum import Enum
from src.utils.content_id import is_valid_content_id, get_content_type


class AuthProvider(str, Enum):
    """Authentication provider types"""
    GOOGLE = "google"


class ReadingLevel(str, Enum):
    """Reading level options"""
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class ThemePreference(str, Enum):
    """Theme preference options"""
    GREEN = "green"
    BLUE = "blue"
    PURPLE = "purple"
    DARK = "dark"


class ProficiencyLevel(str, Enum):
    """Language proficiency level options"""
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    FLUENT = "fluent"


class ColorBlindMode(str, Enum):
    """Color blind mode options"""
    NONE = "none"
    DEUTERANOPIA = "deuteranopia"
    PROTANOPIA = "protanopia"
    TRITANOPIA = "tritanopia"


class DeviceType(str, Enum):
    """Device type options"""
    MOBILE = "mobile"
    TABLET = "tablet"
    DESKTOP = "desktop"


class ReadingMode(str, Enum):
    """Reading mode options"""
    ONLINE = "online"
    OFFLINE = "offline"


class ShareMethod(str, Enum):
    """Share method options"""
    FACEBOOK = "facebook"
    TWITTER = "twitter"
    WHATSAPP = "whatsapp"
    NATIVE = "native"
    COPY_LINK = "copy-link"


class DownloadStatus(str, Enum):
    """Download status options"""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"


class NotificationType(str, Enum):
    """Notification type options"""
    ACHIEVEMENT = "achievement"
    UPDATE = "update"
    REMINDER = "reminder"


class BadgeType(str, Enum):
    """Badge type options"""
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"


# Base User Schemas
class UserBase(BaseModel):
    """Base schema for user data"""
    email: EmailStr
    phone: Optional[str] = None
    display_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None


class UserCreate(UserBase):
    """Schema for creating a new user with Google OAuth"""
    google_id: str
    
    @validator('phone')
    def validate_phone(cls, v):
        if v and not v.startswith('+'):
            return f"+{v}"
        return v


# Login is handled through Google OAuth, no direct login schema needed


class UserResponse(UserBase):
    """Schema for user response"""
    id: uuid.UUID
    auth_provider: AuthProvider
    email_verified: bool
    phone_verified: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None
    is_active: bool
    onboarding_completed: bool
    total_content_read: int
    total_reading_time_minutes: int
    streak_days: int
    last_read_date: Optional[date] = None
    achievement_points: int

    class Config:
        from_attributes = True


class UserUpdateRequest(BaseModel):
    """Schema for updating user profile"""
    display_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    
    @validator('phone')
    def validate_phone(cls, v):
        if v and not v.startswith('+'):
            return f"+{v}"
        return v


# Password change functionality removed as we're using Google OAuth exclusively


# Password reset request functionality removed as we're using Google OAuth exclusively


# Password reset confirmation functionality removed as we're using Google OAuth exclusively


# Google OAuth Schemas
class GoogleAuthRequest(BaseModel):
    """Schema for Google OAuth authentication request"""
    code: str
    redirect_uri: str
    state: Optional[str] = None


class TokenResponse(BaseModel):
    """Schema for token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request"""
    refresh_token: str


# User Preferences Schemas
class UserPreferenceBase(BaseModel):
    """Base schema for user preferences"""
    primary_language: str = "en"
    reading_level: ReadingLevel = ReadingLevel.INTERMEDIATE
    theme_preference: ThemePreference = ThemePreference.GREEN
    notification_email: bool = True
    notification_sms: bool = False
    offline_content_limit_mb: int = 100
    auto_download_enabled: bool = False


class UserPreferenceCreate(UserPreferenceBase):
    """Schema for creating user preferences"""
    pass


class UserPreferenceUpdate(BaseModel):
    """Schema for updating user preferences"""
    primary_language: Optional[str] = None
    reading_level: Optional[ReadingLevel] = None
    theme_preference: Optional[ThemePreference] = None
    notification_email: Optional[bool] = None
    notification_sms: Optional[bool] = None
    offline_content_limit_mb: Optional[int] = None
    auto_download_enabled: Optional[bool] = None


class UserPreferenceResponse(UserPreferenceBase):
    """Schema for user preference response"""
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# User Language Schemas
class UserLanguageBase(BaseModel):
    """Base schema for user language"""
    language_code: str
    is_primary: bool = False
    proficiency_level: Optional[ProficiencyLevel] = None


class UserLanguageCreate(UserLanguageBase):
    """Schema for creating user language"""
    pass


class UserLanguageResponse(UserLanguageBase):
    """Schema for user language response"""
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True


# Interest Category Schemas
class InterestCategoryBase(BaseModel):
    """Base schema for interest category"""
    name: str
    icon_url: Optional[str] = None
    description: Optional[str] = None
    color_code: Optional[str] = None
    is_active: bool = True


class InterestCategoryCreate(InterestCategoryBase):
    """Schema for creating interest category"""
    pass


class InterestCategoryResponse(InterestCategoryBase):
    """Schema for interest category response"""
    id: uuid.UUID

    class Config:
        from_attributes = True


# User Interest Schemas
class UserInterestCreate(BaseModel):
    """Schema for creating user interest"""
    interest_category_id: uuid.UUID


class UserInterestResponse(BaseModel):
    """Schema for user interest response"""
    id: uuid.UUID
    user_id: uuid.UUID
    interest_category_id: uuid.UUID
    selected_at: datetime
    interest_category: InterestCategoryResponse

    class Config:
        from_attributes = True


# User Accessibility Schemas
class UserAccessibilityBase(BaseModel):
    """Base schema for user accessibility"""
    font_size: int = 16
    font_family: str = "sans-serif"
    line_height: float = 1.5
    high_contrast: bool = False
    screen_reader_enabled: bool = False
    text_to_speech_enabled: bool = False
    color_blind_mode: Optional[ColorBlindMode] = None
    reduce_motion: bool = False
    keyboard_navigation: bool = False


class UserAccessibilityCreate(UserAccessibilityBase):
    """Schema for creating user accessibility"""
    pass


class UserAccessibilityUpdate(BaseModel):
    """Schema for updating user accessibility"""
    font_size: Optional[int] = None
    font_family: Optional[str] = None
    line_height: Optional[float] = None
    high_contrast: Optional[bool] = None
    screen_reader_enabled: Optional[bool] = None
    text_to_speech_enabled: Optional[bool] = None
    color_blind_mode: Optional[ColorBlindMode] = None
    reduce_motion: Optional[bool] = None
    keyboard_navigation: Optional[bool] = None


class UserAccessibilityResponse(UserAccessibilityBase):
    """Schema for user accessibility response"""
    user_id: uuid.UUID
    updated_at: datetime

    class Config:
        from_attributes = True


# Content Folder Schemas
class ContentFolderBase(BaseModel):
    """Base schema for content folder"""
    name: str
    color: str = "#2E7D32"
    icon: Optional[str] = None
    parent_folder_id: Optional[uuid.UUID] = None
    sort_order: int = 0


class ContentFolderCreate(ContentFolderBase):
    """Schema for creating content folder"""
    pass


class ContentFolderUpdate(BaseModel):
    """Schema for updating content folder"""
    name: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    parent_folder_id: Optional[uuid.UUID] = None
    sort_order: Optional[int] = None


class ContentFolderResponse(ContentFolderBase):
    """Schema for content folder response"""
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    child_count: int = 0
    content_count: int = 0

    class Config:
        from_attributes = True


# Saved Content Schemas
class SavedContentBase(BaseModel):
    """Base schema for saved content"""
    content_id: uuid.UUID
    content_type: str
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    is_favorite: bool = False
    folder_id: Optional[uuid.UUID] = None


class SavedContentCreate(SavedContentBase):
    """Schema for creating saved content"""
    pass


class SavedContentUpdate(BaseModel):
    """Schema for updating saved content"""
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    is_favorite: Optional[bool] = None
    folder_id: Optional[uuid.UUID] = None


class SavedContentResponse(SavedContentBase):
    """Schema for saved content response"""
    id: uuid.UUID
    user_id: uuid.UUID
    saved_at: datetime
    folder: Optional[ContentFolderResponse] = None

    class Config:
        from_attributes = True


# Offline Content Schemas
class OfflineContentBase(BaseModel):
    """Base schema for offline content"""
    content_id: uuid.UUID
    content_type: str
    download_status: DownloadStatus = DownloadStatus.PENDING
    file_size_bytes: Optional[int] = None
    priority: int = 0


class OfflineContentCreate(OfflineContentBase):
    """Schema for creating offline content"""
    pass


class OfflineContentUpdate(BaseModel):
    """Schema for updating offline content"""
    download_status: Optional[DownloadStatus] = None
    file_size_bytes: Optional[int] = None
    downloaded_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    priority: Optional[int] = None


class OfflineContentResponse(OfflineContentBase):
    """Schema for offline content response"""
    id: uuid.UUID
    user_id: uuid.UUID
    downloaded_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# User Achievement Schemas
class UserAchievementBase(BaseModel):
    """Base schema for user achievement"""
    achievement_type: str
    title: str
    description: Optional[str] = None
    icon_url: Optional[str] = None
    badge_type: Optional[BadgeType] = None
    points_earned: int = 0
    metadata: Optional[Dict[str, Any]] = None


class UserAchievementCreate(UserAchievementBase):
    """Schema for creating user achievement"""
    pass


class UserAchievementResponse(UserAchievementBase):
    """Schema for user achievement response"""
    id: uuid.UUID
    user_id: uuid.UUID
    earned_at: datetime

    class Config:
        from_attributes = True


# Reading History Schemas
class ReadingHistoryBase(BaseModel):
    """Base schema for reading history"""
    content_id: uuid.UUID
    content_type: str
    progress_percentage: int = 0
    last_position: Optional[str] = None
    device_type: Optional[DeviceType] = None
    reading_mode: Optional[ReadingMode] = None


class ReadingHistoryCreate(ReadingHistoryBase):
    """Schema for creating reading history"""
    pass


class ReadingHistoryUpdate(BaseModel):
    """Schema for updating reading history"""
    progress_percentage: Optional[int] = None
    last_position: Optional[str] = None
    completed_at: Optional[datetime] = None
    reading_time_seconds: Optional[int] = None


class ReadingHistoryResponse(ReadingHistoryBase):
    """Schema for reading history response"""
    id: uuid.UUID
    user_id: uuid.UUID
    started_at: datetime
    completed_at: Optional[datetime] = None
    reading_time_seconds: Optional[int] = None

    class Config:
        from_attributes = True


# Onboarding Progress Schemas
class OnboardingProgressBase(BaseModel):
    """Base schema for onboarding progress"""
    step_language_selection: bool = False
    step_interests_selection: bool = False
    step_reading_level: bool = False
    step_accessibility: bool = False
    step_feature_tour: bool = False
    step_celebration: bool = False
    progress_percentage: int = 0
    current_step: int = 1


class OnboardingProgressCreate(OnboardingProgressBase):
    """Schema for creating onboarding progress"""
    pass


class OnboardingProgressUpdate(BaseModel):
    """Schema for updating onboarding progress"""
    step_language_selection: Optional[bool] = None
    step_interests_selection: Optional[bool] = None
    step_reading_level: Optional[bool] = None
    step_accessibility: Optional[bool] = None
    step_feature_tour: Optional[bool] = None
    step_celebration: Optional[bool] = None
    completed_at: Optional[datetime] = None
    progress_percentage: Optional[int] = None
    current_step: Optional[int] = None


class OnboardingProgressResponse(OnboardingProgressBase):
    """Schema for onboarding progress response"""
    user_id: uuid.UUID
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# User Notification Schemas
class UserNotificationBase(BaseModel):
    """Base schema for user notification"""
    title: str
    message: str
    notification_type: NotificationType
    action_url: Optional[str] = None
    priority: int = 0


class UserNotificationCreate(UserNotificationBase):
    """Schema for creating user notification"""
    pass


class UserNotificationUpdate(BaseModel):
    """Schema for updating user notification"""
    is_read: Optional[bool] = None
    read_at: Optional[datetime] = None


class UserNotificationResponse(UserNotificationBase):
    """Schema for user notification response"""
    id: uuid.UUID
    user_id: uuid.UUID
    is_read: bool
    created_at: datetime
    read_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# OAuth Session Schemas
class OAuthSessionBase(BaseModel):
    """Base schema for OAuth session"""
    provider: str
    access_token: str
    refresh_token: Optional[str] = None
    token_expires_at: datetime
    scope: Optional[str] = None
    is_active: bool = True


class OAuthSessionCreate(OAuthSessionBase):
    """Schema for creating OAuth session"""
    pass


class OAuthSessionUpdate(BaseModel):
    """Schema for updating OAuth session"""
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    last_refreshed_at: Optional[datetime] = None
    is_active: Optional[bool] = None


class OAuthSessionResponse(OAuthSessionBase):
    """Schema for OAuth session response"""
    id: uuid.UUID
    user_id: uuid.UUID
    granted_at: datetime
    last_refreshed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Account Link Schemas
class AccountLinkBase(BaseModel):
    """Base schema for account link"""
    linked_provider: str
    linked_email: Optional[str] = None
    linked_id: Optional[str] = None
    is_active: bool = True


class AccountLinkCreate(AccountLinkBase):
    """Schema for creating account link"""
    pass


class AccountLinkUpdate(BaseModel):
    """Schema for updating account link"""
    linked_email: Optional[str] = None
    linked_id: Optional[str] = None
    is_active: Optional[bool] = None


class AccountLinkResponse(AccountLinkBase):
    """Schema for account link response"""
    id: uuid.UUID
    user_id: uuid.UUID
    linked_at: datetime

    class Config:
        from_attributes = True


# Reading History Schemas
class ReadingHistoryCreate(BaseModel):
    """Schema for creating reading history"""
    content_id: str
    content_type: str
    time_spent_seconds: int
    position: float
    total_length: float
    device_type: Optional[DeviceType] = None
    reading_mode: Optional[ReadingMode] = None
    
    @validator('content_id')
    def validate_content_id(cls, v):
        if not is_valid_content_id(v):
            raise ValueError('Invalid content ID format. Must be a standardized content ID.')
        return v
        
    @validator('content_type')
    def validate_content_type(cls, v, values):
        if 'content_id' in values:
            content_id = values['content_id']
            expected_type = get_content_type(content_id)
            if expected_type and expected_type != v:
                raise ValueError(f'Content type mismatch. Expected {expected_type} based on content ID.')
        return v
        
    @validator('position', 'total_length')
    def validate_position_range(cls, v):
        if v < 0 or v > 1:
            raise ValueError('Position and total_length must be between 0 and 1 (representing percentage)')
        return v


class ReadingHistoryResponse(BaseModel):
    """Schema for reading history response"""
    id: uuid.UUID
    user_id: uuid.UUID
    content_id: str
    content_type: str
    time_spent_seconds: int
    position: float
    total_length: float
    progress_percentage: float
    device_type: Optional[str] = None
    reading_mode: Optional[str] = None
    read_at: datetime
    
    class Config:
        from_attributes = True


class ReadingProgressResponse(BaseModel):
    """Schema for reading progress response"""
    content_id: str
    progress_percentage: float
    last_position: float
    last_read_at: Optional[datetime] = None


class ReadingStreakResponse(BaseModel):
    """Schema for reading streak response"""
    current_streak: int
    longest_streak: int
    last_read_date: Optional[date] = None
    streak_maintained: bool


# Complete User Profile Response
class CompleteUserProfileResponse(UserResponse):
    """Complete user profile with all related data"""
    preferences: Optional[UserPreferenceResponse] = None
    languages: List[UserLanguageResponse] = []
    interests: List[UserInterestResponse] = []
    accessibility: Optional[UserAccessibilityResponse] = None
    onboarding_progress: Optional[OnboardingProgressResponse] = None
    achievements_count: int = 0
    saved_content_count: int = 0
    folders_count: int = 0
    
    class Config:
        from_attributes = True


# Sharing Event Schemas
class SharingEventBase(BaseModel):
    """Base schema for sharing event"""
    content_type: str
    content_id: str
    share_method: ShareMethod
    content_url: str


class SharingEventCreate(SharingEventBase):
    """Schema for creating sharing event"""
    pass


class SharingEventResponse(SharingEventBase):
    """Schema for sharing event response"""
    id: uuid.UUID
    user_id: uuid.UUID
    shared_at: datetime
    
    class Config:
        from_attributes = True
