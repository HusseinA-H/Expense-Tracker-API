import asyncio
import os
import uuid
from typing import Any

import structlog

from app.celery_app import celery_app
from app.db.unit_of_work import SQLAlchemyUnitOfWork
from app.tasks import run_async

logger = structlog.get_logger("app.tasks.receipts")

try:
    from PIL import Image

    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False


def _run_async(coro):
    return run_async(coro)


@celery_app.task(name="app.tasks.receipt_tasks.process_receipt_image")
def process_receipt_image(transaction_id: str, file_path: str) -> dict[str, Any]:
    """Validate receipt image, extract metadata, and generate a thumbnail if Pillow is available."""
    return _run_async(_process_receipt_image_async(transaction_id, file_path))


async def _process_receipt_image_async(transaction_id: str, file_path: str) -> dict[str, Any]:
    if not os.path.isfile(file_path):
        logger.warning("Receipt file not found", file_path=file_path, transaction_id=transaction_id)
        return {"status": "failed", "reason": "file_not_found", "file_path": file_path}

    metadata: dict[str, Any] = {
        "file_size_bytes": os.path.getsize(file_path),
        "file_name": os.path.basename(file_path),
    }
    thumbnail_path = None
    is_valid = False

    if PILLOW_AVAILABLE:
        try:
            with Image.open(file_path) as img:
                img.verify()
            with Image.open(file_path) as img:
                is_valid = True
                metadata["format"] = img.format
                metadata["mode"] = img.mode
                metadata["width"] = img.width
                metadata["height"] = img.height

                thumb_dir = os.path.join(os.path.dirname(file_path), "thumbnails")
                os.makedirs(thumb_dir, exist_ok=True)
                thumb_filename = f"thumb_{os.path.basename(file_path)}"
                thumbnail_path = os.path.join(thumb_dir, thumb_filename)

                img.thumbnail((200, 200))
                img.save(thumbnail_path)
                metadata["thumbnail_path"] = thumbnail_path
        except Exception as exc:
            logger.warning(
                "Receipt image validation failed",
                file_path=file_path,
                error=str(exc),
            )
            metadata["validation_error"] = str(exc)
    else:
        ext = os.path.splitext(file_path)[1].lower()
        is_valid = ext in {".jpg", ".jpeg", ".png"}
        metadata["pillow_available"] = False
        metadata["validated_by_extension"] = is_valid

    uow = SQLAlchemyUnitOfWork()
    async with uow:
        tx = await uow.transactions.get(uuid.UUID(transaction_id))
        if tx:
            tx_metadata = dict(tx.tx_metadata or {})
            tx_metadata["receipt_processing"] = {
                "is_valid": is_valid,
                "metadata": metadata,
                "thumbnail_path": thumbnail_path,
            }
            tx.tx_metadata = tx_metadata
            await uow.transactions.update(tx)
            await uow.commit()

    logger.info(
        "Receipt processed",
        transaction_id=transaction_id,
        is_valid=is_valid,
        thumbnail_path=thumbnail_path,
    )

    return {
        "status": "completed" if is_valid else "invalid",
        "transaction_id": transaction_id,
        "file_path": file_path,
        "is_valid": is_valid,
        "metadata": metadata,
        "thumbnail_path": thumbnail_path,
    }
