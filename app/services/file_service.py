import os
import uuid

import structlog
from fastapi import UploadFile

from app.core.exceptions import ValidationError

logger = structlog.get_logger("app.services.file")

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "application/pdf"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


class FileService:
    """Service handling uploaded receipt files validation and local storage."""

    def __init__(self, upload_dir: str = "uploads"):
        self.upload_dir = upload_dir
        os.makedirs(self.upload_dir, exist_ok=True)

    async def save_receipt(self, file: UploadFile) -> str:
        """Validate and save an uploaded receipt file. Returns the relative file URL."""
        # 1. Validate file type
        ext = os.path.splitext(file.filename)[1].lower() if file.filename else ""
        if ext not in ALLOWED_EXTENSIONS or file.content_type not in ALLOWED_MIME_TYPES:
            raise ValidationError(
                message="Unsupported file type. Only JPG, PNG, and PDF are allowed.",
                error_code="UNSUPPORTED_FILE_TYPE",
            )

        # 2. Validate file size
        await file.seek(0)
        content = await file.read()
        size = len(content)

        if size > MAX_FILE_SIZE:
            raise ValidationError(
                message="File size exceeds the maximum limit of 5 MB.",
                error_code="FILE_TOO_LARGE",
            )

        # 3. Generate unique filename and save file
        unique_filename = f"{uuid.uuid4().hex}{ext}"
        filepath = os.path.join(self.upload_dir, unique_filename)

        with open(filepath, "wb") as f:
            f.write(content)

        logger.info("Receipt file saved", filename=unique_filename, filepath=filepath)

        # Return URL path
        return f"/uploads/{unique_filename}"

    def resolve_receipt_path(self, receipt_url: str) -> str:
        """Resolve a receipt URL path to an absolute filesystem path."""
        if not receipt_url.startswith("/uploads/"):
            raise ValidationError(
                message="Invalid receipt URL path.",
                error_code="INVALID_RECEIPT_PATH",
            )
        filename = os.path.basename(receipt_url)
        return os.path.join(self.upload_dir, filename)
