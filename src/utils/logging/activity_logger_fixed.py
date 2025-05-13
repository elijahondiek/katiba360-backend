import os
import json
import logging
import traceback
from datetime import datetime
from typing import Optional, Dict, Any, Union
from pathlib import Path
import asyncio
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler

# Configure logging
activity_log = logging.getLogger("activity_logger")
activity_log.setLevel(logging.INFO)

error_log = logging.getLogger("error_logger")
error_log.setLevel(logging.ERROR)

class ActivityLogger:
    """
    Logger for user activities in a narrative format.
    Logs are stored in logs/activity/ with timestamped files.
    """
    
    def __init__(self):
        """Initialize the activity logger."""
        # Create logs directory if it doesn't exist
        self.logs_dir = Path("logs/activity")
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Get configuration from environment variables
        self.max_file_size = int(os.getenv("ACTIVITY_LOG_MAX_SIZE_MB", "10")) * 1024 * 1024
        self.rotation_when = os.getenv("ACTIVITY_LOG_ROTATION", "midnight")
        
        # Configure handlers
        self._configure_handlers()
    
    def _configure_handlers(self):
        """Configure file handlers for logging."""
        # Clear existing handlers
        if activity_log.handlers:
            activity_log.handlers.clear()
        if error_log.handlers:
            error_log.handlers.clear()
        
        # Create formatters
        activity_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S %z'
        )
        
        error_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] [%(pathname)s:%(lineno)d] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S %z'
        )
        
        # Create activity log handlers
        activity_timed_handler = TimedRotatingFileHandler(
            filename=self.logs_dir / "activity.log",
            when=self.rotation_when,
            backupCount=30  # Keep logs for 30 days
        )
        activity_timed_handler.setFormatter(activity_formatter)
        activity_log.addHandler(activity_timed_handler)
        
        activity_size_handler = RotatingFileHandler(
            filename=self.logs_dir / "activity_size.log",
            maxBytes=self.max_file_size,
            backupCount=10  # Keep 10 backup files
        )
        activity_size_handler.setFormatter(activity_formatter)
        activity_log.addHandler(activity_size_handler)
        
        # Create error log handlers
        error_logs_dir = Path("logs/error")
        error_logs_dir.mkdir(parents=True, exist_ok=True)
        
        error_timed_handler = TimedRotatingFileHandler(
            filename=error_logs_dir / "error.log",
            when=self.rotation_when,
            backupCount=30  # Keep logs for 30 days
        )
        error_timed_handler.setFormatter(error_formatter)
        error_log.addHandler(error_timed_handler)
        
        error_size_handler = RotatingFileHandler(
            filename=error_logs_dir / "error_size.log",
            maxBytes=self.max_file_size,
            backupCount=10  # Keep 10 backup files
        )
        error_size_handler.setFormatter(error_formatter)
        error_log.addHandler(error_size_handler)
    
    async def log_activity(
        self, 
        message: str, 
        user_id: Optional[str] = None,
        activity_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log a user activity in a narrative format.
        
        Args:
            message: The narrative description of the activity
            user_id: The user ID (optional)
            activity_type: The type of activity (optional)
            metadata: Additional contextual information (optional)
        """
        # Create log entry
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "message": message,
            "user_id": user_id,
            "activity_type": activity_type,
            "metadata": metadata or {}
        }
        
        # Log as JSON
        activity_log.info(json.dumps(log_entry))
    
    def log_activity_sync(
        self, 
        message: str, 
        user_id: Optional[str] = None,
        activity_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Synchronous version of log_activity for non-async contexts.
        
        Args:
            message: The narrative description of the activity
            user_id: The user ID (optional)
            activity_type: The type of activity (optional)
            metadata: Additional contextual information (optional)
        """
        # Create log entry
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "message": message,
            "user_id": user_id,
            "activity_type": activity_type,
            "metadata": metadata or {}
        }
        
        # Log as JSON
        activity_log.info(json.dumps(log_entry))
    
    async def log_error(
        self, 
        message: str, 
        error_type: Optional[str] = None,
        user_id: Optional[str] = None,
        exception: Optional[Exception] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log an error with detailed information.
        
        Args:
            message: The error message
            error_type: The type of error (e.g., 'oauth_error')
            user_id: The user ID (optional)
            exception: The exception object (optional)
            metadata: Additional contextual information (optional)
        """
        # Get stack trace if exception is provided
        stack_trace = None
        if exception:
            stack_trace = traceback.format_exception(type(exception), exception, exception.__traceback__)
        
        # Create log entry
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "message": message,
            "error_type": error_type,
            "user_id": user_id,
            "stack_trace": stack_trace,
            "metadata": metadata or {}
        }
        
        # Log as JSON
        error_log.error(json.dumps(log_entry))
    
    def log_error_sync(
        self, 
        message: str, 
        error_type: Optional[str] = None,
        user_id: Optional[str] = None,
        exception: Optional[Exception] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Synchronous version of log_error for non-async contexts.
        
        Args:
            message: The error message
            error_type: The type of error (e.g., 'oauth_error')
            user_id: The user ID (optional)
            exception: The exception object (optional)
            metadata: Additional contextual information (optional)
        """
        # Get stack trace if exception is provided
        stack_trace = None
        if exception:
            stack_trace = traceback.format_exception(type(exception), exception, exception.__traceback__)
        
        # Create log entry
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "message": message,
            "error_type": error_type,
            "user_id": user_id,
            "stack_trace": stack_trace,
            "metadata": metadata or {}
        }
        
        # Log as JSON
        error_log.error(json.dumps(log_entry))


# Global instance for convenience
logger_instance = ActivityLogger()
