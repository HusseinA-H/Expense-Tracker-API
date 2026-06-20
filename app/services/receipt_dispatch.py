import uuid

import structlog

from app.services.file_service import FileService

logger = structlog.get_logger("app.services.receipt_dispatch")


def dispatch_receipt_processing(
    transaction_id: uuid.UUID, receipt_url: str, file_service: FileService
) -> None:
    """Enqueue background receipt processing after a successful upload."""
    try:
        filepath = file_service.resolve_receipt_path(receipt_url)
        from app.tasks.receipt_tasks import process_receipt_image

        process_receipt_image.delay(str(transaction_id), filepath)
        logger.info(
            "Receipt processing task dispatched",
            transaction_id=str(transaction_id),
            filepath=filepath,
        )
    except Exception as exc:
        logger.warning(
            "Failed to dispatch receipt processing task",
            transaction_id=str(transaction_id),
            receipt_url=receipt_url,
            error=str(exc),
            exc_info=True,
        )
