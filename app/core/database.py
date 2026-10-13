"""Database engine, connection pooling and session management."""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import settings
from app.core.logging import logger

Base = declarative_base()

# Determine database engine parameters based on URL
engine_kwargs = {"echo": False}
if "sqlite" in settings.DATABASE_URL:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs["pool_size"] = settings.DB_POOL_SIZE
    engine_kwargs["max_overflow"] = settings.DB_MAX_OVERFLOW

engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for providing an async database session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

async def init_db():
    """Initialize database tables."""
    try:
        async with engine.begin() as conn:
            # If postgresql, enable vector extension if allowed
            if "postgresql" in settings.DATABASE_URL:
                try:
                    from sqlalchemy import text
                    await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'))
                    await conn.execute(text('CREATE EXTENSION IF NOT EXISTS vector;'))
                except Exception as ext_err:
                    logger.warning(f"Could not initialize pgvector extension: {ext_err}")
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database schema initialized successfully.")
    except Exception as e:
        logger.error(f"Error during database initialization: {e}")
