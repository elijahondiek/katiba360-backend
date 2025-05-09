# Standard library imports
from typing import Optional  # For optional fields
import uuid  # For generating unique IDs
from datetime import datetime  # For timestamp fields

# SQLAlchemy imports
from sqlalchemy.orm import Mapped, mapped_column  # For modern SQLAlchemy 2.0 style
from src.database import Base  # Our base class that provides common functionality
from src.utils.custom_utils import utcnow  # Custom utility for UTC timestamps

class Post(Base):
    """
    SQLAlchemy model representing a post in the system.
    
    This model defines the structure and behavior of the 'posts' table
    in the database.
    """
    
    # Name of the database table
    __tablename__ = "posts"
    
    # Primary key field using UUID
    # - Mapped[uuid.UUID]: Indicates this field will contain a UUID
    # - primary_key=True: Makes this the primary key
    # - index=True: Creates a database index for faster lookups
    # - default=uuid.uuid4: Automatically generates a new UUID for new posts
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, 
        index=True, 
        default=uuid.uuid4
    )
    
    # The main content of the post
    # - Mapped[str]: This field will contain text
    # - nullable=False: This field cannot be NULL in the database
    content: Mapped[str] = mapped_column(nullable=False)
    
    # Optional reference to a category
    # - Mapped[Optional[str]]: This field can contain text or be None
    # - nullable=True: This field can be NULL in the database
    category_id: Mapped[Optional[str]] = mapped_column(nullable=True)
    
    # Timestamp when the post was created
    # - Mapped[datetime]: Contains a timestamp
    # - default=utcnow(): Automatically set to current UTC time when created
    created_at: Mapped[datetime] = mapped_column(default=utcnow())
    
    # Flag for moderation purposes
    # - Mapped[bool]: Boolean field
    # - default=False: New posts start as not flagged
    flagged: Mapped[bool] = mapped_column(default=False)
    
    # Optional reason for flagging
    # - Only used when post is flagged
    # - Can be NULL in database
    flag_reason: Mapped[Optional[str]] = mapped_column(nullable=True)