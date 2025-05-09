#!/bin/sh

# Apply database migrations
alembic upgrade head
# fastapi run
# Check the environment and run the appropriate server
if [ "$ENVIRONMENT" = "production" ]; then
    # Run the app in production mode
    fastapi run
else
    # Run the app in development mode
    fastapi dev
fi
