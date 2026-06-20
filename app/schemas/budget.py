import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class BudgetBase(BaseModel):
    category_id: uuid.UUID
    limit_amount: Decimal = Field(..., gt=0, decimal_places=2)
    month: int = Field(..., ge=1, le=12)
    year: int = Field(..., ge=2020)
    alert_threshold: Decimal = Field(
        default=Decimal("0.80"), gt=0, le=1.00, decimal_places=2
    )


class BudgetCreate(BudgetBase):
    pass


class BudgetUpdate(BaseModel):
    limit_amount: Optional[Decimal] = Field(default=None, gt=0, decimal_places=2)
    alert_threshold: Optional[Decimal] = Field(
        default=None, gt=0, le=1.00, decimal_places=2
    )


class BudgetResponse(BudgetBase):
    id: uuid.UUID
    user_id: uuid.UUID
    alert_sent: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {Decimal: lambda v: float(v)}


class BudgetSummaryResponse(BaseModel):
    id: uuid.UUID
    category_id: uuid.UUID
    category_name: str
    limit_amount: Decimal
    spent_amount: Decimal
    percentage: float
    month: int
    year: int
    alert_threshold: float
    alert_sent: bool

    class Config:
        from_attributes = True
        json_encoders = {Decimal: lambda v: float(v)}
