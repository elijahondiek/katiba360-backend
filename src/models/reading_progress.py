from typing import Optional, Dict, Any
import uuid
from datetime import datetime

# SQLAlchemy imports
from sqlalchemy import String, Integer, Float, ForeignKey, DateTime, Text, JSON
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

# Import the Base class from database module
from src.database import Base
from src.utils.custom_utils import utcnow

# Constants
USERS_ID_FK = "tbl_users.id"

class UserReadingProgress(Base):
    """
    SQLAlchemy model representing a user's reading progress for the constitution.
    Tracks which chapters and articles have been read, and reading time.
    """
    __tablename__ = "tbl_user_reading_progress"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey(USERS_ID_FK, ondelete="CASCADE"))
    
    # What was read - chapter or article
    item_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "chapter" or "article"
    reference: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g., "1" for chapter 1, "1.2" for article 2 in chapter 1
    
    # Reading metrics
    read_time_minutes: Mapped[float] = mapped_column(Float, default=0.0)
    total_views: Mapped[int] = mapped_column(Integer, default=1)
    
    # Status
    is_completed: Mapped[bool] = mapped_column(Integer, default=False)
    
    # Timestamps
    first_read_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow())
    last_read_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow(), onupdate=utcnow())
    
    # Optional metadata
    progress_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Relationship to User model
    user = relationship("User", back_populates="reading_progress")
