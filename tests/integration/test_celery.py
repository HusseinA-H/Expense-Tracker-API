import os
import uuid
from datetime import date, datetime, timedelta, timezone
from email import message_from_string
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient

from app.celery_app import celery_app
from app.db.unit_of_work import SQLAlchemyUnitOfWork
from app.models.budget import Budget
from app.models.refresh_token import RefreshToken
from app.models.transaction import Transaction
from app.tasks.budget_alerts import _evaluate_all_budgets_async, evaluate_all_budgets
from app.tasks.celery_beat_schedule import CELERY_BEAT_SCHEDULE
from app.tasks.email_tasks import (
    _send_budget_alert_email_async,
    _send_welcome_email_async,
    send_password_reset_email,
)
from app.tasks.maintenance_tasks import _archive_old_partitions_async, _cleanup_expired_tokens_async
from app.tasks.report_tasks import _generate_csv_export_async, _generate_monthly_report_async


def _extract_email_content(mock_smtp) -> str:
    """Decode MIME email payload from mocked SMTP sendmail call."""
    raw_message = mock_smtp.sendmail.call_args[0][2]
    msg = message_from_string(raw_message)
    parts = []
    if msg.is_multipart():
        for part in msg.walk():
            payload = part.get_payload(decode=True)
            if payload:
                parts.append(payload.decode("utf-8"))
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            parts.append(payload.decode("utf-8"))
    return "\n".join(parts)


@pytest.fixture(autouse=True)
def celery_eager_mode():
    """Run Celery tasks synchronously in tests."""
    celery_app.conf.update(
        task_always_eager=True,
        task_eager_propagates=True,
    )
    yield
    celery_app.conf.update(
        task_always_eager=False,
        task_eager_propagates=False,
    )


@pytest.fixture
def mock_smtp():
    with patch("app.services.email_service.smtplib.SMTP") as mock_smtp_cls:
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
        yield mock_server


@pytest.mark.asyncio
async def test_send_welcome_email_task(test_user, mock_smtp):
    result = await _send_welcome_email_async(str(test_user.id))
    assert result["status"] == "sent"
    assert result["email"] == test_user.email
    mock_smtp.sendmail.assert_called_once()
    message_body = _extract_email_content(mock_smtp)
    assert "Welcome to Expense Tracker" in message_body
    assert test_user.first_name in message_body


def test_send_password_reset_email_task_eager(mock_smtp):
    """Verify email task composition in Celery eager mode (sync context)."""
    result = send_password_reset_email("user@example.com", "reset-token-abc123")
    assert result["status"] == "sent"
    mock_smtp.sendmail.assert_called_once()
    message_body = _extract_email_content(mock_smtp)
    assert "reset-token-abc123" in message_body
    assert "Password Reset" in message_body


@pytest.mark.asyncio
async def test_send_budget_alert_email_task(test_user, uow: SQLAlchemyUnitOfWork, mock_smtp):
    async with uow:
        categories = await uow.categories.get_all_accessible(uuid.uuid4())
        food_cat = next(c for c in categories if c.name == "Food")

        budget = Budget(
            user_id=test_user.id,
            category_id=food_cat.id,
            limit_amount=100.00,
            month=6,
            year=2026,
            alert_threshold=0.80,
            alert_sent=False,
        )
        uow._session.add(budget)
        await uow.commit()
        await uow._session.refresh(budget)
        budget_id = budget.id

    result = await _send_budget_alert_email_async(
        str(test_user.id),
        str(budget_id),
        100.00,
        95.00,
    )
    assert result["status"] == "sent"
    mock_smtp.sendmail.assert_called_once()
    message_body = _extract_email_content(mock_smtp)
    assert "Budget Alert" in message_body
    assert "Food" in message_body


@pytest.mark.asyncio
async def test_evaluate_all_budgets_triggers_alert(
    test_user, uow: SQLAlchemyUnitOfWork, mock_smtp
):
    async with uow:
        categories = await uow.categories.get_all_accessible(uuid.uuid4())
        food_cat = next(c for c in categories if c.name == "Food")

        budget = Budget(
            user_id=test_user.id,
            category_id=food_cat.id,
            limit_amount=100.00,
            month=date.today().month,
            year=date.today().year,
            alert_threshold=0.80,
            alert_sent=False,
        )
        uow._session.add(budget)
        await uow.commit()

        tx = Transaction(
            user_id=test_user.id,
            transaction_type="expense",
            amount=90.00,
            currency="USD",
            category_id=food_cat.id,
            description="Over budget test",
            transaction_date=date.today(),
            payment_method="cash",
        )
        uow._session.add(tx)
        await uow.commit()
        await uow._session.refresh(budget)
        budget_id = budget.id

    result = await _evaluate_all_budgets_async()
    assert result["status"] == "completed"
    assert result["alerts_triggered"] >= 1

    async with uow:
        updated_budget = await uow.budgets.get(budget_id)
        assert updated_budget.alert_sent is True


