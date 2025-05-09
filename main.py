# Import necessary FastAPI components
from fastapi import FastAPI, HTTPException  # Core FastAPI functionality
from fastapi.exceptions import RequestValidationError  # For handling validation errors
from fastapi.responses import ORJSONResponse  # Fast JSON response handler
from fastapi.middleware.cors import CORSMiddleware  # Cross-Origin Resource Sharing
from contextlib import asynccontextmanager  # For async context management
from pydantic import ValidationError  # For Pydantic validation errors
import httpx  # HTTP client for Python
from sqlalchemy.exc import SQLAlchemyError  # Database-related errors

# Import application routes and custom error handlers
from src.routers import app_routes
from src.utils.exception_handlers import (
    http_exception_handler,
    pydantic_validation_error_handler,
    sqlalchemy_exception_handler,
    validation_exception_handler
)

# Initialize FastAPI application
app = FastAPI(
    title="Campus Pulse",  # API title for documentation
    description="Let's learn FastAPI",  # API description for documentation
    version="0.1.0",  # API version number
    default_response_class=ORJSONResponse,  # Use ORJSON for faster JSON handling
)

# CORS Configuration
# Allow all origins for development (should be restricted in production)
origins = ["*"]

# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,      # List of allowed origins (can be ["*"] for all)
    allow_credentials=True,     # Allow cookies in cross-origin requests
    allow_methods=["*"],        # Allow all HTTP methods
    allow_headers=["*"],        # Allow all HTTP headers
)

# Register custom exception handlers
# These ensure consistent error responses across the API
app.add_exception_handler(
    HTTPException,  # Handle general HTTP exceptions
    http_exception_handler
)
app.add_exception_handler(
    RequestValidationError,  # Handle request validation errors
    validation_exception_handler
)
app.add_exception_handler(
    ValidationError,  # Handle Pydantic validation errors
    pydantic_validation_error_handler
)
app.add_exception_handler(
    SQLAlchemyError,  # Handle database-related errors
    sqlalchemy_exception_handler
)

# Include routers
# This adds all the routes from app_routes with the tag "API Endpoints"
app.include_router(
    app_routes.router,
    tags=["API Endpoints"]
)