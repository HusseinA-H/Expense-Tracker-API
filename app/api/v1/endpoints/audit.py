import uuid
from datetime import datetime
from typing import List, Optional

import structlog
from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_audit_service, require_admin
from app.models.user import User
from app.schemas.audit import AuditLogResponse
from app.services.audit_service import AuditService

router = APIRouter()
logger = structlog.get_logger("app.api.audit")


@router.get("/logs", response_model=List[AuditLogResponse])
async def list_audit_logs(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    user_id: Optional[uuid.UUID] = Query(default=None),
    action: Optional[str] = Query(default=None),
    entity_type: Optional[str] = Query(default=None),
    entity_id: Optional[uuid.UUID] = Query(default=None),
    request_id: Optional[str] = Query(default=None),
    date_from: Optional[datetime] = Query(default=None),
    date_to: Optional[datetime] = Query(default=None),
    current_user: User = Depends(require_admin),
    audit_service: AuditService = Depends(get_audit_service),
):
    """Retrieve system-wide audit logs with pagination and filtering. Restricted to Admins."""
    logger.info(
        "Audit logs requested",
        admin_user_id=str(current_user.id),
        page=page,
        per_page=per_page,
    )

    logs, _ = await audit_service.get_audit_logs(
        page=page,
        per_page=per_page,
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        request_id=request_id,
        date_from=date_from,
        date_to=date_to,
    )
    return logs
