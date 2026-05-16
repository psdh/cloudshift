from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from typing import AsyncGenerator
from contextlib import asynccontextmanager

from app.core.config import settings

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL or "postgresql+asyncpg://cloudshift:cloudshift_dev_password@localhost:5432/cloudshift",
    echo=settings.DEBUG,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

# Create session maker
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for models
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session.

    Usage:
        @app.get("/items")
        async def read_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def worker_session() -> AsyncGenerator[AsyncSession, None]:
    """Session for Celery tasks that wrap their work in ``asyncio.run``.

    Each task invocation runs in a *fresh* event loop. The module-global
    pooled engine binds connections to the loop that created them, so reusing
    it across ``asyncio.run`` calls raises "Future attached to a different
    loop". This builds a throwaway NullPool engine inside the current loop and
    disposes it on exit, keeping every connection loop-local.
    """
    from sqlalchemy.pool import NullPool

    engine = create_async_engine(
        settings.DATABASE_URL
        or "postgresql+asyncpg://cloudshift:cloudshift_dev_password@localhost:5432/cloudshift",
        poolclass=NullPool,
    )
    session_maker = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )
    try:
        async with session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    finally:
        await engine.dispose()


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager to get database session for use in async code.

    Usage:
        async with get_async_session() as db:
            result = await db.execute(select(Item))
            items = result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def test_connection():
    """Test database connection."""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute("SELECT 1")
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False
