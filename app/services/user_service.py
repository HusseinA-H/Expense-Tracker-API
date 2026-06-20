import uuid
from typing import List, Tuple

import structlog

from app.core.exceptions import AuthenticationError, ConflictError, NotFoundError
from app.core.security import hash_password, verify_password
from app.db.unit_of_work import SQLAlchemyUnitOfWork
from app.models.user import User
from app.schemas.user import UserUpdate

logger = structlog.get_logger("app.services.user")


class UserService:
    """Service handling user profile updates, password changes, deactivations, and admin lookups."""

    def __init__(self, uow: SQLAlchemyUnitOfWork):
        self.uow = uow

    async def update_profile(self, user_id: uuid.UUID, data: UserUpdate) -> User:
        """Update user profile fields."""
        async with self.uow:
            user = await self.uow.users.get(user_id)
            if not user:
                raise NotFoundError(
                    message="User not found.", error_code="USER_NOT_FOUND"
                )

            # Apply fields that are provided
            update_data = data.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(user, field, value)

            await self.uow.users.update(user)
            await self.uow.commit()

            logger.info("User profile updated", user_id=str(user.id))
            return user

    async def change_password(
        self, user_id: uuid.UUID, current_password: str, new_password: str
    ) -> User:
        """Change the password for the current user after validating their old password."""
        async with self.uow:
            user = await self.uow.users.get(user_id)
            if not user:
                raise NotFoundError(
                    message="User not found.", error_code="USER_NOT_FOUND"
                )

            # Verify current password
            if not verify_password(current_password, user.hashed_password):
                raise AuthenticationError(
                    message="Incorrect current password.",
                    error_code="INVALID_CREDENTIALS",
                )

            # Update password
            user.hashed_password = hash_password(new_password)
            await self.uow.users.update(user)
            await self.uow.commit()

            try:
                from app.events.base import event_bus
                from app.events.definitions import PasswordChanged

                await event_bus.publish(PasswordChanged(user_id=user.id))
            except Exception as e:
                logger.error(
                    "Failed to publish PasswordChanged event",
                    error=str(e),
                    exc_info=True,
                )

            logger.info("User password changed successfully", user_id=str(user.id))
            return user

    async def deactivate_account(self, user_id: uuid.UUID) -> None:
        """Soft-deactivate a user account."""
        async with self.uow:
            user = await self.uow.users.get(user_id)
            if not user:
                raise NotFoundError(
                    message="User not found.", error_code="USER_NOT_FOUND"
                )

            user.is_active = False
            await self.uow.users.update(user)
            await self.uow.commit()

            try:
                from app.events.base import event_bus
                from app.events.definitions import UserDeactivated

                await event_bus.publish(UserDeactivated(user_id=user.id))
            except Exception as e:
                logger.error(
                    "Failed to publish UserDeactivated event",
                    error=str(e),
                    exc_info=True,
                )

            logger.info("User account deactivated", user_id=str(user.id))

    async def list_users(
        self, page: int = 1, per_page: int = 20
    ) -> Tuple[List[User], int]:
        """List users in the system (Admin only). Returns (items, total_count)."""
        async with self.uow:
            users = await self.uow.users.get_multi(page=page, per_page=per_page)
            total = await self.uow.users.count()
            return users, total
