import uuid

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.budget import Budget
from app.repositories.base import BaseRepository


class BudgetRepository(BaseRepository[Budget]):
    """Repository handling Budget database queries."""

    def __init__(self, session: AsyncSession):
        super().__init__(Budget, session)

    async def get_by_user_category_period(
        self, user_id: uuid.UUID, category_id: uuid.UUID, month: int, year: int
    ) -> Budget | None:
        """Fetch a specific budget based on user, category, and month/year period."""
        stmt = select(Budget).where(
            and_(
                Budget.user_id == user_id,
                Budget.category_id == category_id,
                Budget.month == month,
                Budget.year == year,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_budgets_for_period(
        self, user_id: uuid.UUID, month: int, year: int
    ) -> list[Budget]:
        """Fetch all budgets configured for a user in a specific month/year period."""
        stmt = select(Budget).where(
            and_(Budget.user_id == user_id, Budget.month == month, Budget.year == year)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_all_for_period(self, month: int, year: int) -> list[Budget]:
        """Fetch all budgets for a specific month/year period across all users."""
        stmt = select(Budget).where(
            and_(
                Budget.month == month,
                Budget.year == year,
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
