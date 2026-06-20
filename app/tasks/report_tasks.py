import asyncio
import csv
import json
import os
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import extract, func, select

from app.celery_app import celery_app
from app.db.unit_of_work import SQLAlchemyUnitOfWork
from app.domain.specifications import (
    NotDeleted,
    TransactionByUser,
    TransactionInDateRange,
)
from app.events.base import event_bus
from app.events.definitions import ReportGenerated
from app.models.transaction import Transaction
from app.tasks import run_async

logger = structlog.get_logger("app.tasks.reports")

EXPORT_DIR = "exports"


def _run_async(coro):
    return run_async(coro)


def _ensure_export_dir() -> str:
    os.makedirs(EXPORT_DIR, exist_ok=True)
    return EXPORT_DIR


@celery_app.task(name="app.tasks.report_tasks.generate_csv_export")
def generate_csv_export(user_id: str, start_date: str, end_date: str) -> dict[str, Any]:
    """Generate a CSV export of user transactions for the given date range."""
    return _run_async(_generate_csv_export_async(user_id, start_date, end_date))


async def _generate_csv_export_async(
    user_id: str, start_date: str, end_date: str
) -> dict[str, Any]:
    uid = uuid.UUID(user_id)
    date_from = date.fromisoformat(start_date)
    date_to = date.fromisoformat(end_date)

    spec = (
        TransactionByUser(uid)
        & TransactionInDateRange(date_from, date_to)
        & NotDeleted()
    )

    uow = SQLAlchemyUnitOfWork()
    async with uow:
        transactions = await uow.transactions.get_filtered(
            spec=spec,
            page=1,
            per_page=10000,
            sort_by="transaction_date",
            sort_order="asc",
        )

        export_dir = _ensure_export_dir()
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"transactions_{user_id[:8]}_{timestamp}.csv"
        filepath = os.path.join(export_dir, filename)

        with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                "id",
                "transaction_type",
                "amount",
                "currency",
                "category_id",
                "description",
                "transaction_date",
                "payment_method",
                "receipt_url",
                "tags",
            ])
            for tx in transactions:
                writer.writerow([
                    str(tx.id),
                    tx.transaction_type,
                    float(tx.amount),
                    tx.currency,
                    str(tx.category_id) if tx.category_id else "",
                    tx.description or "",
                    tx.transaction_date.isoformat(),
                    tx.payment_method,
                    tx.receipt_url or "",
                    json.dumps(tx.tags),
                ])

        file_url = f"/exports/{filename}"
        await event_bus.publish(
            ReportGenerated(
                user_id=uid,
                report_type="csv_export",
                file_url=file_url,
            )
        )

        logger.info(
            "CSV export generated",
            user_id=user_id,
            filepath=filepath,
            row_count=len(transactions),
        )

        return {
            "status": "completed",
            "user_id": user_id,
            "file_path": filepath,
            "file_url": file_url,
            "row_count": len(transactions),
        }


@celery_app.task(name="app.tasks.report_tasks.generate_monthly_report")
def generate_monthly_report(user_id: str, month: int, year: int) -> dict[str, Any]:
    """Generate a monthly summary report for a user."""
    return _run_async(_generate_monthly_report_async(user_id, month, year))


async def _generate_monthly_report_async(
    user_id: str, month: int, year: int
) -> dict[str, Any]:
    uid = uuid.UUID(user_id)

    uow = SQLAlchemyUnitOfWork()
    async with uow:
        base_filters = (
            Transaction.user_id == uid,
            Transaction.deleted_at.is_(None),
            extract("month", Transaction.transaction_date) == month,
            extract("year", Transaction.transaction_date) == year,
        )

        expense_stmt = (
            select(func.sum(Transaction.amount))
            .where(*base_filters, Transaction.transaction_type == "expense")
        )
        income_stmt = (
            select(func.sum(Transaction.amount))
            .where(*base_filters, Transaction.transaction_type == "income")
        )
        count_stmt = select(func.count()).select_from(Transaction).where(*base_filters)

        expense_result = await uow._session.execute(expense_stmt)
        income_result = await uow._session.execute(income_stmt)
        count_result = await uow._session.execute(count_stmt)

        total_expenses = float(expense_result.scalar() or 0)
        total_income = float(income_result.scalar() or 0)
        transaction_count = count_result.scalar() or 0

        category_stmt = (
            select(Transaction.category_id, func.sum(Transaction.amount))
            .where(*base_filters, Transaction.transaction_type == "expense")
            .group_by(Transaction.category_id)
        )
        category_result = await uow._session.execute(category_stmt)
        spending_by_category = {}
        for cat_id, amount in category_result.all():
            if cat_id is not None:
                category = await uow.categories.get(cat_id)
                cat_name = category.name if category else "Unknown"
                spending_by_category[cat_name] = float(amount)

        budgets = await uow.budgets.get_user_budgets_for_period(uid, month, year)
        budget_summaries = []
        for budget in budgets:
            category = await uow.categories.get(budget.category_id)
            budget_summaries.append({
                "category": category.name if category else "Unknown",
                "limit_amount": float(budget.limit_amount),
                "alert_threshold": float(budget.alert_threshold),
                "alert_sent": budget.alert_sent,
            })

        report = {
            "user_id": user_id,
            "month": month,
            "year": year,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_expenses": total_expenses,
                "total_income": total_income,
                "net": total_income - total_expenses,
                "transaction_count": transaction_count,
            },
            "spending_by_category": spending_by_category,
            "budgets": budget_summaries,
        }

        export_dir = _ensure_export_dir()
        filename = f"monthly_report_{user_id[:8]}_{year}_{month:02d}.json"
        filepath = os.path.join(export_dir, filename)

        with open(filepath, "w", encoding="utf-8") as report_file:
            json.dump(report, report_file, indent=2)

        file_url = f"/exports/{filename}"
        await event_bus.publish(
            ReportGenerated(
                user_id=uid,
                report_type="monthly_summary",
                file_url=file_url,
            )
        )

        logger.info(
            "Monthly report generated",
            user_id=user_id,
            month=month,
            year=year,
            filepath=filepath,
        )

        return {
            "status": "completed",
            "user_id": user_id,
            "month": month,
            "year": year,
            "file_path": filepath,
            "file_url": file_url,
            "report": report,
        }
