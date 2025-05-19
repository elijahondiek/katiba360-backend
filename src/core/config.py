import os
from decouple import config
from datetime import timedelta
from typing import Optional, Dict, Any, List

# Environment
ENVIRONMENT = config("ENVIRONMENT", default="development")

# Database
DATABASE_URL = config("DATABASE_URL")
REDIS_URL = config("REDIS_URL", default="redis://localhost:6379/0")

# Application settings
APP_NAME = config("APP_NAME", default="Katiba360")
APP_VERSION = config("APP_VERSION", default="0.1.0")
API_PREFIX = config("API_PREFIX", default="/api/v1")
DEBUG = config("DEBUG", default=False, cast=bool)
TIMEZONE = config("TIMEZONE", default="Africa/Nairobi")

# JWT Settings
JWT_SECRET_KEY = config("JWT_SECRET_KEY")
JWT_ALGORITHM = config("JWT_ALGORITHM", default="HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = config("ACCESS_TOKEN_EXPIRE_MINUTES", default=30, cast=int)
REFRESH_TOKEN_EXPIRE_DAYS = config("REFRESH_TOKEN_EXPIRE_DAYS", default=7, cast=int)

# Google OAuth Settings
GOOGLE_CLIENT_ID = config("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = config("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = config("GOOGLE_REDIRECT_URI", default="http://localhost:3000/auth/google/callback")

# CORS Settings
CORS_ORIGINS = config("CORS_ORIGINS", default="http://localhost:3000").split(",")
CORS_METHODS = config("CORS_METHODS", default="GET,POST,PUT,DELETE,OPTIONS").split(",")
CORS_HEADERS = config("CORS_HEADERS", default="Content-Type,Authorization,X-Requested-With,Accept").split(",")

# Logging Settings
LOG_LEVEL = config("LOG_LEVEL", default="INFO")
ACTIVITY_LOG_MAX_SIZE_MB = config("ACTIVITY_LOG_MAX_SIZE_MB", default=10, cast=int)
ACTIVITY_LOG_ROTATION = config("ACTIVITY_LOG_ROTATION", default="midnight")
ERROR_LOG_MAX_SIZE_MB = config("ERROR_LOG_MAX_SIZE_MB", default=10, cast=int)
ERROR_LOG_ROTATION = config("ERROR_LOG_ROTATION", default="midnight")

# Content Settings
DEFAULT_LANGUAGE = config("DEFAULT_LANGUAGE", default="en")
SUPPORTED_LANGUAGES = config("SUPPORTED_LANGUAGES", default="en,sw,ki").split(",")
DEFAULT_READING_LEVEL = config("DEFAULT_READING_LEVEL", default="intermediate")
DEFAULT_OFFLINE_CONTENT_LIMIT_MB = config("DEFAULT_OFFLINE_CONTENT_LIMIT_MB", default=100, cast=int)

# Public paths that don't require authentication
PUBLIC_PATHS = [
    "/",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/health",  # Root health check endpoint
    f"{API_PREFIX}/auth/login",
    f"{API_PREFIX}/auth/google",
    f"{API_PREFIX}/auth/google/callback",
    f"{API_PREFIX}/health"  # API-prefixed health check endpoint
]

# Public path prefixes that don't require authentication
PUBLIC_PATH_PREFIXES = [
    "/static/",
    f"{API_PREFIX}/public/",
    f"{API_PREFIX}/constitution"
]

# Settings class for FastAPI
class Settings:
    app_name: str = APP_NAME
    app_version: str = APP_VERSION
    api_prefix: str = API_PREFIX
    debug: bool = DEBUG
    database_url: str = DATABASE_URL
    redis_url: str = REDIS_URL
    jwt_secret_key: str = JWT_SECRET_KEY
    jwt_algorithm: str = JWT_ALGORITHM
    access_token_expire_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES
    refresh_token_expire_days: int = REFRESH_TOKEN_EXPIRE_DAYS
    google_client_id: str = GOOGLE_CLIENT_ID
    google_client_secret: str = GOOGLE_CLIENT_SECRET
    google_redirect_uri: str = GOOGLE_REDIRECT_URI
    cors_origins: List[str] = CORS_ORIGINS
    cors_methods: List[str] = CORS_METHODS                  
    cors_headers: List[str] = CORS_HEADERS
    public_paths: List[str] = PUBLIC_PATHS
    public_path_prefixes: List[str] = PUBLIC_PATH_PREFIXES
    timezone: str = TIMEZONE
    default_language: str = DEFAULT_LANGUAGE
    supported_languages: List[str] = SUPPORTED_LANGUAGES
    default_reading_level: str = DEFAULT_READING_LEVEL
    default_offline_content_limit_mb: int = DEFAULT_OFFLINE_CONTENT_LIMIT_MB

# Create settings instance
settings = Settings()