@pytest.mark.asyncio
async def test_generate_csv_export_creates_file(test_user, uow: SQLAlchemyUnitOfWork):
    async with uow:
        categories = await uow.categories.get_all_accessible(uuid.uuid4())
        food_cat = next(c for c in categories if c.name == "Food")

        tx = Transaction(
            user_id=test_user.id,
            transaction_type="expense",
            amount=25.50,
            currency="USD",
            category_id=food_cat.id,
            description="CSV export test",
            transaction_date=date(2026, 6, 15),
            payment_method="cash",
        )
        uow._session.add(tx)
        await uow.commit()

    result = await _generate_csv_export_async(
        str(test_user.id),
        "2026-06-01",
        "2026-06-30",
    )
    assert result["status"] == "completed"
    assert result["row_count"] >= 1
    assert os.path.isfile(result["file_path"])

    with open(result["file_path"], encoding="utf-8") as csv_file:
        content = csv_file.read()
        assert "CSV export test" in content
        assert "25.5" in content

    os.remove(result["file_path"])


@pytest.mark.asyncio
async def test_generate_monthly_report(test_user, uow: SQLAlchemyUnitOfWork):
    async with uow:
        categories = await uow.categories.get_all_accessible(uuid.uuid4())
        food_cat = next(c for c in categories if c.name == "Food")

        tx = Transaction(
            user_id=test_user.id,
            transaction_type="expense",
            amount=50.00,
            currency="USD",
            category_id=food_cat.id,
            description="Monthly report test",
            transaction_date=date(2026, 6, 10),
            payment_method="card",
        )
        uow._session.add(tx)
        await uow.commit()

    result = await _generate_monthly_report_async(str(test_user.id), 6, 2026)
    assert result["status"] == "completed"
    assert os.path.isfile(result["file_path"])
    assert result["report"]["summary"]["total_expenses"] >= 50.0

    os.remove(result["file_path"])


@pytest.mark.asyncio
async def test_cleanup_expired_tokens(uow: SQLAlchemyUnitOfWork, test_user):
    async with uow:
        expired_token = RefreshToken(
            user_id=test_user.id,
            token_hash="expired_hash_" + uuid.uuid4().hex,
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        revoked_token = RefreshToken(
            user_id=test_user.id,
            token_hash="revoked_hash_" + uuid.uuid4().hex,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            revoked_at=datetime.now(timezone.utc),
        )
        uow._session.add(expired_token)
        uow._session.add(revoked_token)
        await uow.commit()

    result = await _cleanup_expired_tokens_async()
    assert result["status"] == "completed"
    assert result["deleted_count"] >= 2


@pytest.mark.asyncio
async def test_archive_old_partitions():
    result = await _archive_old_partitions_async()
    assert result["status"] == "completed"
    assert result["action"] == "metadata_check_only"
    assert "partitions" in result


def test_celery_beat_schedule_configured():
    assert "evaluate-all-budgets-hourly" in CELERY_BEAT_SCHEDULE
    assert "cleanup-expired-tokens-daily" in CELERY_BEAT_SCHEDULE
    assert "archive-old-partitions-monthly" in CELERY_BEAT_SCHEDULE

    assert (
        CELERY_BEAT_SCHEDULE["evaluate-all-budgets-hourly"]["task"]
        == "app.tasks.budget_alerts.evaluate_all_budgets"
    )
    assert (
        CELERY_BEAT_SCHEDULE["cleanup-expired-tokens-daily"]["task"]
        == "app.tasks.maintenance_tasks.cleanup_expired_tokens"
    )
    assert (
        CELERY_BEAT_SCHEDULE["archive-old-partitions-monthly"]["task"]
        == "app.tasks.maintenance_tasks.archive_old_partitions"
    )


def test_celery_tasks_registered():
    import app.tasks.receipt_tasks  # noqa: F401 - ensure task registration

    registered = celery_app.tasks
    assert "app.tasks.email_tasks.send_welcome_email" in registered
    assert "app.tasks.budget_alerts.evaluate_all_budgets" in registered
    assert "app.tasks.report_tasks.generate_csv_export" in registered
    assert "app.tasks.receipt_tasks.process_receipt_image" in registered
    assert "app.tasks.maintenance_tasks.cleanup_expired_tokens" in registered


@pytest.mark.asyncio
async def test_user_registration_dispatches_welcome_email(client: AsyncClient):
    with patch("app.tasks.email_tasks.send_welcome_email.delay") as mock_delay:
        email = f"celery_test_{uuid.uuid4().hex[:8]}@example.com"
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "Password123!",
                "first_name": "Celery",
                "last_name": "Test",
            },
        )
        assert response.status_code == 201
        mock_delay.assert_called_once()
        called_user_id = mock_delay.call_args[0][0]
        assert called_user_id == response.json()["id"]
