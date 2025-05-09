# Import the SessionFactory we created in database.py
# The dot (.) means "from the current package"
from .database import SessionFactory

# This is a dependency function that FastAPI will use to inject database sessions
# into your route handlers. It's an async generator function.
async def get_db():
    """
    Creates and manages a database session for each request.
    
    This is a FastAPI dependency that:
    1. Creates a new database session
    2. Yields it to the route handler
    3. Ensures the session is closed after the request is complete
    
    Usage in FastAPI:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            # Use the db session here
            pass
    """
    # Create a new database session
    # This is like opening a connection to the database
    db = SessionFactory()
    
    try:
        # Yield the session to the route handler
        # This means the route can use this session for database operations
        yield db
    finally:
        # After the route is done, make sure to close the session
        # This happens even if there's an error in the route
        # The 'finally' block ensures we don't leak database connections
        await db.close()