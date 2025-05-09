# Import typing utilities and FastAPI exception handling
from typing import Any  # Used for accepting any type of error detail
from fastapi import HTTPException, status  # Base exception class and HTTP status codes


class BadRequestException(HTTPException):
    """
    400 Bad Request Exception
    Used when the client sends invalid data or parameters.
    
    Example usage:
        if not valid_input:
            raise BadRequestException("Invalid input format")
    """
    def __init__(self, detail: Any = None) -> None:
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,  # HTTP 400
            detail=detail if detail else "Bad request",  # Custom or default message
        )


class NotFoundException(HTTPException):
    """
    404 Not Found Exception
    Used when a requested resource doesn't exist.
    
    Example usage:
        post = await Post.find_by_id(db, post_id)
        if not post:
            raise NotFoundException(f"Post {post_id} not found")
    """
    def __init__(self, detail: Any = None) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,  # HTTP 404
            detail=detail if detail else "Resource not found",
        )


class ForbiddenException(HTTPException):
    """
    403 Forbidden Exception
    Used when a user is authenticated but doesn't have permission.
    
    Example usage:
        if not user.is_moderator:
            raise ForbiddenException("Only moderators can perform this action")
    """
    def __init__(self, detail: Any = None) -> None:
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,  # HTTP 403
            detail=detail if detail else "Action forbidden",
        )


class ConflictException(HTTPException):
    """
    409 Conflict Exception
    Used when there's a conflict with the current state of the resource.
    
    Example usage:
        if category_exists:
            raise ConflictException("Category with this name already exists")
    """
    def __init__(self, detail: Any = None) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,  # HTTP 409
            detail=detail if detail else "Conflict with existing resource",
        )


class UnprocessableEntityException(HTTPException):
    """
    422 Unprocessable Entity Exception
    Used when the server understands the content but can't process it.
    
    Example usage:
        if post.is_already_flagged:
            raise UnprocessableEntityException("Post is already flagged")
    """
    def __init__(self, detail: Any = None) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,  # HTTP 422
            detail=detail if detail else "Unprocessable entity",
        )


class RateLimitExceededException(HTTPException):
    """
    429 Too Many Requests Exception
    Used when the user has sent too many requests in a given time period.
    
    Example usage:
        if user_request_count > MAX_REQUESTS:
            raise RateLimitExceededException("Too many posts in 1 hour")
    """
    def __init__(self, detail: Any = None) -> None:
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,  # HTTP 429
            detail=detail if detail else "Rate limit exceeded. Try again later.",
        )


class InternalServerErrorException(HTTPException):
    """
    500 Internal Server Error Exception
    Used for unexpected server-side errors that aren't handled by other exceptions.
    
    Example usage:
        try:
            process_data()
        except Exception as e:
            raise InternalServerErrorException(f"Processing failed: {str(e)}")
    """
    def __init__(self, detail: Any = None) -> None:
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,  # HTTP 500
            detail=detail if detail else "Internal server error",
        )
