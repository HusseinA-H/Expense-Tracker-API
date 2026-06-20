import uuid
import pytest
from httpx import AsyncClient
from app.db.unit_of_work import SQLAlchemyUnitOfWork

pytestmark = pytest.mark.asyncio

async def test_audit_logs_require_admin(client: AsyncClient, auth_headers: dict):
    # Regular user trying to query audit logs - should be forbidden
    response = await client.get("/api/v1/audit/logs", headers=auth_headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"

async def test_audit_logs_accessible_to_admin(client: AsyncClient, admin_headers: dict):
    # Admin querying audit logs - should succeed
    response = await client.get("/api/v1/audit/logs", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

async def test_transaction_crud_audit_logs(
    client: AsyncClient, auth_headers: dict, admin_headers: dict, uow: SQLAlchemyUnitOfWork
):
    # 1. Fetch categories to get a valid category ID (Food)
    async with uow:
        categories = await uow.categories.get_all_accessible(uuid.uuid4())
        food_cat = next(c for c in categories if c.name == "Food")
        food_cat_id = food_cat.id

    # 2. Create a transaction
    tx_payload = {
        "transaction_type": "expense",
        "amount": 25.00,
        "currency": "USD",
        "category_id": str(food_cat_id),
        "description": "Lunch audit test",
        "transaction_date": "2026-06-20",
        "payment_method": "cash"
    }
    create_res = await client.post("/api/v1/transactions", json=tx_payload, headers=auth_headers)
    assert create_res.status_code == 201
    tx_id = create_res.json()["id"]

    # 3. Query audit logs as Admin to assert the CREATE log exists
    audit_res = await client.get(f"/api/v1/audit/logs?action=CREATE&entity_type=transaction&entity_id={tx_id}", headers=admin_headers)
    assert audit_res.status_code == 200
    audit_data = audit_res.json()
    assert len(audit_data) == 1
    create_log = audit_data[0]
    assert create_log["action"] == "CREATE"
    assert create_log["entity_type"] == "transaction"
    assert create_log["entity_id"] == tx_id
    assert create_log["new_data"]["description"] == "Lunch audit test"
    assert float(create_log["new_data"]["amount"]) == 25.00

    # 4. Update the transaction
    update_payload = {
        "amount": 35.00,
        "description": "Updated lunch audit test"
    }
    update_res = await client.patch(f"/api/v1/transactions/{tx_id}", json=update_payload, headers=auth_headers)
    assert update_res.status_code == 200

    # 5. Query audit logs as Admin to assert the UPDATE log exists
    audit_res = await client.get(f"/api/v1/audit/logs?action=UPDATE&entity_type=transaction&entity_id={tx_id}", headers=admin_headers)
    assert audit_res.status_code == 200
    audit_data = audit_res.json()
    assert len(audit_data) == 1
    update_log = audit_data[0]
    assert update_log["action"] == "UPDATE"
    assert float(update_log["old_data"]["amount"]) == 25.00
    assert float(update_log["new_data"]["amount"]) == 35.00
    assert update_log["new_data"]["description"] == "Updated lunch audit test"

    # 6. Delete the transaction
    delete_res = await client.delete(f"/api/v1/transactions/{tx_id}", headers=auth_headers)
    assert delete_res.status_code == 204

    # 7. Query audit logs as Admin to assert the DELETE log exists
    audit_res = await client.get(f"/api/v1/audit/logs?action=DELETE&entity_type=transaction&entity_id={tx_id}", headers=admin_headers)
    assert audit_res.status_code == 200
    audit_data = audit_res.json()
    assert len(audit_data) == 1
    delete_log = audit_data[0]
    assert delete_log["action"] == "DELETE"

async def test_auth_and_user_actions_audit_logs(client: AsyncClient, admin_headers: dict):
    # 1. Register a new user
    reg_payload = {
        "email": "audit_user@example.com",
        "password": "Password123!",
        "first_name": "Audit",
        "last_name": "User",
        "preferred_currency": "USD"
    }
    reg_res = await client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code == 201
    user_id = reg_res.json()["id"]

    # Assert registration audit log exists
    audit_res = await client.get(f"/api/v1/audit/logs?action=CREATE&entity_type=user&entity_id={user_id}", headers=admin_headers)
    assert audit_res.status_code == 200
    reg_logs = audit_res.json()
    assert len(reg_logs) == 1
    assert reg_logs[0]["new_data"]["email"] == "audit_user@example.com"

    # 2. Login
    login_payload = {
        "email": "audit_user@example.com",
        "password": "Password123!"
    }
    login_res = await client.post("/api/v1/auth/login", json=login_payload)
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {token}"}

    # Assert login audit log exists
    audit_res = await client.get(f"/api/v1/audit/logs?action=LOGIN&entity_type=user&entity_id={user_id}", headers=admin_headers)
    assert audit_res.status_code == 200
    login_logs = audit_res.json()
    assert len(login_logs) >= 1
    assert login_logs[0]["ip_address"] is not None

    # 3. Change password
    pw_payload = {
        "current_password": "Password123!",
        "new_password": "NewPassword123!"
    }
    pw_res = await client.put("/api/v1/users/me/password", json=pw_payload, headers=user_headers)
    assert pw_res.status_code == 204

    # Assert password change audit log exists
    audit_res = await client.get(f"/api/v1/audit/logs?action=PASSWORD_CHANGE&entity_type=user&entity_id={user_id}", headers=admin_headers)
    assert audit_res.status_code == 200
    pw_logs = audit_res.json()
    assert len(pw_logs) == 1

    # 4. Deactivate account
    deact_res = await client.delete("/api/v1/users/me", headers=user_headers)
    assert deact_res.status_code == 204

    # Assert account deactivation audit log exists (DELETE user action)
    audit_res = await client.get(f"/api/v1/audit/logs?action=DELETE&entity_type=user&entity_id={user_id}", headers=admin_headers)
    assert audit_res.status_code == 200
    deact_logs = audit_res.json()
    assert len(deact_logs) == 1
