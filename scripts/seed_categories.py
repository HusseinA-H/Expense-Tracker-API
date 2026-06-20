import asyncio
import structlog
from sqlalchemy import select
from app.db.session import async_session_maker
from app.models.category import Category

logger = structlog.get_logger("scripts.seed_categories")

DEFAULT_CATEGORIES = [
    {"name": "Food", "icon": "utensils", "color": "#FF5733"},
    {"name": "Transport", "icon": "car", "color": "#3357FF"},
    {"name": "Housing", "icon": "home", "color": "#33FF57"},
    {"name": "Utilities", "icon": "bolt", "color": "#F3FF33"},
    {"name": "Entertainment", "icon": "film", "color": "#FF33F3"},
    {"name": "Healthcare", "icon": "heartbeat", "color": "#FF3333"},
    {"name": "Education", "icon": "graduation-cap", "color": "#33FFF0"},
    {"name": "Shopping", "icon": "shopping-cart", "color": "#F033FF"},
    {"name": "Other", "icon": "ellipsis-h", "color": "#888888"},
]

async def seed_categories():
    """Seed the database with system default categories."""
    logger.info("Starting category seeding...")
    async with async_session_maker() as session:
        for cat_data in DEFAULT_CATEGORIES:
            # Check if category exists
            stmt = select(Category).where(
                Category.name == cat_data["name"],
                Category.is_system == True
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if not existing:
                category = Category(
                    name=cat_data["name"],
                    icon=cat_data["icon"],
                    color=cat_data["color"],
                    is_system=True,
                    user_id=None
                )
                session.add(category)
                logger.info("Category created", name=cat_data["name"])
            else:
                logger.info("Category already exists", name=cat_data["name"])
                
        await session.commit()
    logger.info("Category seeding completed.")

if __name__ == "__main__":
    from app.utils.logging import setup_logging
    setup_logging(log_level="INFO")
    asyncio.run(seed_categories())
