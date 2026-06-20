import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token import RefreshToken
from app.repositories.base import BaseRepository


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    """Repository handling RefreshToken queries."""

    def __init__(self, session: AsyncSession):
        super().__init__(RefreshToken, session)

    async def get_by_token_hash(self, token_hash: str) -> RefreshToken | None:
        """Fetch a refresh token by its hashed value."""
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_expired_and_revoked(self) -> int:
        """Delete refresh tokens that are expired or revoked."""
        now = datetime.now(timezone.utc)
        stmt = delete(RefreshToken).where(
            or_(
                RefreshToken.expires_at < now,
                RefreshToken.revoked_at.is_not(None),
            )
        )
        result = await self.session.execute(stmt)
        return result.rowcount or 0

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> int:
        """Revoke all active refresh tokens for a user."""
        now = datetime.now(timezone.utc)
        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
        result = await self.session.execute(stmt)
        return result.rowcount or 0
