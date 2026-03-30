"""Pytest fixtures for credential validation tests."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base
from app.login_mgmt.login_flow_backend.credential_validation.models import (  # noqa: F401
    CredentialValidationScenario,
    TestExecution,
    TestResult,
    ValidationRule,
)
from app.login_mgmt.login_flow_backend.credential_validation.repository import (
    ExecutionRepository,
    ResultRepository,
    RuleRepository,
    ScenarioRepository,
)
from app.login_mgmt.login_flow_backend.credential_validation.service import (
    CredentialValidationService,
)

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine):
    session_factory = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def scenario_repo(db_session):
    return ScenarioRepository(db_session)


@pytest_asyncio.fixture
async def rule_repo(db_session):
    return RuleRepository(db_session)


@pytest_asyncio.fixture
async def execution_repo(db_session):
    return ExecutionRepository(db_session)


@pytest_asyncio.fixture
async def result_repo(db_session):
    return ResultRepository(db_session)


@pytest_asyncio.fixture
async def service(db_session):
    return CredentialValidationService(db_session)
