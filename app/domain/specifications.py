import uuid
from abc import ABC, abstractmethod
from datetime import date
from sqlalchemy import and_, or_
from app.models.transaction import Transaction

class Specification(ABC):
    """Abstract base class for Specification pattern."""

    @abstractmethod
    def to_expression(self):
        """Convert specification to SQLAlchemy filter expression."""
        pass

    def __and__(self, other: "Specification") -> "AndSpecification":
        return AndSpecification(self, other)

    def __or__(self, other: "Specification") -> "OrSpecification":
        return OrSpecification(self, other)


class AndSpecification(Specification):
    """Combines two specifications with an AND operator."""

    def __init__(self, spec1: Specification, spec2: Specification):
        self.spec1 = spec1
        self.spec2 = spec2

    def to_expression(self):
        return and_(self.spec1.to_expression(), self.spec2.to_expression())


class OrSpecification(Specification):
    """Combines two specifications with an OR operator."""

    def __init__(self, spec1: Specification, spec2: Specification):
        self.spec1 = spec1
        self.spec2 = spec2

    def to_expression(self):
        return or_(self.spec1.to_expression(), self.spec2.to_expression())


class TransactionByUser(Specification):
    """Filter transactions by user ID."""

    def __init__(self, user_id: uuid.UUID):
        self.user_id = user_id

    def to_expression(self):
        return Transaction.user_id == self.user_id


class TransactionInDateRange(Specification):
    """Filter transactions within a date range (inclusive)."""

    def __init__(self, date_from: date | None, date_to: date | None):
        self.date_from = date_from
        self.date_to = date_to

    def to_expression(self):
        expressions = []
        if self.date_from is not None:
            expressions.append(Transaction.transaction_date >= self.date_from)
        if self.date_to is not None:
            expressions.append(Transaction.transaction_date <= self.date_to)
        return and_(*expressions) if expressions else True


class TransactionByType(Specification):
    """Filter transactions by classification type (expense, income, transfer)."""

    def __init__(self, transaction_type: str | None):
        self.transaction_type = transaction_type

    def to_expression(self):
        if self.transaction_type is None:
            return True
        return Transaction.transaction_type == self.transaction_type


class TransactionByCategory(Specification):
    """Filter transactions by category ID."""

    def __init__(self, category_id: uuid.UUID | None):
        self.category_id = category_id

    def to_expression(self):
        if self.category_id is None:
            return True
        return Transaction.category_id == self.category_id


class TransactionByAmountRange(Specification):
    """Filter transactions by numeric amount range."""

    def __init__(self, min_amount: float | None, max_amount: float | None):
        self.min_amount = min_amount
        self.max_amount = max_amount

    def to_expression(self):
        expressions = []
        if self.min_amount is not None:
            expressions.append(Transaction.amount >= self.min_amount)
        if self.max_amount is not None:
            expressions.append(Transaction.amount <= self.max_amount)
        return and_(*expressions) if expressions else True


class NotDeleted(Specification):
    """Filter out soft-deleted records."""

    def to_expression(self):
        return Transaction.deleted_at.is_(None)
