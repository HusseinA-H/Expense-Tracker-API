import io
import uuid
from datetime import date
from unittest.mock import ANY, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.core.security import verify_password
from app.db.unit_of_work import SQLAlchemyUnitOfWork
from app.models.transaction import Transaction

pytestmark = pytest.mark.asyncio


async def test_password_reset_request_returns_204_for_known_user(
    client: AsyncClient, test_user
):
    with patch("app.tasks.email_tasks.send_password_reset_email.delay") as mock_delay:
        response = await client.post(
            "/api/v1/auth/password-reset/request",
            json={"email": test_user.email},
        )
        assert response.status_code == 204
        mock_delay.assert_called_once()


async def test_password_reset_request_returns_204_for_unknown_email(
    client: AsyncClient,
):
    response = await client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "missing@example.com"},
    )
    assert response.status_code == 204


async def test_password_reset_confirm_updates_password(
    client: AsyncClient, test_user, uow: SQLAlchemyUnitOfWork, redis_client
):
    token = "a" * 64
    token_hash = __import__("hashlib").sha256(token.encode("utf-8")).hexdigest()
    await redis_client.setex(f"password_reset:{token_hash}", 3600, str(test_user.id))

    response = await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={
            "email": test_user.email,
            "token": token,
            "new_password": "NewPass123!",
        },
    )
    assert response.status_code == 204

    async with uow:
        user = await uow.users.get(test_user.id)
        assert verify_password("NewPass123!", user.hashed_password)


async def test_password_reset_confirm_rejects_invalid_token(
    client: AsyncClient, test_user
):
    response = await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={
            "email": test_user.email,
            "token": "b" * 64,
            "new_password": "NewPass123!",
        },
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "RESET_TOKEN_INVALID"


async def test_csv_export_endpoint_queues_task(client: AsyncClient, auth_headers: dict):
    with patch("app.api.v1.endpoints.reports.generate_csv_export.delay") as mock_delay:
        mock_delay.return_value = MagicMock(id="csv-task-123")
        response = await client.post(
            "/api/v1/reports/export/csv",
            json={"start_date": "2026-06-01", "end_date": "2026-06-30"},
            headers=auth_headers,
        )
        assert response.status_code == 202
        data = response.json()
        assert data["task_id"] == "csv-task-123"
        assert data["status"] == "pending"
        mock_delay.assert_called_once_with(ANY, "2026-06-01", "2026-06-30")


async def test_monthly_report_endpoint_queues_task(
    client: AsyncClient, auth_headers: dict
):
    with patch(
        "app.api.v1.endpoints.reports.generate_monthly_report.delay"
    ) as mock_delay:
        mock_delay.return_value = MagicMock(id="monthly-task-456")
        response = await client.post(
            "/api/v1/reports/export/monthly",
            json={"month": 6, "year": 2026},
            headers=auth_headers,
        )
        assert response.status_code == 202
        assert response.json()["task_id"] == "monthly-task-456"
        mock_delay.assert_called_once_with(ANY, 6, 2026)


async def test_report_task_status_forbidden_for_other_user(
    client: AsyncClient, auth_headers: dict
):
    with patch("app.celery_app.celery_app.AsyncResult") as mock_result_cls:
        mock_result = MagicMock()
        mock_result.state = "SUCCESS"
        mock_result.failed.return_value = False
        mock_result.ready.return_value = True
        mock_result.result = {
            "status": "completed",
            "user_id": str(uuid.uuid4()),
            "file_url": "/exports/test.csv",
        }
        mock_result_cls.return_value = mock_result

        response = await client.get(
            "/api/v1/reports/tasks/other-user-task",
            headers=auth_headers,
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "FORBIDDEN"


async def test_receipt_upload_dispatches_processing_task(
    client: AsyncClient,
    auth_headers: dict,
    uow: SQLAlchemyUnitOfWork,
    test_user,
):
    async with uow:
        categories = await uow.categories.get_all_accessible(uuid.uuid4())
        food_cat = next(c for c in categories if c.name == "Food")

        tx = Transaction(
            user_id=test_user.id,
            transaction_type="expense",
            amount=12.00,
            currency="USD",
            category_id=food_cat.id,
            description="Receipt wiring test",
            transaction_date=date(2026, 6, 15),
            payment_method="cash",
        )
        uow._session.add(tx)
        await uow.commit()
        await uow._session.refresh(tx)
        tx_id = tx.id

    png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
        b"\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x03\x01\x01"
        b"\x00\x18\xdd\x8d\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )

    with patch("app.tasks.receipt_tasks.process_receipt_image.delay") as mock_delay:
        response = await client.post(
            f"/api/v1/transactions/{tx_id}/receipt",
            headers=auth_headers,
            files={"file": ("receipt.png", io.BytesIO(png_bytes), "image/png")},
        )

    assert response.status_code == 200
    assert response.json()["receipt_url"] is not None
    mock_delay.assert_called_once()
    call_args = mock_delay.call_args[0]
    assert call_args[0] == str(tx_id)
    assert call_args[1].endswith(".png")
