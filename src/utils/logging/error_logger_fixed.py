import os
import json
import logging
import traceback
from datetime import datetime
from typing import Optional, Dict, Any, Union
from pathlib import Path
import asyncio
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from fastapi import Request, status
from starlette.datastructures import Headers

# Configure logging
error_log = logging.getLogger("error_logger")
error_log.setLevel(logging.ERROR)

class ErrorLogger:
    """
    Logger for application errors with detailed context.
    Logs are stored in logs/errors/ with timestamped files.
    """
    
    def __init__(self):
        """Initialize the error logger."""
        # Create logs directory if it doesn't exist
        self.logs_dir = Path("logs/errors")
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Get configuration from environment variables
        self.max_file_size = int(os.getenv("ERROR_LOG_MAX_SIZE_MB", "10")) * 1024 * 1024
        self.rotation_when = os.getenv("ERROR_LOG_ROTATION", "midnight")
        
        # Configure handlers
        self._configure_handlers()
    
    def _configure_handlers(self):
        """Configure file handlers for logging."""
        # Clear existing handlers
        if error_log.handlers:
            error_log.handlers.clear()
        
        # Create a formatter
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S %z'
        )
        
        # Create a timed rotating file handler
        timed_handler = TimedRotatingFileHandler(
            filename=self.logs_dir / "error.log",
            when=self.rotation_when,
            backupCount=30  # Keep logs for 30 days
        )
        timed_handler.setFormatter(formatter)
        error_log.addHandler(timed_handler)
        
        # Create a size-based rotating file handler
        size_handler = RotatingFileHandler(
            filename=self.logs_dir / "error_size.log",
            maxBytes=self.max_file_size,
            backupCount=10  # Keep 10 backup files
        )
        size_handler.setFormatter(formatter)
        error_log.addHandler(size_handler)
    
    async def log_error(
        self,
        error: Exception,
        request: Optional[Request] = None,
        user_id: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log an error with detailed context.
        
        Args:
            error: The exception that occurred
            request: The FastAPI request object (optional)
            user_id: The user ID (optional)
            additional_context: Additional contextual information (optional)
        """
        # Extract stack trace
        stack_trace = traceback.format_exception(
            type(error), error, error.__traceback__
        )
        
        # Create base log entry
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "error_type": error.__class__.__name__,
            "error_message": str(error),
            "stack_trace": "".join(stack_trace),
            "user_id": user_id,
            "additional_context": additional_context or {}
        }
        
        # Add request information if available
        if request:
            log_entry["request"] = {
                "method": request.method,
                "url": str(request.url),
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "client_host": request.client.host if request.client else None,
                "headers": self._safe_headers(request.headers)
            }
            
            # Try to get request body if possible
            try:
                body = await request.json()
                log_entry["request"]["body"] = body
            except Exception:
                # Body might not be JSON or already consumed
                pass
        
        # Log as JSON
        error_log.error(json.dumps(log_entry))
    
    def log_error_sync(
        self,
        error: Exception,
        request_info: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Synchronous version of log_error for non-async contexts.
        
        Args:
            error: The exception that occurred
            request_info: Dictionary with request information (optional)
            user_id: The user ID (optional)
            additional_context: Additional contextual information (optional)
        """
        # Extract stack trace
        stack_trace = traceback.format_exception(
            type(error), error, error.__traceback__
        )
        
        # Create base log entry
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "error_type": error.__class__.__name__,
            "error_message": str(error),
            "stack_trace": "".join(stack_trace),
            "user_id": user_id,
            "request": request_info,
            "additional_context": additional_context or {}
        }
        
        # Log as JSON
        error_log.error(json.dumps(log_entry))
    
    def _safe_headers(self, headers: Headers) -> Dict[str, str]:
        """
        Extract headers while removing sensitive information.
        
        Args:
            headers: Request headers
            
        Returns:
            Dictionary of safe headers
        """
        # List of sensitive headers to mask
        sensitive_headers = [
            "authorization", "cookie", "x-api-key", "api-key",
            "x-csrf-token", "csrf-token", "x-xsrf-token"
        ]
        
        # Create a dictionary of headers
        headers_dict = dict(headers.items())
        
        # Mask sensitive headers
        for header in sensitive_headers:
            if header.lower() in headers_dict:
                headers_dict[header.lower()] = "[REDACTED]"
        
        return headers_dict


# Global instance for convenience
error_logger = ErrorLogger()
