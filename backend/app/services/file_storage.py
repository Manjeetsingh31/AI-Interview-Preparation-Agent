"""File storage service for resume uploads.

Provides secure file handling including validation, sanitization,
and storage of uploaded PDF resume files on disk.

Design decisions:
    - Magic-bytes check (%PDF header) prevents file-extension spoofing.
    - UUID-based stored names eliminate path-traversal and collision risks.
    - UPLOAD_DIR is created on init so callers never deal with missing dirs.
    - MAX_FILE_SIZE is configurable per-instance, enabling easy override in tests.
"""

import logging
import uuid
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class FileStorageError(Exception):
    """Base exception for all file-storage operations."""


class InvalidFileTypeError(FileStorageError):
    """Raised when the uploaded file is not a valid PDF."""


class FileSizeExceededError(FileStorageError):
    """Raised when the uploaded file exceeds the maximum allowed size."""


class FileStorageService:
    """Handles secure file storage for uploaded resume PDFs.

    Validates file type via both extension and magic bytes, enforces
    configurable size limits, and stores files under UUID-based names
    to prevent collisions and path-traversal attacks.

    Attributes:
        UPLOAD_DIR:      Absolute path to the directory holding uploaded files.
        MAX_FILE_SIZE:   Maximum allowed file size in bytes (default 10 MB).
        ALLOWED_EXTENSIONS: Set of permitted file extensions.
        PDF_MAGIC_BYTES: Byte sequence that every valid PDF must start with.
    """

    ALLOWED_EXTENSIONS: frozenset = frozenset({".pdf"})
    PDF_MAGIC_BYTES: bytes = b"%PDF"

    def __init__(
        self,
        upload_dir: str | Path = "uploads/resumes",
        max_file_size: int = 10 * 1024 * 1024,
    ) -> None:
        """Initialise the storage service.

        Args:
            upload_dir:    Directory path for storing uploaded files. Created
                           automatically if it does not exist.
            max_file_size: Maximum allowed file size in bytes.
                           Defaults to 10 MB.
        """
        self.UPLOAD_DIR = Path(upload_dir).resolve()
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        self.MAX_FILE_SIZE = max_file_size
        logger.info(
            "FileStorageService initialised: dir=%s, max_size=%d bytes",
            self.UPLOAD_DIR,
            self.MAX_FILE_SIZE,
        )

    def validate_file(self, filename: str, content: bytes) -> None:
        """Validate uploaded file type and size.

        Checks:
            1. File extension is ``.pdf``.
            2. Content starts with the PDF magic header (``%PDF``).
            3. Content length does not exceed ``MAX_FILE_SIZE``.

        Args:
            filename: Original uploaded filename.
            content:  Raw file bytes.

        Raises:
            InvalidFileTypeError: If the extension is not ``.pdf`` or the
                content does not start with the PDF magic header.
            FileSizeExceededError: If the content exceeds ``MAX_FILE_SIZE``.
        """
        ext = Path(filename).suffix.lower()
        if ext not in self.ALLOWED_EXTENSIONS:
            raise InvalidFileTypeError(
                f"Invalid file type '{ext}'. Only PDF files are allowed.",
            )

        if not content.startswith(self.PDF_MAGIC_BYTES):
            raise InvalidFileTypeError(
                "File is not a valid PDF (missing PDF header).",
            )

        if len(content) > self.MAX_FILE_SIZE:
            raise FileSizeExceededError(
                f"File size {len(content)} bytes exceeds the maximum allowed "
                f"{self.MAX_FILE_SIZE} bytes "
                f"({self.MAX_FILE_SIZE // (1024 * 1024)} MB).",
            )

        logger.debug("File validation passed: %s (%d bytes)", filename, len(content))

    def _generate_stored_name(self, original_filename: str) -> str:
        """Generate a unique stored filename to prevent collisions.

        Args:
            original_filename: Original uploaded filename (used for
                               preserving the extension).

        Returns:
            A unique filename string in the form ``<uuid>.pdf``.
        """
        unique_id = str(uuid.uuid4())
        ext = Path(original_filename).suffix.lower()
        return f"{unique_id}{ext}"

    def save_file(self, filename: str, content: bytes) -> Path:
        """Save validated file content to disk.

        The file is saved under a UUID-based name so the original filename
        never appears on the filesystem, preventing path-traversal attacks.

        Args:
            filename: Original uploaded filename (used only for
                      extension detection).
            content:  Validated file bytes.

        Returns:
            Absolute ``Path`` to the saved file on disk.
        """
        stored_name = self._generate_stored_name(filename)
        file_path = self.UPLOAD_DIR / stored_name
        file_path.write_bytes(content)
        logger.info(
            "File saved: %s (original: %s, size: %d bytes)",
            stored_name,
            filename,
            len(content),
        )
        return file_path.resolve()

    def delete_file(self, file_path: str | Path) -> bool:
        """Delete a previously stored file from disk.

        Args:
            file_path: Path to the file to delete.

        Returns:
            ``True`` if the file was deleted, ``False`` if it did not exist.
        """
        path = Path(file_path)
        if path.exists():
            path.unlink()
            logger.info("Deleted file: %s", path)
            return True
        logger.warning("File not found for deletion: %s", path)
        return False
