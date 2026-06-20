import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class AuditLogResponse(BaseModel):
    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    action: str
    entity_type: str
    entity_id: Optional[uuid.UUID] = None
    old_data: Optional[Dict[str, Any]] = None
    new_data: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class AuditLogFilter(BaseModel):
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)
    user_id: Optional[uuid.UUID] = None
    action: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[uuid.UUID] = None
    request_id: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
