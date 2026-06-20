import uuid
from datetime import date

import structlog
from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status

from app.api.deps import get_current_active_user, get_expense_service, get_file_service
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.expense import ExpenseCreate, ExpenseResponse, ExpenseUpdate
from app.services.expense_service import ExpenseService
from app.services.file_service import FileService
from app.services.receipt_dispatch import dispatch_receipt_processing

router = APIRouter()
logger = structlog.get_logger("app.api.expenses")


@router.post("", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
async def create_expense(
    data: ExpenseCreate,
    current_user: User = Depends(get_current_active_user),
    expense_service: ExpenseService = Depends(get_expense_service),
):
    """Create a new expense (type=expense, backward-compatible)."""
    expense = await expense_service.create_expense(current_user.id, data)
    return expense


@router.get("", response_model=PaginatedResponse[ExpenseResponse])
async def list_expenses(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    category_id: uuid.UUID | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    current_user: User = Depends(get_current_active_user),
    expense_service: ExpenseService = Depends(get_expense_service),
):
    """List expenses satisfying filters and matching user context (paginated, backward-compatible)."""
    items, total = await expense_service.list_expenses(
        user_id=current_user.id,
        page=page,
        per_page=per_page,
        category_id=category_id,
        date_from=date_from,
        date_to=date_to,
    )
    pages = (total + per_page - 1) // per_page
    return PaginatedResponse(
        items=items, total=total, page=page, size=per_page, pages=pages
    )


@router.get("/{id}", response_model=ExpenseResponse)
async def get_expense(
    id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    expense_service: ExpenseService = Depends(get_expense_service),
):
    """Retrieve details of a specific expense (backward-compatible)."""
    expense = await expense_service.get_expense(id, current_user.id)
    return expense


@router.patch("/{id}", response_model=ExpenseResponse)
async def update_expense(
    id: uuid.UUID,
    data: ExpenseUpdate,
    current_user: User = Depends(get_current_active_user),
    expense_service: ExpenseService = Depends(get_expense_service),
):
    """Perform a partial update on an expense record (backward-compatible)."""
    expense = await expense_service.update_expense(id, current_user.id, data)
    return expense


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expense(
    id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    expense_service: ExpenseService = Depends(get_expense_service),
):
    """Soft-delete a specific expense (backward-compatible)."""
    await expense_service.delete_expense(id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{id}/receipt", response_model=ExpenseResponse)
async def upload_receipt(
    id: uuid.UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    expense_service: ExpenseService = Depends(get_expense_service),
    file_service: FileService = Depends(get_file_service),
):
    """Upload a receipt image and link it to the expense."""
    # 1. Save and validate file
    url = await file_service.save_receipt(file)

    # 2. Update expense with receipt URL
    update_data = ExpenseUpdate(receipt_url=url)
    expense = await expense_service.update_expense(id, current_user.id, update_data)

    dispatch_receipt_processing(id, url, file_service)
    return expense
