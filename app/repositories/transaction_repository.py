import uuid
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.transaction import Transaction
from app.repositories.base import BaseRepository
from app.domain.specifications import Specification

class TransactionRepository(BaseRepository[Transaction]):
    """Repository handling Transaction database queries with Specification support."""

    def __init__(self, session: AsyncSession):
        super().__init__(Transaction, session)

    async def get_filtered(
        self,
        spec: Specification,
        page: int = 1,
        per_page: int = 20,
        sort_by: str = "transaction_date",
        sort_order: str = "desc"
    ) -> list[Transaction]:
        """Fetch list of transactions satisfying a composite specification with pagination."""
        offset = (page - 1) * per_page
        
        # Determine sorting column and direction
        sort_attr = getattr(Transaction, sort_by, Transaction.transaction_date)
        if sort_order.lower() == "desc":
            sort_attr = sort_attr.desc()
        else:
            sort_attr = sort_attr.asc()

        stmt = (
            select(Transaction)
            .where(spec.to_expression())
            .order_by(sort_attr)
            .offset(offset)
            .limit(per_page)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_filtered(self, spec: Specification) -> int:
        """Count total transactions matching a specification."""
        stmt = (
            select(func.count())
            .select_from(Transaction)
            .where(spec.to_expression())
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0
