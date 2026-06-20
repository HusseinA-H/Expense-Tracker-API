import uuid

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Category(Base, UUIDMixin, TimestampMixin):
    """Category database model."""

    __tablename__ = "categories"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)
    color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    is_system: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Relationships
    user = relationship("User", back_populates="categories")
    transactions = relationship("Transaction", back_populates="category")
    budgets = relationship(
        "Budget", back_populates="category", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("name", "user_id", name="uq_categories_name_user_id"),
    )
