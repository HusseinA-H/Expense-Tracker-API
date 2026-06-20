import uuid
from datetime import datetime
from typing import List, Tuple, Optional
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit_log import AuditLog
from app.repositories.base import BaseRepository

class AuditRepository(BaseRepository[AuditLog]):
    """Repository handling AuditLog database queries (Append-only)."""

    def __init__(self, session: AsyncSession):
        super().__init__(AuditLog, session)

    def _build_filter_stmt(
        self,
        user_id: Optional[uuid.UUID] = None,
        action: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[uuid.UUID] = None,
        request_id: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ):
        """Helper to build where clauses for filtering audit logs."""
        clauses = []
        if user_id is not None:
            clauses.append(AuditLog.user_id == user_id)
        if action is not None:
            clauses.append(AuditLog.action == action)
        if entity_type is not None:
            clauses.append(AuditLog.entity_type == entity_type)
        if entity_id is not None:
            clauses.append(AuditLog.entity_id == entity_id)
        if request_id is not None:
            clauses.append(AuditLog.request_id == request_id)
        if date_from is not None:
            clauses.append(AuditLog.created_at >= date_from)
        if date_to is not None:
            clauses.append(AuditLog.created_at <= date_to)
        return clauses

    async def get_filtered(
        self,
        page: int = 1,
        per_page: int = 20,
        user_id: Optional[uuid.UUID] = None,
        action: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[uuid.UUID] = None,
        request_id: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> List[AuditLog]:
        """Fetch list of audit logs satisfying filters with pagination."""
        offset = (page - 1) * per_page
        clauses = self._build_filter_stmt(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            request_id=request_id,
            date_from=date_from,
            date_to=date_to
        )
        
        stmt = (
            select(AuditLog)
            .where(and_(*clauses) if clauses else True)
            .order_by(AuditLog.created_at.desc())
            .offset(offset)
            .limit(per_page)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_filtered(
        self,
        user_id: Optional[uuid.UUID] = None,
        action: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[uuid.UUID] = None,
        request_id: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> int:
        """Count total audit logs matching filters."""
        clauses = self._build_filter_stmt(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            request_id=request_id,
            date_from=date_from,
            date_to=date_to
        )
        
        stmt = (
            select(func.count())
            .select_from(AuditLog)
            .where(and_(*clauses) if clauses else True)
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0
