"""
Test fixtures for pytest.

Uses a single temp-file SQLite database shared by a sync engine (for the
synchronous `db_session` fixture used by integration-test setup) and an async
engine (for `db` and the async `get_db` dependency the API actually uses).
A temp file — not `:memory:` — is required because each SQLite in-memory
connection is a *separate* database, so tables created on one connection are
invisible to another (the original cause of the "no such table" failures).
"""

import os
import tempfile

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app

# Ensure every model is registered on Base.metadata before create_all.
# NB: use `from app.models import ...` (not `import app.models.x`) so the
# top-level name `app` keeps pointing at the FastAPI instance imported above.
from app.models import user, connected_account, transfer, audit_log  # noqa: F401


# One shared SQLite file for the whole test session.
_db_fd, _DB_PATH = tempfile.mkstemp(suffix=".sqlite")
os.close(_db_fd)

SYNC_URL = f"sqlite:///{_DB_PATH}"
ASYNC_URL = f"sqlite+aiosqlite:///{_DB_PATH}"

_sync_engine = create_engine(
    SYNC_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_async_engine = create_async_engine(
    ASYNC_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

_SyncSession = sessionmaker(bind=_sync_engine, autoflush=False, autocommit=False)
_AsyncSession = async_sessionmaker(_async_engine, class_=AsyncSession, expire_on_commit=False)


def pytest_sessionfinish(session, exitstatus):
    """Remove the temp database file after the test session."""
    try:
        os.unlink(_DB_PATH)
    except OSError:
        pass


@pytest.fixture(autouse=True)
def _reset_schema():
    """Recreate the schema before every test so tests are isolated."""
    Base.metadata.drop_all(_sync_engine)
    Base.metadata.create_all(_sync_engine)
    yield


@pytest.fixture
def db_session():
    """Synchronous session (used by integration-test data setup)."""
    session = _SyncSession()
    try:
        yield session
    finally:
        session.close()


@pytest_asyncio.fixture
async def db():
    """Asynchronous session (used by unit/logic tests)."""
    async with _AsyncSession() as session:
        yield session


@pytest.fixture
def client():
    """Test client whose `get_db` dependency yields an async session bound
    to the same shared database the `db_session` fixture writes to."""

    async def override_get_db():
        async with _AsyncSession() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
