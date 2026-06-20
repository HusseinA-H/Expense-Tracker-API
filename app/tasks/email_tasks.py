import uuid
from typing import Any

import structlog

from app.celery_app import celery_app
from app.db.unit_of_work import SQLAlchemyUnitOfWork
from app.services.email_service import EmailService
from app.tasks import run_async

logger = structlog.get_logger("app.tasks.email")


@celery_app.task(name="app.tasks.email_tasks.send_welcome_email", queue="email")
def send_welcome_email(user_id: str) -> dict[str, Any]:
    """Send a welcome email to a newly registered user."""
    return run_async(_send_welcome_email_async(user_id))


async def _send_welcome_email_async(user_id: str) -> dict[str, Any]:
    uow = SQLAlchemyUnitOfWork()
    async with uow:
        user = await uow.users.get(uuid.UUID(user_id))
        if not user:
            logger.warning("User not found for welcome email", user_id=user_id)
            return {"status": "skipped", "reason": "user_not_found"}

        email_service = EmailService()
        sent = email_service.send_welcome_email(
            to_email=user.email,
            first_name=user.first_name,
        )
        return {"status": "sent" if sent else "failed", "user_id": user_id, "email": user.email}


@celery_app.task(name="app.tasks.email_tasks.send_password_reset_email", queue="email")
def send_password_reset_email(email: str, token: str) -> dict[str, Any]:
    """Send a password reset email with the reset token."""
    email_service = EmailService()
    sent = email_service.send_password_reset_email(to_email=email, token=token)
    return {"status": "sent" if sent else "failed", "email": email}


@celery_app.task(name="app.tasks.email_tasks.send_budget_alert_email", queue="email")
def send_budget_alert_email(
    user_id: str,
    budget_id: str,
    limit_amount: float,
    spent_amount: float,
) -> dict[str, Any]:
    """Send a budget alert email when spending exceeds the threshold."""
    return run_async(
        _send_budget_alert_email_async(user_id, budget_id, limit_amount, spent_amount)
    )


async def _send_budget_alert_email_async(
    user_id: str,
    budget_id: str,
    limit_amount: float,
    spent_amount: float,
) -> dict[str, Any]:
    uow = SQLAlchemyUnitOfWork()
    async with uow:
        user = await uow.users.get(uuid.UUID(user_id))
        if not user:
            logger.warning("User not found for budget alert email", user_id=user_id)
            return {"status": "skipped", "reason": "user_not_found"}

        budget = await uow.budgets.get(uuid.UUID(budget_id))
        category_name = "Unknown"
        if budget:
            category = await uow.categories.get(budget.category_id)
            if category:
                category_name = category.name

        email_service = EmailService()
        sent = email_service.send_budget_alert_email(
            to_email=user.email,
            first_name=user.first_name,
            category_name=category_name,
            limit_amount=limit_amount,
            spent_amount=spent_amount,
        )
        return {
            "status": "sent" if sent else "failed",
            "user_id": user_id,
            "budget_id": budget_id,
            "email": user.email,
        }
