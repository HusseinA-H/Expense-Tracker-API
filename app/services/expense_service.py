import uuid
from datetime import date
from typing import List, Tuple
from app.core.exceptions import NotFoundError
from app.services.transaction_service import TransactionService
from app.models.transaction import Transaction
from app.schemas.expense import ExpenseCreate, ExpenseUpdate
from app.schemas.transaction import TransactionCreate, TransactionUpdate

class ExpenseService:
    """v1 backward-compatible facade over TransactionService."""

    def __init__(self, transaction_service: TransactionService):
        self._txn = transaction_service

    async def create_expense(self, user_id: uuid.UUID, data: ExpenseCreate) -> Transaction:
        """Create a new expense (type=expense)."""
        return await self._txn.create_transaction(
            user_id=user_id,
            data=TransactionCreate(
                transaction_type="expense",
                amount=data.amount,
                currency=data.currency,
                category_id=data.category_id,
                description=data.description,
                transaction_date=data.expense_date,
                payment_method=data.payment_method,
                tags=data.tags,
                receipt_url=data.receipt_url,
                is_recurring=data.is_recurring,
                metadata={},
            ),
        )

    async def get_expense(self, expense_id: uuid.UUID, user_id: uuid.UUID) -> Transaction:
        """Retrieve a specific expense transaction."""
        txn = await self._txn.get_transaction(expense_id, user_id)
        if txn.transaction_type != "expense":
            raise NotFoundError(
                message="Expense not found.",
                error_code="EXPENSE_NOT_FOUND"
            )
        return txn

    async def update_expense(
        self, expense_id: uuid.UUID, user_id: uuid.UUID, data: ExpenseUpdate
    ) -> Transaction:
        """Update an existing expense transaction."""
        # Ensure it is a valid expense first
        await self.get_expense(expense_id, user_id)
        
        txn_update = TransactionUpdate(
            amount=data.amount,
            currency=data.currency,
            category_id=data.category_id,
            description=data.description,
            transaction_date=data.expense_date,
            payment_method=data.payment_method,
            tags=data.tags,
            receipt_url=data.receipt_url,
            is_recurring=data.is_recurring,
        )
        return await self._txn.update_transaction(expense_id, user_id, txn_update)

    async def delete_expense(self, expense_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """Soft delete an expense transaction."""
        await self.get_expense(expense_id, user_id)
        await self._txn.delete_transaction(expense_id, user_id)

    async def list_expenses(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        per_page: int = 20,
        category_id: uuid.UUID | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> Tuple[List[Transaction], int]:
        """Fetch list of user's expense transactions satisfying filters."""
        return await self._txn.list_transactions(
            user_id=user_id,
            page=page,
            per_page=per_page,
            transaction_type="expense",
            category_id=category_id,
            date_from=date_from,
            date_to=date_to,
        )
