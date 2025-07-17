from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime, date

# SQLAlchemy imports
from sqlalchemy import String, Integer, Boolean, ForeignKey, DateTime, Text, Float, JSON, Table, Enum, Date
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

# Import the Base class from database module
from src.database import Base

# Constants for repeated values
CASCADE_ALL_DELETE_ORPHAN = "all, delete-orphan"
USERS_ID_FK = "tbl_users.id"
DEFAULT_FONT_SIZE = 16
DEFAULT_FONT_FAMILY = "sans-serif"
DEFAULT_LINE_HEIGHT = 1.5
DEFAULT_HIGH_CONTRAST = False
DEFAULT_SCREEN_READER_ENABLED = False
DEFAULT_TEXT_TO_SPEECH_ENABLED = False
DEFAULT_COLOR_BLIND_MODE = None
DEFAULT_REDUCE_MOTION = False
DEFAULT_KEYBOARD_NAVIGATION = False
DEFAULT_NOTIFICATION_EMAIL = True
DEFAULT_NOTIFICATION_SMS = False
DEFAULT_OFFLINE_CONTENT_LIMIT_MB = 100
DEFAULT_AUTO_DOWNLOAD_ENABLED = False
DEFAULT_THEME_PREFERENCE = "green"
DEFAULT_READING_LEVEL = "intermediate"
DEFAULT_PRIMARY_LANGUAGE = "en"

from src.utils.custom_utils import utcnow

class User(Base):
    """
    SQLAlchemy model representing a user in the Katiba360 system.
    """
    __tablename__ = "tbl_users"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20), unique=True, nullable=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    google_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    auth_provider: Mapped[str] = mapped_column(String(50), default="google")
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    phone_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow(), onupdate=utcnow())
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    total_content_read: Mapped[int] = mapped_column(Integer, default=0)
    total_reading_time_minutes: Mapped[int] = mapped_column(Integer, default=0)
    streak_days: Mapped[int] = mapped_column(Integer, default=0)
    last_read_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    achievement_points: Mapped[int] = mapped_column(Integer, default=0)
    
    # Relationships
    preferences = relationship("UserPreference", back_populates="user", uselist=False, cascade=CASCADE_ALL_DELETE_ORPHAN)
    accessibility = relationship("UserAccessibility", back_populates="user", uselist=False, cascade=CASCADE_ALL_DELETE_ORPHAN)
    languages = relationship("UserLanguage", back_populates="user", cascade=CASCADE_ALL_DELETE_ORPHAN)
    interests = relationship("UserInterest", back_populates="user", cascade=CASCADE_ALL_DELETE_ORPHAN)
    achievements = relationship("UserAchievement", back_populates="user", cascade=CASCADE_ALL_DELETE_ORPHAN)
    saved_contents = relationship("SavedContent", back_populates="user", cascade=CASCADE_ALL_DELETE_ORPHAN)
    content_folders = relationship("ContentFolder", back_populates="user", cascade=CASCADE_ALL_DELETE_ORPHAN)
    offline_contents = relationship("OfflineContent", back_populates="user", cascade=CASCADE_ALL_DELETE_ORPHAN)
    reading_histories = relationship("ReadingHistory", back_populates="user", cascade=CASCADE_ALL_DELETE_ORPHAN)
    reading_progress = relationship("UserReadingProgress", back_populates="user", cascade=CASCADE_ALL_DELETE_ORPHAN)
    onboarding_progress = relationship("OnboardingProgress", back_populates="user", uselist=False, cascade=CASCADE_ALL_DELETE_ORPHAN)
    notifications = relationship("UserNotification", back_populates="user", cascade=CASCADE_ALL_DELETE_ORPHAN)
    oauth_sessions = relationship("OAuthSession", back_populates="user", cascade=CASCADE_ALL_DELETE_ORPHAN)
    account_links = relationship("AccountLink", back_populates="user", cascade=CASCADE_ALL_DELETE_ORPHAN)
    sharing_events = relationship("SharingEvent", back_populates="user", cascade=CASCADE_ALL_DELETE_ORPHAN)


