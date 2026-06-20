from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

# Primary engine with connection pooling parameters configured for production
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
    echo=settings.is_dev,
    connect_args={
        "server_settings": {
            "statement_timeout": "30000",  # 30s limit on statements
            "idle_in_transaction_session_timeout": "60000",  # 60s limit on idle tx
        }
    },
)

# Read replica engine (optional but configured per section 33.5)
read_engine = create_async_engine(
    settings.DATABASE_READ_URL,
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
    echo=settings.is_dev,
    connect_args={
        "server_settings": {
            "statement_timeout": "30000",
            "idle_in_transaction_session_timeout": "60000",
        }
    },
)

async_session_maker = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)

async_read_session_maker = async_sessionmaker(
    bind=read_engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency injection to get DB write session."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_read_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency injection to get DB read session (from read replica)."""
    async with async_read_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
