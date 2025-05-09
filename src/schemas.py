# Import required types and utilities
from typing import Optional  # For optional fields
from datetime import datetime  # For timestamp handling
from pydantic import BaseModel, Field  # For data validation and field configuration

# Base Post Schema
# This defines the common fields shared by all post-related schemas
class PostBase(BaseModel):
    # Content field with validation
    # - ... means this field is required
    # - max_length=1000 limits the post length to 1000 characters
    content: str = Field(
        ...,  
        max_length=1000,
        description="The main content of the post",
        example="This is a sample post content"
    )
    
    # Optional category reference
    # - Optional[str] means this field can be None
    # - None is the default value
    category_id: Optional[str] = Field(
        None,
        description="ID of the category this post belongs to"
    )

# Schema for creating new posts
# Inherits from PostBase to get content and category_id fields
class PostCreate(PostBase):
    """
    Used when creating a new post. Only includes fields that should be
    provided when creating a post (excludes auto-generated fields).
    
    Example usage:
        post_data = PostCreate(
            content="Hello, World!",
            category_id="announcements"
        )
    """
    pass  # No additional fields needed for post creation

# Schema for post responses
# Used when returning post data to the client
class PostResponse(PostBase):
    """
    Used when sending post data back to the client. Includes all fields
    that should be visible in the API response.
    """
    # UUID of the post, converted to string for API responses
    id: str
    
    # Timestamp when the post was created
    created_at: datetime
    
    # Moderation flags with defaults
    flagged: bool = Field(
        False,
        description="Indicates if the post has been flagged for moderation"
    )
    flag_reason: Optional[str] = Field(
        None,
        description="Reason for flagging, if the post is flagged"
    )

    class Config:
        # Enables ORM mode, which allows Pydantic to work with SQLAlchemy models
        orm_mode = True
        # This means you can do:
        # db_post = Post(content="Hello")  # SQLAlchemy model
        # api_response = PostResponse.from_orm(db_post)  # Convert to Pydantic model
        
        
class PostFlagRequest(BaseModel):
    """Schema for flagging a post request"""
    reason: str = Field(
        ...,  # Required field
        min_length=1,
        max_length=255,
        description="Reason for flagging the post",
        example="Inappropriate content"
    )