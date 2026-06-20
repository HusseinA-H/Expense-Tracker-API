import uuid
import pytest
from datetime import date
from httpx import AsyncClient
from app.models.budget import Budget
from app.models.transaction import Transaction
from app.db.unit_of_work import SQLAlchemyUnitOfWork

pytestmark = pytest.mark.asyncio

async def test_create_budget(client: AsyncClient, auth_headers: dict, uow: SQLAlchemyUnitOfWork):
    # Find a category (we seeded "Food" as a system category)
    async with uow:
        categories = await uow.categories.get_all_accessible(uuid.uuid4())
        food_cat = next(c for c in categories if c.name == "Food")
        food_cat_id = food_cat.id

    payload = {
        "category_id": str(food_cat_id),
        "limit_amount": 500.00,
        "month": 6,
        "year": 2026,
        "alert_threshold": 0.85
    }
    
    response = await client.post("/api/v1/budgets", json=payload, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["category_id"] == str(food_cat_id)
    assert float(data["limit_amount"]) == 500.00
    assert data["month"] == 6
    assert data["year"] == 2026
    assert float(data["alert_threshold"]) == 0.85
    assert data["alert_sent"] is False

    # Check database
    async with uow:
        budget = await uow.budgets.get(uuid.UUID(data["id"]))
        assert budget is not None
        assert float(budget.limit_amount) == 500.00

async def test_create_duplicate_budget(client: AsyncClient, auth_headers: dict, uow: SQLAlchemyUnitOfWork):
    async with uow:
        categories = await uow.categories.get_all_accessible(uuid.uuid4())
        food_cat = next(c for c in categories if c.name == "Food")
        food_cat_id = food_cat.id

    payload = {
        "category_id": str(food_cat_id),
        "limit_amount": 500.00,
        "month": 6,
        "year": 2026
    }
    
    # Create first
    res1 = await client.post("/api/v1/budgets", json=payload, headers=auth_headers)
    assert res1.status_code == 201
    
    # Create duplicate
    res2 = await client.post("/api/v1/budgets", json=payload, headers=auth_headers)
    assert res2.status_code == 409
    assert res2.json()["error"]["code"] == "BUDGET_ALREADY_EXISTS"

async def test_create_budget_invalid_category(client: AsyncClient, auth_headers: dict):
    payload = {
        "category_id": str(uuid.uuid4()),
        "limit_amount": 500.00,
        "month": 6,
        "year": 2026
    }
    response = await client.post("/api/v1/budgets", json=payload, headers=auth_headers)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "CATEGORY_NOT_FOUND"

async def test_list_budgets(client: AsyncClient, auth_headers: dict, uow: SQLAlchemyUnitOfWork):
    async with uow:
        categories = await uow.categories.get_all_accessible(uuid.uuid4())
        food_cat = next(c for c in categories if c.name == "Food")
        transport_cat = next(c for c in categories if c.name == "Transport")
        food_cat_id = food_cat.id
        transport_cat_id = transport_cat.id

    # Create two budgets
    await client.post("/api/v1/budgets", json={
        "category_id": str(food_cat_id),
        "limit_amount": 200.00,
        "month": 6,
        "year": 2026
    }, headers=auth_headers)

    await client.post("/api/v1/budgets", json={
        "category_id": str(transport_cat_id),
        "limit_amount": 100.00,
        "month": 6,
        "year": 2026
    }, headers=auth_headers)

    # List budgets
    response = await client.get("/api/v1/budgets?month=6&year=2026", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    
    # Check other period - should be empty
    response_empty = await client.get("/api/v1/budgets?month=7&year=2026", headers=auth_headers)
    assert response_empty.status_code == 200
    assert len(response_empty.json()) == 0

async def test_update_budget(client: AsyncClient, auth_headers: dict, uow: SQLAlchemyUnitOfWork):
    async with uow:
        categories = await uow.categories.get_all_accessible(uuid.uuid4())
        food_cat = next(c for c in categories if c.name == "Food")
        food_cat_id = food_cat.id

    create_res = await client.post("/api/v1/budgets", json={
        "category_id": str(food_cat_id),
        "limit_amount": 200.00,
        "month": 6,
        "year": 2026
    }, headers=auth_headers)
    budget_id = create_res.json()["id"]

    # Update limit
    update_res = await client.patch(
        f"/api/v1/budgets/{budget_id}",
        json={"limit_amount": 350.00, "alert_threshold": 0.90},
        headers=auth_headers
    )
    assert update_res.status_code == 200
    updated_data = update_res.json()
    assert float(updated_data["limit_amount"]) == 350.00
    assert float(updated_data["alert_threshold"]) == 0.90

async def test_delete_budget(client: AsyncClient, auth_headers: dict, uow: SQLAlchemyUnitOfWork):
    async with uow:
        categories = await uow.categories.get_all_accessible(uuid.uuid4())
        food_cat = next(c for c in categories if c.name == "Food")
        food_cat_id = food_cat.id

    create_res = await client.post("/api/v1/budgets", json={
        "category_id": str(food_cat_id),
        "limit_amount": 200.00,
        "month": 6,
        "year": 2026
    }, headers=auth_headers)
    budget_id = create_res.json()["id"]

    delete_res = await client.delete(f"/api/v1/budgets/{budget_id}", headers=auth_headers)
    assert delete_res.status_code == 204

    # Verify deleted
    async with uow:
        budget = await uow.budgets.get(uuid.UUID(budget_id))
        assert budget is None

async def test_budget_isolation(client: AsyncClient, auth_headers: dict, other_auth_headers: dict, uow: SQLAlchemyUnitOfWork):
    async with uow:
        categories = await uow.categories.get_all_accessible(uuid.uuid4())
        food_cat = next(c for c in categories if c.name == "Food")
        food_cat_id = food_cat.id

    # Create budget for User 1
    create_res = await client.post("/api/v1/budgets", json={
        "category_id": str(food_cat_id),
        "limit_amount": 200.00,
        "month": 6,
        "year": 2026
    }, headers=auth_headers)
    budget_id = create_res.json()["id"]

    # User 2 lists budgets - should not see User 1's budget
    list_res = await client.get("/api/v1/budgets?month=6&year=2026", headers=other_auth_headers)
    assert len(list_res.json()) == 0

    # User 2 updates User 1's budget - should return 404
    update_res = await client.patch(
        f"/api/v1/budgets/{budget_id}",
        json={"limit_amount": 500.00},
        headers=other_auth_headers
    )
    assert update_res.status_code == 404

    # User 2 deletes User 1's budget - should return 404
    delete_res = await client.delete(f"/api/v1/budgets/{budget_id}", headers=other_auth_headers)
    assert delete_res.status_code == 404

async def test_budget_summary(client: AsyncClient, auth_headers: dict, uow: SQLAlchemyUnitOfWork, test_user):
    async with uow:
        categories = await uow.categories.get_all_accessible(uuid.uuid4())
        food_cat = next(c for c in categories if c.name == "Food")
        food_cat_id = food_cat.id

    # 1. Create a budget for Food (limit = 100)
    await client.post("/api/v1/budgets", json={
        "category_id": str(food_cat_id),
        "limit_amount": 100.00,
        "month": 6,
        "year": 2026
    }, headers=auth_headers)

    # 2. Add an expense transaction under Food for 35.50
    # Note: we use unified transaction router POST /transactions
    tx_payload = {
        "transaction_type": "expense",
        "amount": 35.50,
        "currency": "USD",
        "category_id": str(food_cat_id),
        "description": "Groceries",
        "transaction_date": "2026-06-15",
        "payment_method": "cash"
    }
    tx_res = await client.post("/api/v1/transactions", json=tx_payload, headers=auth_headers)
    assert tx_res.status_code == 201

    # 3. Get budget summary and assert values
    summary_res = await client.get("/api/v1/budgets/summary?month=6&year=2026", headers=auth_headers)
    assert summary_res.status_code == 200
    data = summary_res.json()
    assert len(data) == 1
    
    food_summary = data[0]
    assert food_summary["category_name"] == "Food"
    assert float(food_summary["limit_amount"]) == 100.00
    assert float(food_summary["spent_amount"]) == 35.50
    assert food_summary["percentage"] == 0.355

    # 4. Add another expense under Food for 45.00
    await client.post("/api/v1/transactions", json={
        "transaction_type": "expense",
        "amount": 45.00,
        "currency": "USD",
        "category_id": str(food_cat_id),
        "description": "Dinner",
        "transaction_date": "2026-06-20",
        "payment_method": "credit_card"
    }, headers=auth_headers)

    # 5. Add an income transaction (should NOT affect spent_amount)
    await client.post("/api/v1/transactions", json={
        "transaction_type": "income",
        "amount": 1000.00,
        "currency": "USD",
        "category_id": str(food_cat_id),
        "description": "Salary",
        "transaction_date": "2026-06-01",
        "payment_method": "bank_transfer"
    }, headers=auth_headers)

    # 6. Re-check budget summary (should show 35.50 + 45.00 = 80.50 spent)
    summary_res = await client.get("/api/v1/budgets/summary?month=6&year=2026", headers=auth_headers)
    data = summary_res.json()
    food_summary = data[0]
    assert float(food_summary["spent_amount"]) == 80.50
    assert food_summary["percentage"] == 0.805
