import pytest
from httpx import AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_json_login_backward_compatible(client: AsyncClient, test_user):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "password123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]
    assert data["refresh_token"]


@pytest.mark.asyncio
async def test_oauth2_token_login_form(client: AsyncClient, test_user):
    """Swagger Authorize sends application/x-www-form-urlencoded to /auth/token."""
    response = await client.post(
        "/api/v1/auth/token",
        data={"username": test_user.email, "password": "password123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]
    assert data["refresh_token"]


@pytest.mark.asyncio
async def test_oauth2_token_me_after_authorization(client: AsyncClient, test_user):
    login_response = await client.post(
        "/api/v1/auth/token",
        data={"username": test_user.email, "password": "password123"},
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]

    me_response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["email"] == test_user.email
    assert me_response.json()["id"] == str(test_user.id)


@pytest.mark.asyncio
async def test_oauth2_token_invalid_credentials(client: AsyncClient, test_user):
    response = await client.post(
        "/api/v1/auth/token",
        data={"username": test_user.email, "password": "wrong-password"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_openapi_oauth2_token_url():
    schema = app.openapi()
    oauth2 = schema["components"]["securitySchemes"]["OAuth2PasswordBearer"]
    assert oauth2["type"] == "oauth2"
    assert oauth2["flows"]["password"]["tokenUrl"] == "/api/v1/auth/token"
    assert "email" in oauth2["description"].lower()


def test_openapi_users_me_requires_oauth2():
    """Protected routes must declare OAuth2 security so Swagger injects Authorization."""
    schema = app.openapi()
    me_get = schema["paths"]["/api/v1/users/me"]["get"]
    assert {"OAuth2PasswordBearer": []} in me_get["security"]


@pytest.mark.asyncio
async def test_oauth2_swagger_form_with_grant_type(client: AsyncClient, test_user):
    """Swagger UI sends grant_type=password with form-urlencoded credentials."""
    response = await client.post(
        "/api/v1/auth/token",
        data={
            "grant_type": "password",
            "username": test_user.email,
            "password": "password123",
        },
    )
    assert response.status_code == 200
    assert response.json()["access_token"]


@pytest.mark.asyncio
async def test_oauth2_me_without_authorization_header_fails(client: AsyncClient):
    """Without Bearer token, /users/me returns 401 (Swagger must authorize first)."""
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401
