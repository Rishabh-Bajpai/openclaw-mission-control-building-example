"""
Database Configuration and Session Management

This module sets up SQLAlchemy 2.0 with async support for the application.
It handles database connections, session management, and automatic table creation.

Architecture Overview:
---------------------
Mission Control uses SQLAlchemy 2.0 with async/await support. This allows
non-blocking database operations, which is essential for FastAPI's async model.

Key Components:
1. Async Engine - Connection pool to the database
2. Async Session - Transaction context for database operations
3. Declarative Base - Base class for ORM models
4. Dependency Injection - FastAPI dependency for database sessions

Database Support:
-----------------
Supports any database with an async SQLAlchemy driver:
- SQLite (aiosqlite) - Good for development
- PostgreSQL (asyncpg) - Recommended for production
- MySQL (aiomysql) - Alternative to PostgreSQL

For development, SQLite is configured by default. For production, switch
to PostgreSQL for better concurrency and features.

Usage:
------
Getting a database session in API endpoints:

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db

@app.get("/items/")
async def get_items(db: AsyncSession = Depends(get_db)):
    # Use db session here
    result = await db.execute(select(Item))
    items = result.scalars().all()
    return items
```

Direct session usage (in services, scheduler, etc.):

```python
from app.core.database import async_session

async def do_something():
    async with async_session() as db:
        result = await db.execute(select(Item))
        items = result.scalars().all()
        # Session auto-closes here
```

Transaction Management:
----------------------
SQLAlchemy async sessions support transactions:

```python
async with async_session() as db:
    try:
        db.add(new_item)
        await db.commit()  # Commit transaction
    except Exception:
        await db.rollback()  # Rollback on error
        raise
```

Important: Always use 'await' with database operations!

Extension Points:
-----------------
1. Add connection pooling options:
   ```python
   engine = create_async_engine(
       settings.DATABASE_URL,
       echo=settings.DEBUG,
       pool_size=20,
       max_overflow=30,
       pool_pre_ping=True
   )
   ```

2. Add event listeners:
   ```python
   @event.listens_for(engine.sync_engine, "connect")
   def on_connect(dbapi_conn, connection_record):
       # Run on each new connection
       pass
   ```

3. Custom session options:
   ```python
   async_session = async_sessionmaker(
       engine,
       class_=AsyncSession,
       expire_on_commit=False,
       autoflush=False
   )
   ```

Migration Strategy:
------------------
Currently, tables are auto-created on startup via init_db(). For production,
consider using Alembic for database migrations:

```bash
pip install alembic
alembic init alembic
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

Performance Considerations:
---------------------------
1. Use select() with specific columns instead of querying all columns
2. Use joinedload() for eager loading relationships
3. Add database indexes for frequently queried columns
4. Use connection pooling for production
5. Consider read replicas for heavy read operations

See Also:
---------
- app/core/config.py - Database URL configuration
- app/models/models.py - ORM model definitions
- https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings


# Database Engine
# The engine maintains a connection pool to the database
echo = settings.DEBUG
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    # Future: Add connection pooling options here
    # pool_size=20,
    # max_overflow=30,
    # pool_pre_ping=True,  # Verify connections before using
)
"""
Async SQLAlchemy engine instance.

This engine manages the database connection pool. It's configured from
settings.DATABASE_URL and uses settings.DEBUG to enable SQL query logging.

The engine is shared across the application - don't create multiple engines.
"""


# Async Session Factory
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    # Future: Add session options here
    # autoflush=False,
    # autocommit=False,
)
"""
Factory for creating async database sessions.

Use this to create sessions outside of FastAPI dependencies:

```python
async with async_session() as db:
    # Your database operations here
    result = await db.execute(select(Model))
    items = result.scalars().all()
```

Sessions created with expire_on_commit=False keep objects usable
after commit, which is helpful for returning data from services.
"""


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy ORM models.

    All model classes in app/models/models.py should inherit from this class.
    It provides the foundation for declarative model definition.

    Example:
        class Agent(Base):
            __tablename__ = "agents"
            id = Column(Integer, primary_key=True)
            name = Column(String(100))

    The Base.metadata is used to:
    - Create all tables (init_db)
    - Reflect existing database schema
    - Manage relationships between models
    """

    pass


async def get_db():
    """
    FastAPI dependency for database session injection.

    This function is used with FastAPI's Depends() to provide database
    sessions to API endpoints. It handles session lifecycle automatically.

    Usage:
        @app.get("/items/")
        async def get_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()

    Yields:
        AsyncSession: Database session with automatic cleanup

    The session is automatically closed when the request completes,
    even if an exception occurs. This prevents connection leaks.

    Note: You must await db.commit() to save changes. Sessions are
    not automatically committed!
    """
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """
    Initialize database by creating all tables.

    This function is called on application startup. It creates all tables
    defined in models that inherit from Base if they don't already exist.

    Called from:
        app/main.py in lifespan() startup sequence

    Tables Created:
        - agents
        - teams
        - tasks
        - goals
        - messages
        - meetings
        - agent_logs
        - settings

    Important Notes:
    1. This uses create_all() which is safe to run multiple times
       (it skips tables that already exist)
    2. It does NOT handle schema migrations - for production, use Alembic
    3. Tables are created with current model definitions
    4. This is an async operation - must be awaited

    Production Considerations:
    - For production with existing data, use Alembic migrations
    - Disable auto-creation and run migrations separately
    - Add migration check before starting application

    Example with Alembic (future):
        # Instead of init_db(), check migration status
        from alembic import command
        from alembic.config import Config
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
