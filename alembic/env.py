import os
import sys
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the project root directory to the path so we can import our models
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
print(f"Added {project_root} to Python path")

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Set database connection parameters from environment variables
section = config.config_ini_section

# Get database URL from environment variables
database_url = os.environ.get("DATABASE_URL", f"postgresql+asyncpg://{os.environ.get('DB_USER', 'postgres')}:{os.environ.get('DB_PASSWORD', 'postgres')}@{os.environ.get('DB_HOST', 'localhost')}:{os.environ.get('DB_PORT', '5432')}/{os.environ.get('DB_NAME', 'katiba360')}")

# Set the database URL in the Alembic config
config.set_main_option("sqlalchemy.url", database_url)

# Alternatively, you can use a single DATABASE_URL environment variable
# if os.environ.get("DATABASE_URL"):
#     config.set_main_option("sqlalchemy.url", os.environ.get("DATABASE_URL"))

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
try:
    from src.database import Base
    # Import models - we'll import each one individually to handle potential import errors
    try:
        from src.models.user_models import User, UserPreference, UserLanguage, InterestCategory, UserInterest
        from src.models.user_models import UserAccessibility, ContentFolder, SavedContent, OfflineContent
        from src.models.user_models import UserAchievement, ReadingHistory, OnboardingProgress, UserNotification
        from src.models.user_models import OAuthSession, AccountLink
        print("Successfully imported user models")
    except ImportError as e:
        print(f"Error importing user models: {e}")
    
    print("All models imported successfully")
except ImportError as e:
    print(f"Error importing base: {e}")
    raise

target_metadata = [Base.metadata]

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Add these options for better autogenerate support
        include_schemas=True,
        include_name=include_name,  # Use our custom filter function
        compare_type=True,
        compare_server_default=True,
        render_as_batch=True,
        # Reset the revision history
        version_table="alembic_version",
        version_table_schema=None,
    )

    with context.begin_transaction():
        context.run_migrations()


def include_name(name, type_, parent_names):
    """Filter function for schema names"""
    # You can add custom logic here to include/exclude specific tables
    # For example, to exclude certain tables:
    # if type_ == "table" and name.startswith("excluded_"):
    #     return False
    return True

def do_run_migrations(connection: Connection) -> None:
    """Run migrations with the given connection."""
    context.configure(
        connection=connection, 
        target_metadata=target_metadata,
        # Add these options for better autogenerate support
        include_schemas=True,
        include_name=include_name,  # Use our custom filter function
        compare_type=True,
        compare_server_default=True,
        render_as_batch=True,
        # Reset the revision history
        version_table="alembic_version",
        version_table_schema=None,
    )
    
    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations() -> None:
    """Run migrations in an async context."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
