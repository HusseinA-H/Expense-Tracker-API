import datetime
import structlog
import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, status, Response
from fastapi.security import OAuth2PasswordRequestForm
from app.api.deps import get_auth_service, oauth2_scheme, get_redis
from app.services.auth_service import AuthService
from app.schemas.user import UserCreate, UserResponse
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    PasswordResetRequest,
    PasswordResetConfirmRequest,
)
from app.core.security import verify_access_token

router = APIRouter()
logger = structlog.get_logger("app.api.auth")

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: UserCreate,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Register a new user account."""
    user = await auth_service.register_user(data)
    return user

@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Authenticate credentials and return access and refresh tokens (JSON body)."""
    tokens = await auth_service.login_user(data)
    return tokens


@router.post("/token", response_model=TokenResponse)
async def login_oauth2_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service),
):
    """OAuth2 password grant token endpoint (form-urlencoded).

    Used by Swagger UI Authorize and other OAuth2 clients.
    Submit the user's **email** in the `username` field.
    """
    tokens = await auth_service.login_user(
        LoginRequest(email=form_data.username, password=form_data.password)
    )
    return tokens

@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    data: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Rotate the refresh token and return a new token pair."""
    tokens = await auth_service.rotate_refresh_token(data.refresh_token)
    return tokens

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    data: RefreshTokenRequest,
    token: str = Depends(oauth2_scheme),
    auth_service: AuthService = Depends(get_auth_service),
    redis: aioredis.Redis = Depends(get_redis)
):
    """Log out user by blacklisting access token and revoking refresh token."""
    # 1. Revoke refresh token in database
    await auth_service.logout_user(data.refresh_token)
    
    # 2. Blacklist access token in Redis
    try:
        payload = verify_access_token(token)
        now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        remaining_ttl = payload.exp - now
        if remaining_ttl > 0:
            await redis.setex(f"blacklist:{payload.jti}", remaining_ttl, "true")
            logger.info("Access token blacklisted on logout", jti=payload.jti, ttl=remaining_ttl)
    except Exception as e:
        logger.warning("Could not blacklist access token on logout", error=str(e))
        
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/password-reset/request", status_code=status.HTTP_204_NO_CONTENT)
async def request_password_reset(
    data: PasswordResetRequest,
    auth_service: AuthService = Depends(get_auth_service),
    redis: aioredis.Redis = Depends(get_redis),
):
    """Request a password reset email. Always returns 204."""
    await auth_service.request_password_reset(data.email, redis)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/password-reset/confirm", status_code=status.HTTP_204_NO_CONTENT)
async def confirm_password_reset(
    data: PasswordResetConfirmRequest,
    auth_service: AuthService = Depends(get_auth_service),
    redis: aioredis.Redis = Depends(get_redis),
):
    """Confirm password reset with token and new password."""
    await auth_service.confirm_password_reset(
        data.email, data.token, data.new_password, redis
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
