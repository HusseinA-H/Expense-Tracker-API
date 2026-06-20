import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from app.api.deps import get_redis, get_unit_of_work
from app.config import settings
from app.db.unit_of_work import SQLAlchemyUnitOfWork

logger = structlog.get_logger("app.health")
router = APIRouter(tags=["Health"])


@router.get("/live")
async def liveness_probe():
    """Kubernetes liveness probe — process is running."""
    return {"status": "ok", "version": settings.APP_VERSION}


@router.get("/ready")
async def readiness_probe(
    uow: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    redis=Depends(get_redis),
):
    """Readiness probe — verify database and Redis connectivity."""
    checks: dict[str, str] = {}

    try:
        async with uow:
            await uow._session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        logger.warning("Database readiness check failed", error=str(exc))
        checks["database"] = "error"

    try:
        await redis.ping()
        checks["redis"] = "ok"
    except Exception as exc:
        logger.warning("Redis readiness check failed", error=str(exc))
        checks["redis"] = "error"

    all_ok = all(status == "ok" for status in checks.values())
    payload = {
        "status": "ok" if all_ok else "degraded",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "checks": checks,
    }

    if not all_ok:
        raise HTTPException(status_code=503, detail=payload)

    return payload
