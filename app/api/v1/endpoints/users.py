import structlog
from fastapi import APIRouter, Depends, Query, Response, status

from app.api.deps import get_current_active_user, get_user_service, require_admin
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.user import PasswordChangeRequest, UserResponse, UserUpdate
from app.services.user_service import UserService

router = APIRouter()
logger = structlog.get_logger("app.api.users")


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_active_user)):
    """Retrieve the profile details of the authenticated user."""
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_me(
    data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service),
):
    """Update profile details of the authenticated user."""
    updated_user = await user_service.update_profile(current_user.id, data)
    return updated_user


@router.put("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    data: PasswordChangeRequest,
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service),
):
    """Change the password of the authenticated user."""
    await user_service.change_password(
        current_user.id, data.current_password, data.new_password
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_me(
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service),
):
    """Deactivate (soft-delete) the authenticated user's account."""
    await user_service.deactivate_account(current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("", response_model=PaginatedResponse[UserResponse])
async def list_users(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    current_admin: User = Depends(require_admin),
    user_service: UserService = Depends(get_user_service),
):
    """List all registered users (Admin only, paginated)."""
    items, total = await user_service.list_users(page=page, per_page=per_page)
    pages = (total + per_page - 1) // per_page
    return PaginatedResponse(
        items=items, total=total, page=page, size=per_page, pages=pages
    )
