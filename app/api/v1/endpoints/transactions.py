import uuid
from datetime import date
import structlog
from fastapi import APIRouter, Depends, status, Response, Query, File, UploadFile
from app.api.deps import get_transaction_service, get_current_active_user, get_file_service
from app.services.transaction_service import TransactionService
from app.services.file_service import FileService
from app.services.receipt_dispatch import dispatch_receipt_processing
from app.schemas.transaction import TransactionResponse, TransactionCreate, TransactionUpdate
from app.schemas.common import PaginatedResponse
from app.models.user import User

router = APIRouter()
logger = structlog.get_logger("app.api.transactions")

@router.post("", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    data: TransactionCreate,
    current_user: User = Depends(get_current_active_user),
    transaction_service: TransactionService = Depends(get_transaction_service)
):
    """Create a new transaction (expense, income, or transfer)."""
    txn = await transaction_service.create_transaction(current_user.id, data)
    return txn

@router.get("", response_model=PaginatedResponse[TransactionResponse])
async def list_transactions(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    transaction_type: str | None = Query(default=None),
    category_id: uuid.UUID | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    min_amount: float | None = Query(default=None, ge=0),
    max_amount: float | None = Query(default=None, ge=0),
    sort_by: str = Query(default="transaction_date"),
    sort_order: str = Query(default="desc"),
    current_user: User = Depends(get_current_active_user),
    transaction_service: TransactionService = Depends(get_transaction_service)
):
    """List transactions satisfying filters and matching user context (paginated)."""
    items, total = await transaction_service.list_transactions(
        user_id=current_user.id,
        page=page,
        per_page=per_page,
        transaction_type=transaction_type,
        category_id=category_id,
        date_from=date_from,
        date_to=date_to,
        min_amount=min_amount,
        max_amount=max_amount,
        sort_by=sort_by,
        sort_order=sort_order
    )
    pages = (total + per_page - 1) // per_page
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        size=per_page,
        pages=pages
    )

@router.get("/{id}", response_model=TransactionResponse)
async def get_transaction(
    id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    transaction_service: TransactionService = Depends(get_transaction_service)
):
    """Retrieve details of a specific transaction."""
    txn = await transaction_service.get_transaction(id, current_user.id)
    return txn

@router.patch("/{id}", response_model=TransactionResponse)
async def update_transaction(
    id: uuid.UUID,
    data: TransactionUpdate,
    current_user: User = Depends(get_current_active_user),
    transaction_service: TransactionService = Depends(get_transaction_service)
):
    """Perform a partial update on a transaction record."""
    txn = await transaction_service.update_transaction(id, current_user.id, data)
    return txn

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    transaction_service: TransactionService = Depends(get_transaction_service)
):
    """Soft-delete a specific transaction."""
    await transaction_service.delete_transaction(id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.post("/{id}/receipt", response_model=TransactionResponse)
async def upload_receipt(
    id: uuid.UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    transaction_service: TransactionService = Depends(get_transaction_service),
    file_service: FileService = Depends(get_file_service)
):
    """Upload a receipt image and link it to the transaction."""
    # 1. Save and validate file
    url = await file_service.save_receipt(file)
    
    # 2. Update transaction with receipt URL
    update_data = TransactionUpdate(receipt_url=url)
    txn = await transaction_service.update_transaction(id, current_user.id, update_data)

    dispatch_receipt_processing(id, url, file_service)
    return txn
