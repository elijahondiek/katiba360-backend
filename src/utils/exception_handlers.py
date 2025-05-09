from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException, Request
import logging

from src.utils.custom_utils import generate_response

logger = logging.getLogger(__name__)

# Helper to sanitize errors for JSON serialization
def sanitize_errors(errors):
    sanitized = []
    for error in errors:
        sanitized_error = error.copy()
        # Remove or stringify any non-serializable content
        if "ctx" in sanitized_error:
            sanitized_error["ctx"] = {
                key: str(value) for key, value in sanitized_error["ctx"].items()
            }
        sanitized.append(sanitized_error)
    return sanitized


# HTTPException handler
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.error(f"HTTPException: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content=generate_response(
            status_code=exc.status_code,
            response_message=str(exc.detail),
            customer_message=str(exc.detail),
            body={},
        ),
    )


# RequestValidationError handler
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Request Validation Error: {exc.errors()}")
    sanitized_errors = sanitize_errors(exc.errors())
    return JSONResponse(
        status_code=422,
        content=generate_response(
            status_code=422,
            response_message="Validation error occurred.",
            customer_message="Invalid data provided. Please check your input.",
            body={"errors": sanitized_errors},
        ),
    )


# Pydantic ValidationError handler
async def pydantic_validation_error_handler(request: Request, exc: ValidationError):
    logger.error(f"Pydantic Validation Error: {exc.errors()}")
    sanitized_errors = sanitize_errors(exc.errors())
    return JSONResponse(
        status_code=422,
        content=generate_response(
            status_code=422,
            response_message="Data validation error occurred.",
            customer_message="Invalid data provided. Please check your input.",
            body={"errors": sanitized_errors},
        ),
    )


# SQLAlchemyError handler
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.error(f"SQLAlchemyError: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content=generate_response(
            status_code=500,
            response_message="Database error occurred.",
            customer_message="An internal error occurred. Please try again later.",
            body={"error": str(exc)},
        ),
    )
