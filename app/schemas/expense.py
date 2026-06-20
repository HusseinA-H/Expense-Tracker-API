import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class ExpenseBase(BaseModel):
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    category_id: uuid.UUID
    description: Optional[str] = Field(default=None, max_length=500)
    expense_date: date
    payment_method: str = Field(default="cash", max_length=20)
    tags: List[str] = Field(default_factory=list)
    receipt_url: Optional[str] = Field(default=None, max_length=500)
    is_recurring: bool = False

    @field_validator("payment_method")
    @classmethod
    def validate_payment_method(cls, v: str) -> str:
        v_lower = v.lower()
        if v_lower not in (
            "cash",
            "credit_card",
            "debit_card",
            "bank_transfer",
            "other",
        ):
            raise ValueError(
                "Payment method must be one of: cash, credit_card, debit_card, bank_transfer, other"
            )
        return v_lower

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        v_upper = v.upper()
        if not v_upper.isalpha():
            raise ValueError("Currency must contain only letters")
        return v_upper


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseUpdate(BaseModel):
    amount: Optional[Decimal] = Field(default=None, gt=0, decimal_places=2)
    currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    category_id: Optional[uuid.UUID] = None
    description: Optional[str] = Field(default=None, max_length=500)
    expense_date: Optional[date] = None
    payment_method: Optional[str] = None
    tags: Optional[List[str]] = None
    receipt_url: Optional[str] = Field(default=None, max_length=500)
    is_recurring: Optional[bool] = None

    @field_validator("payment_method")
    @classmethod
    def validate_payment_method(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v_lower = v.lower()
            if v_lower not in (
                "cash",
                "credit_card",
                "debit_card",
                "bank_transfer",
                "other",
            ):
                raise ValueError(
                    "Payment method must be one of: cash, credit_card, debit_card, bank_transfer, other"
                )
            return v_lower
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v_upper = v.upper()
            if not v_upper.isalpha():
                raise ValueError("Currency must contain only letters")
            return v_upper
        return v


class ExpenseResponse(ExpenseBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {Decimal: lambda v: float(v)}
