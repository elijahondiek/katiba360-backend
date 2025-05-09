import os
import json
from typing import Optional
from fastapi import APIRouter, Form, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.dependencies import get_db
from src import models, schemas
from src.utils.custom_utils import generate_response
from src.exceptions import BadRequestException, NotFoundException

POST_CREATED_SUCCESS = "Post created successfully."
POST_FLAGGED_SUCCESS = "Post flagged successfully."

# Initialize router
router = APIRouter()

# Load categories from JSON
current_dir = os.path.dirname(os.path.abspath(__file__))
categories_path = os.path.join(current_dir, "categories.json")
with open(categories_path, "r") as file:
    CATEGORIES = json.load(file)

### --- CATEGORIES --- ###

@router.get("/categories")
async def get_categories():
    """
    Fetch all categories from the JSON file.
    """
    return generate_response(
        status_code=200,
        response_message="Categories retrieved successfully.",
        customer_message="Successfully loaded categories.",
        body=CATEGORIES,
    )

### --- POSTS --- ###

@router.post("/posts")
async def create_post(
    post: schemas.PostCreate,  # Use Pydantic model directly
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new post.
    """
    # Validate category if provided
    if post.category_id:
        category = next((cat for cat in CATEGORIES if cat["id"] == post.category_id), None)
        if not category:
            raise NotFoundException(detail="Category not found.")

    # Save the post to the database
    new_post = models.Post(
        content=post.content,
        category_id=post.category_id,
    )
    db.add(new_post)
    await db.commit()
    await db.refresh(new_post)

    # Construct and return the response
    return generate_response(
        status_code=201,
        response_message=POST_CREATED_SUCCESS,
        customer_message="Post created successfully.",
        body={
            "id": str(new_post.id),
            "content": new_post.content,
            "category_id": new_post.category_id,
            "created_at": new_post.created_at.isoformat(),
        },
    )

@router.get("/posts")
async def get_posts(
    db: AsyncSession = Depends(get_db),
    category_id: Optional[str] = None,
    limit: int = 10,
    offset: int = 0,
):
    """
    Fetch posts, optionally filtered by category.
    """
    query = (
        select(models.Post)
        .order_by(models.Post.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    
    if category_id:
        query = query.where(models.Post.category_id == category_id)

    result = await db.execute(query)
    posts = result.scalars().all()

    # Format the response
    return generate_response(
        status_code=200,
        response_message="Posts retrieved successfully.",
        customer_message="Successfully loaded posts.",
        body=[
            {
                "id": str(post.id),
                "content": post.content,
                "category_id": post.category_id,
                "created_at": post.created_at.isoformat(),
                "flagged": post.flagged,
                "flag_reason": post.flag_reason,
            }
            for post in posts
        ],
    )

@router.post("/posts/{post_id}/flag")
async def flag_post(
    post_id: str,
    flag_data: schemas.PostFlagRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Flag a post for moderation.
    """
    query = await db.execute(
        select(models.Post).where(models.Post.id == post_id)
    )
    post = query.scalars().first()

    if not post:
        raise NotFoundException(detail="Post not found.")

    if post.flagged:
        raise BadRequestException(detail="Post is already flagged.")

    post.flagged = True
    post.flag_reason = flag_data.reason
    await db.commit()
    await db.refresh(post)

    return generate_response(
        status_code=200,
        response_message=POST_FLAGGED_SUCCESS,
        customer_message="The post has been flagged for moderation.",
        body={
            "id": str(post.id),
            "content": post.content,
            "category_id": post.category_id,
            "created_at": post.created_at.isoformat(),
            "flagged": post.flagged,
            "flag_reason": post.flag_reason,
        },
    )