import uuid
import pytest
from httpx import AsyncClient
from app.models.category import Category
from app.db.unit_of_work import SQLAlchemyUnitOfWork

pytestmark = pytest.mark.asyncio

async def test_list_categories(client: AsyncClient, auth_headers: dict, test_user: dict):
    # Retrieve categories
    response = await client.get("/api/v1/categories", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    
    # We should have the 9 system categories seeded
    assert len(data) >= 9
    system_cat_names = [c["name"] for c in data if c["is_system"]]
    assert "Food" in system_cat_names
    assert "Transport" in system_cat_names

async def test_create_category(client: AsyncClient, auth_headers: dict, uow: SQLAlchemyUnitOfWork, test_user):
    payload = {
        "name": "Subscriptions",
        "icon": "card",
        "color": "#123456"
    }
    response = await client.post("/api/v1/categories", json=payload, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Subscriptions"
    assert data["is_system"] is False
    assert data["user_id"] == str(test_user.id)
    
    # Verify in DB
    async with uow:
        category = await uow.categories.get(uuid.UUID(data["id"]))
        assert category is not None
        assert category.name == "Subscriptions"

async def test_create_duplicate_category(client: AsyncClient, auth_headers: dict):
    payload = {
        "name": "Food",  # Already exists as a system category
        "icon": "utensils",
        "color": "#FF5733"
    }
    response = await client.post("/api/v1/categories", json=payload, headers=auth_headers)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CATEGORY_ALREADY_EXISTS"

async def test_update_category(client: AsyncClient, auth_headers: dict, uow: SQLAlchemyUnitOfWork, test_user):
    # First create a custom category
    payload = {
        "name": "Custom Cat",
        "icon": "icon",
        "color": "#112233"
    }
    create_response = await client.post("/api/v1/categories", json=payload, headers=auth_headers)
    cat_id = create_response.json()["id"]
    
    # Update it
    update_payload = {
        "name": "Updated Cat",
        "color": "#778899"
    }
    update_response = await client.patch(f"/api/v1/categories/{cat_id}", json=update_payload, headers=auth_headers)
    assert update_response.status_code == 200
    updated_data = update_response.json()
    assert updated_data["name"] == "Updated Cat"
    assert updated_data["color"] == "#778899"

async def test_update_system_category_forbidden(client: AsyncClient, auth_headers: dict, uow: SQLAlchemyUnitOfWork):
    # Find a system category
    async with uow:
        categories = await uow.categories.get_all_accessible(uuid.uuid4()) # any uuid works since system cats are fetched
        system_cat = next(c for c in categories if c.is_system)
        system_cat_id = system_cat.id
        
    response = await client.patch(
        f"/api/v1/categories/{system_cat_id}",
        json={"name": "New System Name"},
        headers=auth_headers
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"

async def test_delete_category(client: AsyncClient, auth_headers: dict, uow: SQLAlchemyUnitOfWork):
    # First create custom category
    payload = {
        "name": "To Delete",
        "icon": "bin",
        "color": "#990000"
    }
    create_response = await client.post("/api/v1/categories", json=payload, headers=auth_headers)
    cat_id = create_response.json()["id"]
    
    # Delete it
    delete_response = await client.delete(f"/api/v1/categories/{cat_id}", headers=auth_headers)
    assert delete_response.status_code == 204
    
    # Verify in DB it is gone
    async with uow:
        category = await uow.categories.get(uuid.UUID(cat_id))
        assert category is None

async def test_delete_system_category_forbidden(client: AsyncClient, auth_headers: dict, uow: SQLAlchemyUnitOfWork):
    async with uow:
        categories = await uow.categories.get_all_accessible(uuid.uuid4())
        system_cat = next(c for c in categories if c.is_system)
        system_cat_id = system_cat.id
        
    response = await client.delete(f"/api/v1/categories/{system_cat_id}", headers=auth_headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"

async def test_category_isolation(client: AsyncClient, auth_headers: dict, other_auth_headers: dict):
    # User 1 creates a custom category
    payload = {
        "name": "User 1 Private",
        "icon": "lock",
        "color": "#111111"
    }
    create_response = await client.post("/api/v1/categories", json=payload, headers=auth_headers)
    cat_id = create_response.json()["id"]
    
    # User 2 lists categories - should NOT see User 1's custom category
    list_response = await client.get("/api/v1/categories", headers=other_auth_headers)
    data = list_response.json()
    user2_cat_names = [c["name"] for c in data]
    assert "User 1 Private" not in user2_cat_names
    
    # User 2 attempts to update User 1's custom category - should fail with NotFound
    update_response = await client.patch(
        f"/api/v1/categories/{cat_id}",
        json={"name": "Hack Attempt"},
        headers=other_auth_headers
    )
    assert update_response.status_code == 404
    
    # User 2 attempts to delete User 1's custom category - should fail with NotFound
    delete_response = await client.delete(f"/api/v1/categories/{cat_id}", headers=other_auth_headers)
    assert delete_response.status_code == 404