class UserPreference(Base):
    """
    SQLAlchemy model representing user preferences.
    """
    __tablename__ = "tbl_user_preferences"
    
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey(USERS_ID_FK, ondelete="CASCADE"), primary_key=True)
    primary_language: Mapped[str] = mapped_column(String(10), default="en")
    reading_level: Mapped[str] = mapped_column(String(20), default="intermediate")
    theme_preference: Mapped[str] = mapped_column(String(20), default="green")
    notification_email: Mapped[bool] = mapped_column(Boolean, default=True)
    notification_sms: Mapped[bool] = mapped_column(Boolean, default=False)
    offline_content_limit_mb: Mapped[int] = mapped_column(Integer, default=100)
    auto_download_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow(), onupdate=utcnow())
    
    # Relationship
    user = relationship("User", back_populates="preferences")


class UserLanguage(Base):
    """
    SQLAlchemy model representing user language preferences.
    """
    __tablename__ = "tbl_user_languages"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey(USERS_ID_FK, ondelete="CASCADE"))
    language_code: Mapped[str] = mapped_column(String(10), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    proficiency_level: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow())
    
    # Relationship
    user = relationship("User", back_populates="languages")
    
    # Table constraints are defined in the migration script


class InterestCategory(Base):
    """
    SQLAlchemy model representing interest categories.
    """
    __tablename__ = "tbl_interest_categories"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    icon_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    color_code: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Relationships
    user_interests = relationship("UserInterest", back_populates="interest_category")


class UserInterest(Base):
    """
    SQLAlchemy model representing user interests.
    """
    __tablename__ = "tbl_user_interests"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey(USERS_ID_FK, ondelete="CASCADE"))
    interest_category_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tbl_interest_categories.id", ondelete="CASCADE"))
    selected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow())
    
    # Relationships
    user = relationship("User", back_populates="interests")
    interest_category = relationship("InterestCategory", back_populates="user_interests")
    
    # Table constraints are defined in the migration script


class UserAccessibility(Base):
    """
    SQLAlchemy model representing user accessibility settings.
    """
    __tablename__ = "tbl_user_accessibility"
    
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey(USERS_ID_FK, ondelete="CASCADE"), primary_key=True)
    font_size: Mapped[int] = mapped_column(Integer, default=16)
    font_family: Mapped[str] = mapped_column(String(50), default="sans-serif")
    line_height: Mapped[float] = mapped_column(Float, default=1.5)
    high_contrast: Mapped[bool] = mapped_column(Boolean, default=False)
    screen_reader_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    text_to_speech_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    color_blind_mode: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    reduce_motion: Mapped[bool] = mapped_column(Boolean, default=False)
    keyboard_navigation: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow(), onupdate=utcnow())
    
    # Relationship
    user = relationship("User", back_populates="accessibility")


class ContentFolder(Base):
    """
    SQLAlchemy model representing content folders.
    """
    __tablename__ = "tbl_content_folders"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey(USERS_ID_FK, ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    color: Mapped[str] = mapped_column(String(7), default="#2E7D32")
    icon: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    parent_folder_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("tbl_content_folders.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow())
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    
    # Relationships
    user = relationship("User", back_populates="content_folders")
    parent_folder = relationship("ContentFolder", remote_side=[id], backref="child_folders")
    saved_contents = relationship("SavedContent", back_populates="folder")


class SavedContent(Base):
    """
    SQLAlchemy model representing saved content.
    """
    __tablename__ = "tbl_saved_content"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey(USERS_ID_FK, ondelete="CASCADE"))
    content_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    content_type: Mapped[str] = mapped_column(String(50), nullable=False)
    tags: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    saved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow())
    folder_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("tbl_content_folders.id"), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="saved_contents")
    folder = relationship("ContentFolder", back_populates="saved_contents")
    
    # Table constraints are defined in the migration script


