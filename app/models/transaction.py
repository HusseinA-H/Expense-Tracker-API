import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Transaction(Base, UUIDMixin, TimestampMixin):
    """Unified Transaction database model."""

    __tablename__ = "transactions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    transaction_type: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(
        String(3), default="USD", server_default="'USD'", nullable=False
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    payment_method: Mapped[str] = mapped_column(
        String(20), default="cash", server_default="'cash'", nullable=False
    )
    receipt_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_recurring: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    tags: Mapped[list] = mapped_column(
        JSONB, default=list, server_default="'[]'::jsonb", nullable=False
    )
    tx_metadata: Mapped[dict] = mapped_column(
        "metadata", JSONB, default=dict, server_default="'{}'::jsonb", nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    user = relationship("User", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")

    __table_args__ = (
        CheckConstraint(
            "transaction_type IN ('expense', 'income', 'transfer')",
            name="ck_transaction_type",
        ),
        CheckConstraint("amount > 0", name="ck_transaction_amount_positive"),
        Index("ix_txn_user_date", "user_id", "transaction_date"),
        Index("ix_txn_user_type", "user_id", "transaction_type"),
        # Partial index excluding soft-deleted transactions
        Index(
            "ix_txn_active",
            "user_id",
            "transaction_date",
            postgresql_where="deleted_at IS NULL",
        ),
        # GIN index on tags
        Index("ix_txn_tags", "tags", postgresql_using="gin"),
    )
