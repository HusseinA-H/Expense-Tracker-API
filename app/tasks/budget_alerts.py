import asyncio
from datetime import date
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import extract, func, select

from app.celery_app import celery_app
from app.db.unit_of_work import SQLAlchemyUnitOfWork
from app.events.base import event_bus
from app.events.definitions import BudgetExceeded
from app.models.transaction import Transaction
from app.tasks import run_async

logger = structlog.get_logger("app.tasks.budget_alerts")


def _run_async(coro):
    return run_async(coro)


@celery_app.task(name="app.tasks.budget_alerts.evaluate_all_budgets")
def evaluate_all_budgets() -> dict[str, Any]:
    """Scan all active budgets for the current month and trigger alerts when exceeded."""
    return _run_async(_evaluate_all_budgets_async())


async def _evaluate_all_budgets_async() -> dict[str, Any]:
    today = date.today()
    month = today.month
    year = today.year
    alerts_triggered = 0
    budgets_evaluated = 0

    uow = SQLAlchemyUnitOfWork()
    async with uow:
        budgets = await uow.budgets.get_all_for_period(month, year)
        budgets_evaluated = len(budgets)

        for budget in budgets:
            if budget.alert_sent:
                continue

            stmt = (
                select(func.sum(Transaction.amount))
                .where(
                    Transaction.user_id == budget.user_id,
                    Transaction.category_id == budget.category_id,
                    Transaction.transaction_type == "expense",
                    Transaction.deleted_at.is_(None),
                    extract("month", Transaction.transaction_date) == month,
                    extract("year", Transaction.transaction_date) == year,
                )
            )
            result = await uow._session.execute(stmt)
            spent_val = result.scalar() or 0.0
            spent_amount = Decimal(str(spent_val))
            limit = Decimal(str(budget.limit_amount))

            if limit <= 0:
                continue

            percentage = spent_amount / limit
            if percentage < Decimal(str(budget.alert_threshold)):
                continue

            category = await uow.categories.get(budget.category_id)
            category_name = category.name if category else "Unknown"

            budget.alert_sent = True
            await uow.budgets.update(budget)
            await uow.commit()

            await event_bus.publish(
                BudgetExceeded(
                    user_id=budget.user_id,
                    budget_id=budget.id,
                    category_name=category_name,
                    limit_amount=limit,
                    spent_amount=spent_amount,
                    percentage=percentage,
                )
            )
            alerts_triggered += 1
            logger.info(
                "Budget exceeded alert triggered",
                budget_id=str(budget.id),
                user_id=str(budget.user_id),
                category_name=category_name,
            )

    return {
        "status": "completed",
        "month": month,
        "year": year,
        "budgets_evaluated": budgets_evaluated,
        "alerts_triggered": alerts_triggered,
    }
