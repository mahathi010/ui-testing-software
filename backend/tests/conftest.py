"""Pytest fixtures for backend tests."""

import asyncio

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine):
    session_factory = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def definition_payload():
    return {
        "name": "Test Login Definition",
        "target_url": "https://example.com/login",
        "version": "1.0",
        "page_identity_indicator": "Login | Example",
        "viewport_width": 1280,
        "viewport_height": 720,
        "clean_session_required": True,
        "is_active": True,
    }


@pytest.fixture
def execution_payload():
    """Returns a factory; call with definition_id after creating a definition."""
    def _make(definition_id: str) -> dict:
        return {
            "definition_id": definition_id,
            "target_url": "https://example.com/login",
            "target_version": "1.0",
            "status": "pending",
        }
    return _make
