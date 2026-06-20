import uuid
from datetime import date, datetime, timezone
import structlog
from typing import List, Tuple
from app.core.exceptions import NotFoundError, ValidationError
from app.db.unit_of_work import SQLAlchemyUnitOfWork
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionCreate, TransactionUpdate
from app.domain.specifications import (
    TransactionByUser,
    TransactionByType,
    TransactionByCategory,
    TransactionInDateRange,
    TransactionByAmountRange,
    NotDeleted,
)

logger = structlog.get_logger("app.services.transaction")

class TransactionService:
    """Service handling core transaction CRUD and filtering business logic."""

    def __init__(self, uow: SQLAlchemyUnitOfWork):
        self.uow = uow

    async def create_transaction(self, user_id: uuid.UUID, data: TransactionCreate) -> Transaction:
        """Create a new transaction (expense, income, or transfer)."""
        async with self.uow:
            # 1. Validate category if provided
            if data.category_id is not None:
                category = await self.uow.categories.get_accessible(data.category_id, user_id)
                if not category:
                    raise NotFoundError(
                        message="Category not found or access denied.",
                        error_code="CATEGORY_NOT_FOUND"
                    )
            
            # 2. Check semantic type constraints
            if data.transaction_type == "expense" and data.category_id is None:
                raise ValidationError(
                    message="Expenses must be categorized.",
                    error_code="VALIDATION_ERROR"
                )
            if data.transaction_type == "transfer" and data.category_id is not None:
                raise ValidationError(
                    message="Transfers cannot have a category.",
                    error_code="VALIDATION_ERROR"
                )

            # 3. Create transaction record
            txn = Transaction(
                user_id=user_id,
                transaction_type=data.transaction_type,
                amount=data.amount,
                currency=data.currency,
                category_id=data.category_id,
                description=data.description,
                transaction_date=data.transaction_date,
                payment_method=data.payment_method,
                receipt_url=data.receipt_url,
                is_recurring=data.is_recurring,
                tags=data.tags,
                tx_metadata=data.tx_metadata,
            )
            
            await self.uow.transactions.add(txn)
            await self.uow.commit()
            await self.uow.refresh(txn)
            
            try:
                from app.events.base import event_bus
                from app.events.definitions import TransactionCreated
                await event_bus.publish(
                    TransactionCreated(
                        transaction_id=txn.id,
                        user_id=user_id,
                        transaction_type=txn.transaction_type,
                        amount=txn.amount,
                        category_id=txn.category_id,
                        currency=txn.currency,
                        transaction_date=txn.transaction_date,
                        description=txn.description
                    )
                )
            except Exception as e:
                logger.error("Failed to publish TransactionCreated event", error=str(e), exc_info=True)

            logger.info("Transaction created successfully", user_id=str(user_id), transaction_id=str(txn.id))
            return txn

    async def get_transaction(self, transaction_id: uuid.UUID, user_id: uuid.UUID) -> Transaction:
        """Retrieve a specific active transaction belonging to the user."""
        async with self.uow:
            txn = await self.uow.transactions.get(transaction_id)
            if not txn or txn.user_id != user_id or txn.deleted_at is not None:
                raise NotFoundError(
                    message="Transaction not found.",
                    error_code="TRANSACTION_NOT_FOUND"
                )
            return txn

    async def update_transaction(
        self, transaction_id: uuid.UUID, user_id: uuid.UUID, data: TransactionUpdate
    ) -> Transaction:
        """Perform a partial update on a transaction record."""
        async with self.uow:
            # 1. Fetch record
            txn = await self.uow.transactions.get(transaction_id)
            if not txn or txn.user_id != user_id or txn.deleted_at is not None:
                raise NotFoundError(
                    message="Transaction not found.",
                    error_code="TRANSACTION_NOT_FOUND"
                )

            # 2. Check category validation if changing
            if data.category_id is not None:
                category = await self.uow.categories.get_accessible(data.category_id, user_id)
                if not category:
                    raise NotFoundError(
                        message="Category not found or access denied.",
                        error_code="CATEGORY_NOT_FOUND"
                    )

            # Track old data for event/audit
            old_data = {
                "amount": float(txn.amount),
                "currency": txn.currency,
                "category_id": str(txn.category_id) if txn.category_id else None,
                "description": txn.description,
                "transaction_date": txn.transaction_date.isoformat(),
                "payment_method": txn.payment_method,
                "tags": list(txn.tags) if txn.tags else []
            }

            # Apply updates
            update_data = data.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(txn, field, value)

            # 3. Check semantic constraints post-update
            if txn.transaction_type == "expense" and txn.category_id is None:
                raise ValidationError(
                    message="Expenses must be categorized.",
                    error_code="VALIDATION_ERROR"
                )
            if txn.transaction_type == "transfer" and txn.category_id is not None:
                raise ValidationError(
                    message="Transfers cannot have a category.",
                    error_code="VALIDATION_ERROR"
                )

            await self.uow.transactions.update(txn)
            await self.uow.commit()
            await self.uow.refresh(txn)
            
            try:
                from app.events.base import event_bus
                from app.events.definitions import TransactionUpdated
                new_data = {
                    "amount": float(txn.amount),
                    "currency": txn.currency,
                    "category_id": str(txn.category_id) if txn.category_id else None,
                    "description": txn.description,
                    "transaction_date": txn.transaction_date.isoformat(),
                    "payment_method": txn.payment_method,
                    "tags": list(txn.tags) if txn.tags else []
                }
                await event_bus.publish(
                    TransactionUpdated(
                        transaction_id=txn.id,
                        user_id=user_id,
                        old_data=old_data,
                        new_data=new_data
                    )
                )
            except Exception as e:
                logger.error("Failed to publish TransactionUpdated event", error=str(e), exc_info=True)

            logger.info("Transaction updated successfully", user_id=str(user_id), transaction_id=str(txn.id))
            return txn

    async def delete_transaction(self, transaction_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """Soft delete a transaction."""
        async with self.uow:
            txn = await self.uow.transactions.get(transaction_id)
            if not txn or txn.user_id != user_id or txn.deleted_at is not None:
                raise NotFoundError(
                    message="Transaction not found.",
                    error_code="TRANSACTION_NOT_FOUND"
                )

            # Perform soft delete
            txn.deleted_at = datetime.now(timezone.utc)
            await self.uow.transactions.update(txn)
            await self.uow.commit()
            
            try:
                from app.events.base import event_bus
                from app.events.definitions import TransactionDeleted
                await event_bus.publish(
                    TransactionDeleted(
                        transaction_id=txn.id,
                        user_id=user_id
                    )
                )
            except Exception as e:
                logger.error("Failed to publish TransactionDeleted event", error=str(e), exc_info=True)

            logger.info("Transaction soft-deleted successfully", user_id=str(user_id), transaction_id=str(txn.id))

    async def list_transactions(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        per_page: int = 20,
        transaction_type: str | None = None,
        category_id: uuid.UUID | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        min_amount: float | None = None,
        max_amount: float | None = None,
        sort_by: str = "transaction_date",
        sort_order: str = "desc"
    ) -> Tuple[List[Transaction], int]:
        """Fetch list of transactions satisfying filters and matching user context."""
        # Build composite specification
        spec = (
            TransactionByUser(user_id)
            & TransactionByType(transaction_type)
            & TransactionByCategory(category_id)
            & TransactionInDateRange(date_from, date_to)
            & TransactionByAmountRange(min_amount, max_amount)
            & NotDeleted()
        )

        async with self.uow:
            items = await self.uow.transactions.get_filtered(
                spec=spec,
                page=page,
                per_page=per_page,
                sort_by=sort_by,
                sort_order=sort_order
            )
            total = await self.uow.transactions.count_filtered(spec)
            return items, total
