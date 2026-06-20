import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Expense(Base):
    """SQLAlchemy model for the legacy expenses view (Read-only view over transactions)."""

    __tablename__ = "expenses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id")
    )
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3))
    description: Mapped[str | None] = mapped_column(String(500))
    expense_date: Mapped[date] = mapped_column(Date)
    payment_method: Mapped[str] = mapped_column(String(20))
    receipt_url: Mapped[str | None] = mapped_column(String(500))
    is_recurring: Mapped[bool] = mapped_column(Boolean)
    tags: Mapped[list] = mapped_column(JSONB)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    # Relationships
    user = relationship("User", viewonly=True)
    category = relationship("Category", viewonly=True)
