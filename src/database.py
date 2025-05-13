# Import necessary types and utilities
from typing import Any, Optional  # Used for type hints when the return type could be anything
import logging

# FastAPI imports for HTTP-related functionality
from fastapi import HTTPException, status  # For raising HTTP errors with status codes

# SQLAlchemy imports for database operations
from sqlalchemy import select  # For creating SELECT queries
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,  # Provides async attribute access for models
    async_sessionmaker,  # Creates async database sessions
    create_async_engine,  # Creates async database engine
    AsyncSession,  # Type hint for async sessions
)
from sqlalchemy.exc import SQLAlchemyError  # For handling database errors
from sqlalchemy.orm import DeclarativeBase  # Base class for declarative models

# Import configuration (usually contains environment variables and settings)
from .core.config import settings

# Database URL from configuration (e.g., postgresql+asyncpg://user:pass@localhost/dbname)
DATABASE_URL = settings.database_url

# Create an async database engine
# - future=True enables SQLAlchemy 2.0 style queries
# - echo=True logs all SQL statements (useful for debugging, consider disabling in production)
engine = create_async_engine(DATABASE_URL, future=True, echo=settings.debug)

# Create a session factory for creating new database sessions
# - autoflush=False prevents automatic flushing of changes to the database
# - expire_on_commit=False keeps objects usable after session commit
SessionFactory = async_sessionmaker(engine, autoflush=False, expire_on_commit=False)

async def init_db():
    """Initialize the database connection"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def close_db():
    """Close the database connection"""
    await engine.dispose()

async def get_db():
    """Dependency for getting a database session
    
    Yields:
        AsyncSession: Database session
    """
    async with SessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# Base class for all database models
class Base(AsyncAttrs, DeclarativeBase):
    """
    Base class that all SQLAlchemy models will inherit from.
    Includes helpful utility methods for common operations.
    """
    
    async def save(self, db: AsyncSession):
        """
        Save the current model instance to the database.
        
        Args:
            db (AsyncSession): The database session to use
            
        Returns:
            The result of the commit operation
            
        Raises:
            HTTPException: If there's an error saving to the database
        """
        try:
            # Add the current instance to the session
            db.add(self)
            # Commit the changes to the database
            return await db.commit()
        except SQLAlchemyError as ex:
            # If there's a database error, raise an HTTP 422 error
            # This is useful for API responses
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, 
                detail=repr(ex)
            ) from ex

    @classmethod
    async def find_by_id(cls, db: AsyncSession, id: str):
        """
        Find a model instance by its ID.
        
        Args:
            db (AsyncSession): The database session to use
            id (str): The ID to look for
            
        Returns:
            The first matching instance or None if not found
        """
        # Create a SELECT query for the current class
        query = select(cls).where(cls.id == id)
        # Execute the query
        result = await db.execute(query)
        # Return the first result (or None if not found)
        return result.scalars().first()