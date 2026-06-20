import uuid
import structlog
from app.core.exceptions import NotFoundError, ConflictError, AuthorizationError
from app.db.unit_of_work import SQLAlchemyUnitOfWork
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryUpdate

logger = structlog.get_logger("app.services.category")

class CategoryService:
    """Service handling category CRUD business logic."""

    def __init__(self, uow: SQLAlchemyUnitOfWork):
        self.uow = uow

    async def create_category(self, user_id: uuid.UUID, data: CategoryCreate) -> Category:
        """Create a custom category scoped to the user."""
        async with self.uow:
            # Check if category name already exists for this user or as a system category
            existing = await self.uow.categories.get_by_name(data.name, user_id)
            if existing:
                raise ConflictError(
                    message=f"Category with name '{data.name}' already exists.",
                    error_code="CATEGORY_ALREADY_EXISTS"
                )

            category = Category(
                name=data.name,
                icon=data.icon,
                color=data.color,
                is_system=False,
                user_id=user_id,
            )
            await self.uow.categories.add(category)
            await self.uow.commit()

            logger.info("Category created successfully", user_id=str(user_id), category_id=str(category.id))
            return category

    async def update_category(
        self, category_id: uuid.UUID, user_id: uuid.UUID, data: CategoryUpdate
    ) -> Category:
        """Update a custom category (system categories cannot be modified)."""
        async with self.uow:
            category = await self.uow.categories.get(category_id)
            if not category or (category.user_id != user_id and not category.is_system):
                raise NotFoundError(
                    message="Category not found.",
                    error_code="CATEGORY_NOT_FOUND"
                )

            if category.is_system:
                raise AuthorizationError(
                    message="System categories cannot be modified.",
                    error_code="FORBIDDEN",
                    status_code=403
                )

            # Check name collision if name is updated
            if data.name is not None and data.name != category.name:
                existing = await self.uow.categories.get_by_name(data.name, user_id)
                if existing:
                    raise ConflictError(
                        message=f"Category with name '{data.name}' already exists.",
                        error_code="CATEGORY_ALREADY_EXISTS"
                    )

            update_data = data.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(category, field, value)

            await self.uow.categories.update(category)
            await self.uow.commit()
            await self.uow.refresh(category)

            logger.info("Category updated successfully", user_id=str(user_id), category_id=str(category.id))
            return category

    async def delete_category(self, category_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """Delete a custom category (system categories cannot be deleted)."""
        async with self.uow:
            category = await self.uow.categories.get(category_id)
            if not category or (category.user_id != user_id and not category.is_system):
                raise NotFoundError(
                    message="Category not found.",
                    error_code="CATEGORY_NOT_FOUND"
                )

            if category.is_system:
                raise AuthorizationError(
                    message="System categories cannot be deleted.",
                    error_code="FORBIDDEN",
                    status_code=403
                )

            await self.uow.categories.delete(category)
            await self.uow.commit()

            logger.info("Category deleted successfully", user_id=str(user_id), category_id=str(category_id))

    async def list_categories(self, user_id: uuid.UUID) -> list[Category]:
        """List all accessible categories (system categories + custom user categories)."""
        async with self.uow:
            return await self.uow.categories.get_all_accessible(user_id)
