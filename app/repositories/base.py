import uuid
from typing import Generic, Type, TypeVar
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)

class BaseRepository(Generic[ModelType]):
    """Generic async repository implementing standard CRUD operations."""

    def __init__(self, model: Type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def get(self, id: uuid.UUID) -> ModelType | None:
        """Fetch a single record by its primary key ID."""
        return await self.session.get(self.model, id)

    async def get_multi(
        self,
        page: int = 1,
        per_page: int = 20,
    ) -> list[ModelType]:
        """Fetch multiple records with pagination."""
        offset = (page - 1) * per_page
        stmt = select(self.model).offset(offset).limit(per_page)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count(self) -> int:
        """Count total records for this entity."""
        stmt = select(func.count()).select_from(self.model)
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def add(self, entity: ModelType) -> ModelType:
        """Add a new entity to the session (does not commit)."""
        self.session.add(entity)
        return entity

    async def update(self, entity: ModelType) -> ModelType:
        """Update an existing entity in the session."""
        # Work is managed by SQLAlchemy session; method provided for repository pattern purity
        return entity

    async def delete(self, entity: ModelType) -> None:
        """Delete an entity from the session."""
        await self.session.delete(entity)
