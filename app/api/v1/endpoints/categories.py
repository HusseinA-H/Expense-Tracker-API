import uuid
import structlog
from fastapi import APIRouter, Depends, status, Response
from app.api.deps import get_category_service, get_current_active_user
from app.services.category_service import CategoryService
from app.schemas.category import CategoryResponse, CategoryCreate, CategoryUpdate
from app.models.user import User

router = APIRouter()
logger = structlog.get_logger("app.api.categories")

@router.get("", response_model=list[CategoryResponse])
async def list_categories(
    current_user: User = Depends(get_current_active_user),
    category_service: CategoryService = Depends(get_category_service)
):
    """Retrieve all categories (system and custom categories scoped to the user)."""
    categories = await category_service.list_categories(current_user.id)
    return categories

@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    data: CategoryCreate,
    current_user: User = Depends(get_current_active_user),
    category_service: CategoryService = Depends(get_category_service)
):
    """Create a new custom category."""
    category = await category_service.create_category(current_user.id, data)
    return category

@router.patch("/{id}", response_model=CategoryResponse)
async def update_category(
    id: uuid.UUID,
    data: CategoryUpdate,
    current_user: User = Depends(get_current_active_user),
    category_service: CategoryService = Depends(get_category_service)
):
    """Update a custom category (system categories cannot be modified)."""
    category = await category_service.update_category(id, current_user.id, data)
    return category

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    category_service: CategoryService = Depends(get_category_service)
):
    """Delete a custom category (system categories cannot be deleted)."""
    await category_service.delete_category(id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
