import asyncio
import os
from typing import AsyncGenerator

import pytest
import redis.asyncio as aioredis
from httpx import ASGITransport, AsyncClient
from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Force testing environment
os.environ["ENVIRONMENT"] = "testing"

from app.api.deps import get_redis, get_unit_of_work
from app.config import settings
from app.core.security import create_access_token, hash_password
from app.db.unit_of_work import SQLAlchemyUnitOfWork
from app.events.handlers import register_event_handlers
from app.main import app
from app.models.user import User

# Register event handlers for test context
register_event_handlers()


@pytest.fixture(scope="function")
async def test_engine() -> AsyncGenerator:
    """Create a function-scoped test engine."""
    engine = create_async_engine(
        settings.DATABASE_URL,
        poolclass=NullPool,
    )
    yield engine
    await engine.dispose()


@pytest.fixture(scope="function")
def test_session_maker(test_engine) -> async_sessionmaker:
    """Create a function-scoped test sessionmaker."""
    return async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@pytest.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a database session wrapped in a transaction that rolls back."""
    async with test_engine.connect() as connection:
        # Begin a transaction
        transaction = await connection.begin()
        # Create a session bound to the connection
        async with AsyncSession(bind=connection, expire_on_commit=False) as session:
            yield session
            # Rollback the transaction to keep database clean
            await transaction.rollback()


@pytest.fixture(scope="function", autouse=True)
def mock_uow_globally(db_session: AsyncSession, monkeypatch):
    """Override SQLAlchemyUnitOfWork globally during tests to use the active test db_session."""
    from app.db.unit_of_work import SQLAlchemyUnitOfWork
    from app.repositories.audit_repository import AuditRepository
    from app.repositories.budget_repository import BudgetRepository
    from app.repositories.category_repository import CategoryRepository
    from app.repositories.refresh_token_repository import RefreshTokenRepository
    from app.repositories.transaction_repository import TransactionRepository
    from app.repositories.user_repository import UserRepository

    async def mock_enter(self):
        self._session = db_session
        self.users = UserRepository(self._session)
        self.categories = CategoryRepository(self._session)
        self.transactions = TransactionRepository(self._session)
        self.budgets = BudgetRepository(self._session)
        self.audit = AuditRepository(self._session)
        self.refresh_tokens = RefreshTokenRepository(self._session)
        return self

    async def mock_exit(self, exc_type, exc_val, exc_tb):
        pass

    async def mock_commit(self):
        await self._session.flush()

    async def mock_rollback(self):
        pass

    monkeypatch.setattr(SQLAlchemyUnitOfWork, "__aenter__", mock_enter)
    monkeypatch.setattr(SQLAlchemyUnitOfWork, "__aexit__", mock_exit)
    monkeypatch.setattr(SQLAlchemyUnitOfWork, "commit", mock_commit)
    monkeypatch.setattr(SQLAlchemyUnitOfWork, "rollback", mock_rollback)


@pytest.fixture(scope="function")
async def uow(db_session: AsyncSession) -> SQLAlchemyUnitOfWork:
    """Provide a UnitOfWork instance bound to the active transaction session."""
    from app.db.unit_of_work import SQLAlchemyUnitOfWork

    return SQLAlchemyUnitOfWork()


@pytest.fixture(scope="function")
async def redis_client() -> AsyncGenerator[aioredis.Redis, None]:
    """Provide a test Redis client using database index 5 to isolate test cache/tokens."""
    base_url = settings.REDIS_URL.rsplit("/", 1)[0]
    test_redis_url = f"{base_url}/5"
    client = aioredis.from_url(test_redis_url, decode_responses=True)
    try:
        yield client
    finally:
        await client.flushdb()
        await client.close()


@pytest.fixture(scope="function")
async def client(
    uow: SQLAlchemyUnitOfWork,
    redis_client: aioredis.Redis,
) -> AsyncGenerator[AsyncClient, None]:
    """Provide an HTTP client with dependency overrides for Unit of Work and Redis."""
    app.dependency_overrides[get_unit_of_work] = lambda: uow
    app.dependency_overrides[get_redis] = lambda: redis_client

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def test_user(uow: SQLAlchemyUnitOfWork) -> User:
    """Create a default test user."""
    async with uow:
        user = await uow.users.get_by_email("test@example.com")
        if not user:
            user = User(
                email="test@example.com",
                hashed_password=hash_password("password123"),
                first_name="Test",
                last_name="User",
                is_active=True,
                is_verified=True,
                role="user",
            )
            uow._session.add(user)
            await uow.commit()
            await uow._session.refresh(user)
        return user


@pytest.fixture(scope="function")
async def admin_user(uow: SQLAlchemyUnitOfWork) -> User:
    """Create an admin user."""
    async with uow:
        user = await uow.users.get_by_email("admin@example.com")
        if not user:
            user = User(
                email="admin@example.com",
                hashed_password=hash_password("adminpass"),
                first_name="Admin",
                last_name="User",
                is_active=True,
                is_verified=True,
                role="admin",
            )
            uow._session.add(user)
            await uow.commit()
            await uow._session.refresh(user)
        return user


@pytest.fixture(scope="function")
async def other_user(uow: SQLAlchemyUnitOfWork) -> User:
    """Create a second test user."""
    async with uow:
        user = await uow.users.get_by_email("other@example.com")
        if not user:
            user = User(
                email="other@example.com",
                hashed_password=hash_password("password123"),
                first_name="Other",
                last_name="User",
                is_active=True,
                is_verified=True,
                role="user",
            )
            uow._session.add(user)
            await uow.commit()
            await uow._session.refresh(user)
        return user


@pytest.fixture(scope="function")
def auth_headers(test_user: User) -> dict[str, str]:
    """Provide authentication headers for test_user."""
    token = create_access_token(
        user_id=test_user.id, role=test_user.role, email=test_user.email
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def admin_headers(admin_user: User) -> dict[str, str]:
    """Provide authentication headers for admin_user."""
    token = create_access_token(
        user_id=admin_user.id, role=admin_user.role, email=admin_user.email
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def other_auth_headers(other_user: User) -> dict[str, str]:
    """Provide authentication headers for other_user."""
    token = create_access_token(
        user_id=other_user.id, role=other_user.role, email=other_user.email
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function", autouse=True)
async def seed_default_categories(db_session: AsyncSession):
    """Seed default system categories inside the transaction session."""
    from app.models.category import Category
    from scripts.seed_categories import DEFAULT_CATEGORIES

    for cat_data in DEFAULT_CATEGORIES:
        category = Category(
            name=cat_data["name"],
            icon=cat_data["icon"],
            color=cat_data["color"],
            is_system=True,
            user_id=None,
        )
        db_session.add(category)
    await db_session.flush()
