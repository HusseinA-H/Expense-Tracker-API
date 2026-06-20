from collections.abc import AsyncGenerator
import redis.asyncio as aioredis
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import get_db, get_read_db
from app.db.redis import get_redis
from app.db.unit_of_work import SQLAlchemyUnitOfWork
from app.services.auth_service import AuthService
from app.services.user_service import UserService
from app.services.transaction_service import TransactionService
from app.services.expense_service import ExpenseService
from app.services.category_service import CategoryService
from app.services.budget_service import BudgetService
from app.services.file_service import FileService
from app.services.audit_service import AuditService
from app.core.security import verify_access_token, TokenPayload

from app.core.exceptions import AuthenticationError
from app.models.user import User

# OAuth2 token endpoint used by Swagger UI (form-urlencoded username/password).
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/token",
    scheme_name="OAuth2PasswordBearer",
)

async def get_unit_of_work() -> AsyncGenerator[SQLAlchemyUnitOfWork, None]:
    """Dependency injection providing the Unit of Work."""
    yield SQLAlchemyUnitOfWork()

async def get_auth_service(
    uow: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
) -> AuthService:
    """Dependency injection providing the AuthService."""
    return AuthService(uow)

async def get_user_service(
    uow: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
) -> UserService:
    """Dependency injection providing the UserService."""
    return UserService(uow)

async def get_transaction_service(
    uow: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
) -> TransactionService:
    """Dependency injection providing the TransactionService."""
    return TransactionService(uow)

async def get_expense_service(
    txn_service: TransactionService = Depends(get_transaction_service),
) -> ExpenseService:
    """Dependency injection providing the ExpenseService."""
    return ExpenseService(txn_service)

async def get_category_service(
    uow: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
) -> CategoryService:
    """Dependency injection providing the CategoryService."""
    return CategoryService(uow)

async def get_budget_service(
    uow: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
) -> BudgetService:
    """Dependency injection providing the BudgetService."""
    return BudgetService(uow)

async def get_audit_service(
    uow: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
) -> AuditService:
    """Dependency injection providing the AuditService."""
    return AuditService(uow)

async def get_file_service() -> FileService:
    """Dependency injection providing the FileService."""
    return FileService()







async def get_current_user(
    token: str = Depends(oauth2_scheme),
    uow: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    redis: aioredis.Redis = Depends(get_redis),
) -> User:
    """Extract and validate the current user from JWT access token."""
    # 1. Decode and verify signature
    payload = verify_access_token(token)
    
    # 2. Check if token is blacklisted in Redis (optional blacklist lookup)
    # If the JTI is found in the Redis blacklist, deny access immediately.
    is_blacklisted = await redis.get(f"blacklist:{payload.jti}")
    if is_blacklisted:
        raise AuthenticationError(
            message="Token has been blacklisted / revoked.",
            error_code="TOKEN_BLACKLISTED"
        )
        
    # 3. Retrieve user from database
    async with uow:
        user = await uow.users.get(payload.sub)
        if not user:
            raise AuthenticationError(
                message="User associated with this token was not found.",
                error_code="USER_NOT_FOUND"
            )
        
        # Keep user object loaded
        return user

async def get_current_active_user(
    user: User = Depends(get_current_user),
) -> User:
    """Ensure that the authenticated user account is active."""
    if not user.is_active:
        raise AuthenticationError(
            message="User account is deactivated.",
            error_code="USER_INACTIVE"
        )
    return user

async def require_admin(
    user: User = Depends(get_current_active_user),
) -> User:
    """Ensure that the user has administrative privileges."""
    if user.role != "admin":
        from app.core.exceptions import AuthorizationError
        raise AuthorizationError(
            message="Administrative privileges required.",
            error_code="FORBIDDEN",
        )
    return user
