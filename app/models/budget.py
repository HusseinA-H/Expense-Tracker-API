import uuid
from sqlalchemy import Numeric, Integer, Boolean, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, UUIDMixin, TimestampMixin

class Budget(Base, UUIDMixin, TimestampMixin):
    """Budget database model."""
    __tablename__ = "budgets"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="CASCADE"), nullable=False
    )
    limit_amount: Mapped[float] = mapped_column(
        Numeric(12, 2), nullable=False
    )
    month: Mapped[int] = mapped_column(
        Integer, nullable=False
    )
    year: Mapped[int] = mapped_column(
        Integer, nullable=False
    )
    alert_threshold: Mapped[float] = mapped_column(
        Numeric(3, 2), default=0.80, server_default="0.80", nullable=False
    )
    alert_sent: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="budgets")
    category = relationship("Category", back_populates="budgets")

    __table_args__ = (
        UniqueConstraint("user_id", "category_id", "month", "year", name="uq_budgets_user_cat_period"),
        CheckConstraint("limit_amount > 0", name="ck_budget_limit_positive"),
        CheckConstraint("month >= 1 AND month <= 12", name="ck_budget_month_range"),
        CheckConstraint("year >= 2020", name="ck_budget_year_range"),
        CheckConstraint("alert_threshold > 0 AND alert_threshold <= 1.0", name="ck_budget_threshold_range"),
    )
