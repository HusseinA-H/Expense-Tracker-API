from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.session import async_session_maker
from app.repositories.audit_repository import AuditRepository
from app.repositories.budget_repository import BudgetRepository
from app.repositories.category_repository import CategoryRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.transaction_repository import TransactionRepository
from app.repositories.user_repository import UserRepository


class SQLAlchemyUnitOfWork:
    """SQLAlchemy implementation of the Unit of Work pattern."""

    def __init__(self, session_factory: async_sessionmaker = async_session_maker):
        self._session_factory = session_factory

    async def __aenter__(self) -> "SQLAlchemyUnitOfWork":
        self._session: AsyncSession = self._session_factory()
        self.users = UserRepository(self._session)
        self.categories = CategoryRepository(self._session)
        self.transactions = TransactionRepository(self._session)
        self.budgets = BudgetRepository(self._session)
        self.audit = AuditRepository(self._session)
        self.refresh_tokens = RefreshTokenRepository(self._session)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type:
            await self.rollback()
        await self._session.close()

    async def commit(self) -> None:
        """Commit the database session changes."""
        await self._session.commit()

    async def rollback(self) -> None:
        """Rollback the database session changes."""
        await self._session.rollback()

    async def refresh(self, instance) -> None:
        """Refresh the state of an instance from the database."""
        await self._session.refresh(instance)
