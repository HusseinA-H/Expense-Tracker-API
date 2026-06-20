from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Optional
from uuid import UUID

from app.events.base import DomainEvent


@dataclass(frozen=True, kw_only=True)
class UserRegistered(DomainEvent):
    user_id: UUID
    email: str


@dataclass(frozen=True, kw_only=True)
class UserLoggedIn(DomainEvent):
    user_id: UUID
    ip_address: str
    user_agent: str


@dataclass(frozen=True, kw_only=True)
class TransactionCreated(DomainEvent):
    transaction_id: UUID
    user_id: UUID
    transaction_type: str  # expense | income | transfer
    amount: Decimal
    category_id: Optional[UUID]
    currency: str
    transaction_date: date
    description: Optional[str] = None


@dataclass(frozen=True, kw_only=True)
class TransactionUpdated(DomainEvent):
    transaction_id: UUID
    user_id: UUID
    old_data: Dict[str, Any]
    new_data: Dict[str, Any]


@dataclass(frozen=True, kw_only=True)
class TransactionDeleted(DomainEvent):
    transaction_id: UUID
    user_id: UUID


@dataclass(frozen=True, kw_only=True)
class BudgetExceeded(DomainEvent):
    user_id: UUID
    budget_id: UUID
    category_name: str
    limit_amount: Decimal
    spent_amount: Decimal
    percentage: Decimal


@dataclass(frozen=True, kw_only=True)
class ReportGenerated(DomainEvent):
    user_id: UUID
    report_type: str  # monthly_summary | trend | csv_export
    file_url: Optional[str]


@dataclass(frozen=True, kw_only=True)
class PasswordChanged(DomainEvent):
    user_id: UUID


@dataclass(frozen=True, kw_only=True)
class UserDeactivated(DomainEvent):
    user_id: UUID