class OfflineContent(Base):
    """
    SQLAlchemy model representing offline content.
    """
    __tablename__ = "tbl_offline_content"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey(USERS_ID_FK, ondelete="CASCADE"))
    content_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    content_type: Mapped[str] = mapped_column(String(50), nullable=False)
    download_status: Mapped[str] = mapped_column(String(20), nullable=False)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    downloaded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow())
    
    # Relationship
    user = relationship("User", back_populates="offline_contents")


class UserAchievement(Base):
    """
    SQLAlchemy model representing user achievements.
    """
    __tablename__ = "tbl_user_achievements"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey(USERS_ID_FK, ondelete="CASCADE"))
    achievement_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    icon_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    badge_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    points_earned: Mapped[int] = mapped_column(Integer, default=0)
    earned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow())
    achievement_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Relationship
    user = relationship("User", back_populates="achievements")


class ReadingHistory(Base):
    """
    SQLAlchemy model representing reading history.
    """
    __tablename__ = "tbl_reading_history"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey(USERS_ID_FK, ondelete="CASCADE"))
    content_id: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(50), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    time_spent_seconds: Mapped[int] = mapped_column(Integer, default=0)
    position: Mapped[float] = mapped_column(Float, default=0.0)
    total_length: Mapped[float] = mapped_column(Float, default=1.0)
    progress_percentage: Mapped[float] = mapped_column(Float, default=0.0)
    device_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    reading_mode: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    read_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow())
    
    # Relationship
    user = relationship("User", back_populates="reading_histories")


class OnboardingProgress(Base):
    """
    SQLAlchemy model representing onboarding progress.
    """
    __tablename__ = "tbl_onboarding_progress"
    
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey(USERS_ID_FK, ondelete="CASCADE"), primary_key=True)
    step_language_selection: Mapped[bool] = mapped_column(Boolean, default=False)
    step_interests_selection: Mapped[bool] = mapped_column(Boolean, default=False)
    step_reading_level: Mapped[bool] = mapped_column(Boolean, default=False)
    step_accessibility: Mapped[bool] = mapped_column(Boolean, default=False)
    step_feature_tour: Mapped[bool] = mapped_column(Boolean, default=False)
    step_celebration: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    progress_percentage: Mapped[int] = mapped_column(Integer, default=0)
    current_step: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow(), onupdate=utcnow())
    
    # Relationship
    user = relationship("User", back_populates="onboarding_progress")


class UserNotification(Base):
    """
    SQLAlchemy model representing user notifications.
    """
    __tablename__ = "tbl_user_notifications"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey(USERS_ID_FK, ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    notification_type: Mapped[str] = mapped_column(String(50), nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    action_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow())
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationship
    user = relationship("User", back_populates="notifications")


class OAuthSession(Base):
    """
    SQLAlchemy model representing OAuth sessions.
    """
    __tablename__ = "tbl_oauth_sessions"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey(USERS_ID_FK, ondelete="CASCADE"))
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    access_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    scope: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow())
    last_refreshed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow())
    
    # Relationship
    user = relationship("User", back_populates="oauth_sessions")


class AccountLink(Base):
    """
    SQLAlchemy model representing account links.
    """
    __tablename__ = "tbl_account_links"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey(USERS_ID_FK, ondelete="CASCADE"))
    linked_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    linked_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    linked_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Relationship
    user = relationship("User", back_populates="account_links")
    
    # Table constraints are defined in the migration script


class SharingEvent(Base):
    """
    SQLAlchemy model representing sharing events for tracking user sharing behavior.
    """
    __tablename__ = "tbl_sharing_events"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey(USERS_ID_FK, ondelete="CASCADE"))
    content_type: Mapped[str] = mapped_column(String(50), nullable=False)
    content_id: Mapped[str] = mapped_column(String(255), nullable=False)
    share_method: Mapped[str] = mapped_column(String(20), nullable=False)
    content_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    shared_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow())
    
    # Relationship
    user = relationship("User", back_populates="sharing_events")


# Password reset functionality removed as we're using Google OAuth exclusively
