import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import AliasChoices, BaseModel, Field, field_validator


class TransactionBase(BaseModel):
    transaction_type: str = Field(..., description="expense, income, or transfer")
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    category_id: Optional[uuid.UUID] = None
    description: Optional[str] = Field(default=None, max_length=500)
    transaction_date: date
    payment_method: str = Field(default="cash", max_length=20)
    receipt_url: Optional[str] = Field(default=None, max_length=500)
    is_recurring: bool = False
    tags: List[str] = Field(default_factory=list)
    tx_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("tx_metadata", "metadata"),
        serialization_alias="metadata",
    )

    @field_validator("transaction_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        v_lower = v.lower()
        if v_lower not in ("expense", "income", "transfer"):
            raise ValueError(
                "Transaction type must be 'expense', 'income', or 'transfer'"
            )
        return v_lower

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


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    transaction_type: Optional[str] = None
    amount: Optional[Decimal] = Field(default=None, gt=0, decimal_places=2)
    currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    category_id: Optional[uuid.UUID] = None
    description: Optional[str] = Field(default=None, max_length=500)
    transaction_date: Optional[date] = None
    payment_method: Optional[str] = None
    receipt_url: Optional[str] = Field(default=None, max_length=500)
    is_recurring: Optional[bool] = None
    tags: Optional[List[str]] = None
    tx_metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        validation_alias=AliasChoices("tx_metadata", "metadata"),
        serialization_alias="metadata",
    )

    @field_validator("transaction_type")
    @classmethod
    def validate_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v_lower = v.lower()
            if v_lower not in ("expense", "income", "transfer"):
                raise ValueError(
                    "Transaction type must be 'expense', 'income', or 'transfer'"
                )
            return v_lower
        return v

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


class TransactionResponse(TransactionBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True
        json_encoders = {Decimal: lambda v: float(v)}
