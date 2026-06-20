import uuid
import structlog
from datetime import date
from decimal import Decimal
from typing import List
from sqlalchemy import select, func, extract
from app.core.exceptions import NotFoundError, ConflictError
from app.db.unit_of_work import SQLAlchemyUnitOfWork
from app.models.budget import Budget
from app.models.transaction import Transaction
from app.models.category import Category
from app.schemas.budget import BudgetCreate, BudgetUpdate, BudgetSummaryResponse

logger = structlog.get_logger("app.services.budget")

class BudgetService:
    """Service handling budget CRUD operations and threshold checks."""

    def __init__(self, uow: SQLAlchemyUnitOfWork):
        self.uow = uow

    async def create_budget(self, user_id: uuid.UUID, data: BudgetCreate) -> Budget:
        """Create a new category budget for a specific month and year."""
        async with self.uow:
            # 1. Verify category exists and is accessible
            category = await self.uow.categories.get_accessible(data.category_id, user_id)
            if not category:
                raise NotFoundError(
                    message="Category not found.",
                    error_code="CATEGORY_NOT_FOUND"
                )

            # 2. Check unique constraint
            existing = await self.uow.budgets.get_by_user_category_period(
                user_id=user_id,
                category_id=data.category_id,
                month=data.month,
                year=data.year
            )
            if existing:
                raise ConflictError(
                    message="A budget for this category and monthly period already exists.",
                    error_code="BUDGET_ALREADY_EXISTS"
                )

            budget = Budget(
                user_id=user_id,
                category_id=data.category_id,
                limit_amount=data.limit_amount,
                month=data.month,
                year=data.year,
                alert_threshold=data.alert_threshold,
                alert_sent=False
            )
            
            await self.uow.budgets.add(budget)
            await self.uow.commit()
            await self.uow.refresh(budget)

            logger.info("Budget created successfully", user_id=str(user_id), budget_id=str(budget.id))
            return budget

    async def update_budget(
        self, budget_id: uuid.UUID, user_id: uuid.UUID, data: BudgetUpdate
    ) -> Budget:
        """Update an existing budget's limit amount or threshold."""
        async with self.uow:
            budget = await self.uow.budgets.get(budget_id)
            if not budget or budget.user_id != user_id:
                raise NotFoundError(
                    message="Budget not found.",
                    error_code="BUDGET_NOT_FOUND"
                )

            update_data = data.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(budget, field, value)

            # Reset alert_sent if limit was raised
            budget.alert_sent = False

            await self.uow.budgets.update(budget)
            await self.uow.commit()
            await self.uow.refresh(budget)

            logger.info("Budget updated successfully", user_id=str(user_id), budget_id=str(budget.id))
            return budget

    async def delete_budget(self, budget_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """Delete a budget."""
        async with self.uow:
            budget = await self.uow.budgets.get(budget_id)
            if not budget or budget.user_id != user_id:
                raise NotFoundError(
                    message="Budget not found.",
                    error_code="BUDGET_NOT_FOUND"
                )

            await self.uow.budgets.delete(budget)
            await self.uow.commit()

            logger.info("Budget deleted successfully", user_id=str(user_id), budget_id=str(budget_id))

    async def list_budgets(self, user_id: uuid.UUID, month: int, year: int) -> list[Budget]:
        """List all budgets for a user in a specific period."""
        async with self.uow:
            return await self.uow.budgets.get_user_budgets_for_period(user_id, month, year)

    async def get_budget_summary(self, user_id: uuid.UUID, month: int, year: int) -> list[BudgetSummaryResponse]:
        """Compile a list of category budgets with actual spending aggregated in a single DB query."""
        async with self.uow:
            # 1. Fetch all budgets for this period
            budgets = await self.uow.budgets.get_user_budgets_for_period(user_id, month, year)
            if not budgets:
                return []

            # 2. Aggregate spending by category for this month
            # SELECT category_id, SUM(amount) FROM transactions
            # WHERE user_id = :uid AND transaction_type = 'expense' AND deleted_at IS NULL
            # AND EXTRACT(month FROM transaction_date) = :m AND EXTRACT(year FROM transaction_date) = :y
            # GROUP BY category_id
            stmt = (
                select(Transaction.category_id, func.sum(Transaction.amount))
                .where(
                    Transaction.user_id == user_id,
                    Transaction.transaction_type == "expense",
                    Transaction.deleted_at.is_(None),
                    extract("month", Transaction.transaction_date) == month,
                    extract("year", Transaction.transaction_date) == year
                )
                .group_by(Transaction.category_id)
            )
            res = await self.uow._session.execute(stmt)
            spending_map = {row[0]: row[1] for row in res.all() if row[0] is not None}

            # 3. Build summary responses
            summaries = []
            for b in budgets:
                category = await self.uow.categories.get(b.category_id)
                category_name = category.name if category else "Unknown"
                spent_amount = spending_map.get(b.category_id, 0.0)

                limit = float(b.limit_amount)
                spent = float(spent_amount)
                percentage = round((spent / limit), 4) if limit > 0 else 0.0

                summaries.append(
                    BudgetSummaryResponse(
                        id=b.id,
                        category_id=b.category_id,
                        category_name=category_name,
                        limit_amount=b.limit_amount,
                        spent_amount=spent_amount,
                        percentage=percentage,
                        month=b.month,
                        year=b.year,
                        alert_threshold=float(b.alert_threshold),
                        alert_sent=b.alert_sent
                    )
                )
            return summaries

    async def check_budget_threshold(
        self, user_id: uuid.UUID, category_id: uuid.UUID, month: int, year: int
    ) -> None:
        """Check if actual spending exceeds budget limit or alert threshold, publish Event if so."""
        async with self.uow:
            # 1. Fetch the budget
            budget = await self.uow.budgets.get_by_user_category_period(
                user_id=user_id,
                category_id=category_id,
                month=month,
                year=year
            )
            if not budget:
                return

            # 2. Aggregate spending
            stmt = (
                select(func.sum(Transaction.amount))
                .where(
                    Transaction.user_id == user_id,
                    Transaction.category_id == category_id,
                    Transaction.transaction_type == "expense",
                    Transaction.deleted_at.is_(None),
                    extract("month", Transaction.transaction_date) == month,
                    extract("year", Transaction.transaction_date) == year
                )
            )
            res = await self.uow._session.execute(stmt)
            spent_val = res.scalar() or 0.00
            spent_amount = Decimal(str(spent_val))

            # 3. Compare with limit
            limit = budget.limit_amount
            if limit <= 0:
                return

            percentage = spent_amount / limit
            threshold = budget.alert_threshold

            # If spent exceeds threshold and alert hasn't been sent yet
            if percentage >= threshold and not budget.alert_sent:
                category = await self.uow.categories.get(category_id)
                cat_name = category.name if category else "Unknown"
                
                from app.events.base import event_bus
                from app.events.definitions import BudgetExceeded
                
                # Update budget alert_sent flag
                budget.alert_sent = True
                await self.uow.budgets.update(budget)
                await self.uow.commit()

                await event_bus.publish(
                    BudgetExceeded(
                        user_id=user_id,
                        budget_id=budget.id,
                        category_name=cat_name,
                        limit_amount=limit,
                        spent_amount=spent_amount,
                        percentage=percentage
                    )
                )
