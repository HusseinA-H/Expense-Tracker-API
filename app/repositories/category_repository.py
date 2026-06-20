import uuid

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.repositories.base import BaseRepository


class CategoryRepository(BaseRepository[Category]):
    """Repository handling Category database queries."""

    def __init__(self, session: AsyncSession):
        super().__init__(Category, session)

    async def get_accessible(
        self, category_id: uuid.UUID, user_id: uuid.UUID
    ) -> Category | None:
        """Fetch a category if it is a system category or owned by the user."""
        stmt = select(Category).where(
            and_(
                Category.id == category_id,
                (Category.is_system == True) | (Category.user_id == user_id),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_accessible(self, user_id: uuid.UUID) -> list[Category]:
        """Fetch all system categories and user-created custom categories."""
        stmt = (
            select(Category)
            .where((Category.is_system == True) | (Category.user_id == user_id))
            .order_by(Category.name.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_name(self, name: str, user_id: uuid.UUID) -> Category | None:
        """Fetch category by name (exact match) for a specific user or system category."""
        stmt = select(Category).where(
            and_(
                Category.name == name,
                (Category.is_system == True) | (Category.user_id == user_id),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
