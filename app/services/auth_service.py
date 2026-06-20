import hashlib
import uuid
from datetime import datetime, timedelta, timezone
import structlog
from app.config import settings
from app.core.exceptions import AuthenticationError, ConflictError
from app.core.security import (
    create_access_token,
    generate_opaque_token,
    hash_password,
    verify_password,
)
from app.db.unit_of_work import SQLAlchemyUnitOfWork
from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.user import UserCreate

logger = structlog.get_logger("app.services.auth")

def _hash_token(token: str) -> str:
    """Hash a high-entropy string using SHA-256 for fast lookup and storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

class AuthService:
    """Service handling registration, login, token rotation, and logout business logic."""

    def __init__(self, uow: SQLAlchemyUnitOfWork):
        self.uow = uow

    async def register_user(self, data: UserCreate) -> User:
        """Register a new user in the system."""
        async with self.uow:
            # Check if user already exists
            existing_user = await self.uow.users.get_by_email(data.email)
            if existing_user:
                raise ConflictError(
                    message=f"A user with email {data.email} already exists.",
                    error_code="EMAIL_ALREADY_EXISTS"
                )

            # Create User object
            hashed_pwd = hash_password(data.password)
            user = User(
                email=data.email,
                hashed_password=hashed_pwd,
                first_name=data.first_name,
                last_name=data.last_name,
                preferred_currency=data.preferred_currency,
            )

            await self.uow.users.add(user)
            await self.uow.commit()
            await self.uow.refresh(user)

            try:
                from app.events.base import event_bus
                from app.events.definitions import UserRegistered
                await event_bus.publish(
                    UserRegistered(
                        user_id=user.id,
                        email=user.email
                    )
                )
            except Exception as e:
                logger.error("Failed to publish UserRegistered event", error=str(e), exc_info=True)
            
            logger.info("User registered successfully", email=user.email, user_id=str(user.id))
            return user

    async def login_user(self, data: LoginRequest) -> TokenResponse:
        """Authenticate user credentials and issue access + refresh tokens."""
        async with self.uow:
            user = await self.uow.users.get_by_email(data.email)
            if not user or not verify_password(data.password, user.hashed_password):
                raise AuthenticationError(
                    message="Invalid email or password.",
                    error_code="INVALID_CREDENTIALS"
                )

            if not user.is_active:
                raise AuthenticationError(
                    message="User account is deactivated.",
                    error_code="USER_INACTIVE"
                )

            # 1. Generate access token
            access_token = create_access_token(user_id=user.id, role=user.role, email=user.email)

            # 2. Generate and store refresh token
            raw_refresh_token = generate_opaque_token()
            token_hash = _hash_token(raw_refresh_token)
            expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

            refresh_token_obj = RefreshToken(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=expires_at,
            )
            await self.uow.refresh_tokens.add(refresh_token_obj)
            await self.uow.commit()

            try:
                from app.events.base import event_bus
                from app.events.definitions import UserLoggedIn
                ctx = structlog.contextvars.get_contextvars()
                ip_addr = ctx.get("ip_address") or "unknown"
                ua = ctx.get("user_agent") or "unknown"
                await event_bus.publish(
                    UserLoggedIn(
                        user_id=user.id,
                        ip_address=ip_addr,
                        user_agent=ua
                    )
                )
            except Exception as e:
                logger.error("Failed to publish UserLoggedIn event", error=str(e), exc_info=True)

            logger.info("User logged in successfully", user_id=str(user.id))
            return TokenResponse(
                access_token=access_token,
                refresh_token=raw_refresh_token,
            )

    async def rotate_refresh_token(self, refresh_token: str) -> TokenResponse:
        """Verify refresh token, invalidate it, and issue a new pair (Refresh Token Rotation)."""
        token_hash = _hash_token(refresh_token)
        
        async with self.uow:
            token_record = await self.uow.refresh_tokens.get_by_token_hash(token_hash)
            if (
                not token_record
                or token_record.revoked_at is not None
                or token_record.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc)
            ):
                raise AuthenticationError(
                    message="Refresh token is invalid, expired, or has been revoked.",
                    error_code="TOKEN_INVALID"
                )

            user = await self.uow.users.get(token_record.user_id)
            if not user or not user.is_active:
                raise AuthenticationError(
                    message="Associated user is inactive or not found.",
                    error_code="INVALID_CREDENTIALS"
                )

            # Revoke current token
            token_record.revoked_at = datetime.now(timezone.utc)
            await self.uow.refresh_tokens.update(token_record)

            # Generate new access token
            access_token = create_access_token(user_id=user.id, role=user.role, email=user.email)

            # Generate new refresh token
            new_raw_refresh = generate_opaque_token()
            new_hash = _hash_token(new_raw_refresh)
            expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

            new_refresh_record = RefreshToken(
                user_id=user.id,
                token_hash=new_hash,
                expires_at=expires_at,
            )
            await self.uow.refresh_tokens.add(new_refresh_record)
            await self.uow.commit()

            logger.info("Refresh token rotated successfully", user_id=str(user.id))
            return TokenResponse(
                access_token=access_token,
                refresh_token=new_raw_refresh,
            )

    async def logout_user(self, refresh_token: str) -> None:
        """Revoke the refresh token on logout."""
        token_hash = _hash_token(refresh_token)
        async with self.uow:
            token_record = await self.uow.refresh_tokens.get_by_token_hash(token_hash)
            if token_record and token_record.revoked_at is None:
                token_record.revoked_at = datetime.now(timezone.utc)
                await self.uow.refresh_tokens.update(token_record)
                await self.uow.commit()
                logger.info("Refresh token revoked on logout", user_id=str(token_record.user_id))
            else:
                logger.warning("Attempted to logout with invalid or already revoked refresh token")

    async def request_password_reset(self, email: str, redis) -> None:
        """Issue a password reset token and dispatch the reset email.

        Always completes silently to avoid email enumeration.
        """
        async with self.uow:
            user = await self.uow.users.get_by_email(email)

        if not user or not user.is_active:
            logger.info(
                "Password reset requested for unknown or inactive account",
                email=email,
            )
            return

        raw_token = generate_opaque_token()
        token_hash = _hash_token(raw_token)
        ttl_seconds = settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES * 60
        redis_key = f"password_reset:{token_hash}"

        await redis.setex(redis_key, ttl_seconds, str(user.id))

        try:
            from app.tasks.email_tasks import send_password_reset_email

            send_password_reset_email.delay(user.email, raw_token)
            logger.info("Password reset email dispatched", user_id=str(user.id))
        except Exception as exc:
            await redis.delete(redis_key)
            logger.error(
                "Failed to dispatch password reset email",
                user_id=str(user.id),
                error=str(exc),
                exc_info=True,
            )

    async def confirm_password_reset(
        self, email: str, token: str, new_password: str, redis
    ) -> None:
        """Validate reset token and set a new password."""
        token_hash = _hash_token(token)
        redis_key = f"password_reset:{token_hash}"
        stored_user_id = await redis.get(redis_key)

        async with self.uow:
            user = await self.uow.users.get_by_email(email)
            if (
                not user
                or not user.is_active
                or not stored_user_id
                or stored_user_id != str(user.id)
            ):
                raise AuthenticationError(
                    message="Invalid or expired password reset token.",
                    error_code="RESET_TOKEN_INVALID",
                )

            user.hashed_password = hash_password(new_password)
            await self.uow.users.update(user)
            await self.uow.refresh_tokens.revoke_all_for_user(user.id)
            await self.uow.commit()

        await redis.delete(redis_key)

        try:
            from app.events.base import event_bus
            from app.events.definitions import PasswordChanged

            await event_bus.publish(PasswordChanged(user_id=user.id))
        except Exception as exc:
            logger.error(
                "Failed to publish PasswordChanged event",
                user_id=str(user.id),
                error=str(exc),
                exc_info=True,
            )

        logger.info("Password reset confirmed", user_id=str(user.id))
