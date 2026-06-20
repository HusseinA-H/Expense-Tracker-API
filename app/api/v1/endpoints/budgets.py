import uuid
import structlog
from fastapi import APIRouter, Depends, status, Response, Query
from app.api.deps import get_budget_service, get_current_active_user
from app.services.budget_service import BudgetService
from app.schemas.budget import BudgetResponse, BudgetCreate, BudgetUpdate, BudgetSummaryResponse
from app.models.user import User

router = APIRouter()
logger = structlog.get_logger("app.api.budgets")

@router.post("", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
async def create_budget(
    data: BudgetCreate,
    current_user: User = Depends(get_current_active_user),
    budget_service: BudgetService = Depends(get_budget_service)
):
    """Create a new category budget."""
    budget = await budget_service.create_budget(current_user.id, data)
    return budget

@router.get("", response_model=list[BudgetResponse])
async def list_budgets(
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2020),
    current_user: User = Depends(get_current_active_user),
    budget_service: BudgetService = Depends(get_budget_service)
):
    """Retrieve all budgets configured for a user in a specific monthly period."""
    budgets = await budget_service.list_budgets(current_user.id, month, year)
    return budgets

@router.get("/summary", response_model=list[BudgetSummaryResponse])
async def get_budget_summary(
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2020),
    current_user: User = Depends(get_current_active_user),
    budget_service: BudgetService = Depends(get_budget_service)
):
    """Retrieve a budget spent summary breakdown for a specific monthly period."""
    summary = await budget_service.get_budget_summary(current_user.id, month, year)
    return summary

@router.patch("/{id}", response_model=BudgetResponse)
async def update_budget(
    id: uuid.UUID,
    data: BudgetUpdate,
    current_user: User = Depends(get_current_active_user),
    budget_service: BudgetService = Depends(get_budget_service)
):
    """Update configured parameters of an existing budget."""
    budget = await budget_service.update_budget(id, current_user.id, data)
    return budget

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_budget(
    id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    budget_service: BudgetService = Depends(get_budget_service)
):
    """Delete a specific category budget configuration."""
    await budget_service.delete_budget(id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
