import asyncio
from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy import text

from app.celery_app import celery_app
from app.db.unit_of_work import SQLAlchemyUnitOfWork
from app.tasks import run_async

logger = structlog.get_logger("app.tasks.maintenance")


def _run_async(coro):
    return run_async(coro)


@celery_app.task(name="app.tasks.maintenance_tasks.cleanup_expired_tokens")
def cleanup_expired_tokens() -> dict[str, Any]:
    """Remove expired and long-revoked refresh tokens from the database."""
    return _run_async(_cleanup_expired_tokens_async())


async def _cleanup_expired_tokens_async() -> dict[str, Any]:
    uow = SQLAlchemyUnitOfWork()
    async with uow:
        deleted_count = await uow.refresh_tokens.delete_expired_and_revoked()
        await uow.commit()

    logger.info("Expired refresh tokens cleaned up", deleted_count=deleted_count)
    return {"status": "completed", "deleted_count": deleted_count}


@celery_app.task(name="app.tasks.maintenance_tasks.archive_old_partitions")
def archive_old_partitions() -> dict[str, Any]:
    """Stub maintenance task for audit log partition archival.

    Checks partition metadata and logs partitions eligible for archival.
    Full partition creation is managed by the database schedule; this task
    performs metadata checks and reports status without destructive operations
    in development environments.
    """
    return _run_async(_archive_old_partitions_async())


async def _archive_old_partitions_async() -> dict[str, Any]:
    uow = SQLAlchemyUnitOfWork()
    partitions: list[dict[str, Any]] = []

    async with uow:
        result = await uow._session.execute(
            text("""
                SELECT
                    c.relname AS partition_name,
                    pg_get_expr(c.relpartbound, c.oid) AS partition_bound
                FROM pg_class c
                JOIN pg_inherits i ON c.oid = i.inhrelid
                JOIN pg_class p ON i.inhparent = p.oid
                WHERE p.relname = 'audit_logs'
                ORDER BY c.relname
            """)
        )
        rows = result.fetchall()
        for row in rows:
            partitions.append({
                "partition_name": row[0],
                "partition_bound": row[1],
            })

    default_partition = next(
        (p for p in partitions if p["partition_name"] == "audit_logs_default"),
        None,
    )
    child_partitions = [
        p for p in partitions if p["partition_name"] != "audit_logs_default"
    ]

    logger.info(
        "Audit log partition metadata checked",
        total_partitions=len(partitions),
        child_partitions=len(child_partitions),
        has_default=default_partition is not None,
    )

    return {
        "status": "completed",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "total_partitions": len(partitions),
        "child_partitions": len(child_partitions),
        "partitions": partitions,
        "action": "metadata_check_only",
        "message": (
            "Partition archival is stubbed; partition creation runs on database schedule. "
            "No partitions were dropped."
        ),
    }
