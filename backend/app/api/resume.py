"""Resume upload API router.

Handles PDF resume upload, validation, secure storage, and text extraction.
Returns a structured JSON response with the extracted content and metadata.

Design decisions:
    - The router is an ``APIRouter`` with ``prefix="/api/resumes"`` so it can
      be included in ``main.py`` without duplicating the path prefix.
    - A lightweight Pydantic response model (``ResumeUploadResponse``) is
      defined here rather than in ``schemas/`` to keep the module self-contained
      and avoid touching existing schema files.
    - File validation and parsing are delegated to dedicated service classes
      (``FileStorageService`` and ``ResumeParser``), keeping the endpoint thin.
    - Every failure mode maps to a specific HTTP status code:
        * ``400`` for bad input (invalid type, corrupted PDF, empty PDF, etc.)
        * ``413`` for payload-too-large
        * ``500`` for unexpected server errors
"""

import hashlib
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models import models
from backend.app.models.user import User
from backend.app.services.file_storage import (
    FileStorageService,
    InvalidFileTypeError,
    FileSizeExceededError,
)
from backend.app.services.resume_parser import (
    ResumeParser,
    CorruptedPDFError,
    PasswordProtectedPDFError,
    EmptyPDFError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/resumes", tags=["resumes"])

# --- Singleton service instances (stateless, safe to share) -----------------
storage = FileStorageService()
parser = ResumeParser()


# --- Pydantic response schema -----------------------------------------------
class ResumeUploadResponse(BaseModel):
    """Schema for the resume upload response.

    Returned after a successful upload — contains the original filename,
    page count, full extracted text, and an ISO-8601 upload timestamp.
    """

    filename: str = Field(..., description="Original uploaded filename")
    pages: int = Field(..., ge=1, description="Number of PDF pages")
    extracted_text: str = Field(..., description="Full text extracted from the PDF")
    upload_time: str = Field(..., description="ISO-8601 timestamp of the upload")

    model_config = {"json_schema_extra": {
        "example": {
            "filename": "resume.pdf",
            "pages": 2,
            "extracted_text": "John Doe\nPython Developer\n...",
            "upload_time": "2026-06-26T12:00:00+00:00",
        },
    }}


# --- Authentication dependency (mirrors the logic in main.py) ---------------
def get_current_user_id(db: Session = Depends(get_db)) -> str:
    """Return the ID of the default mock user.

    Uses the same logic as ``main.py`` to stay consistent with the rest of
    the application.  In production this would decode a JWT from the
    ``Authorization`` header instead.

    Args:
        db: Database session (injected by FastAPI).

    Returns:
        The ``id`` (UUID string) of the authenticated user.
    """
    user = (
        db.query(User)
        .filter(User.email == "candidate@example.com")
        .first()
    )
    if not user:
        user = User(
            email="candidate@example.com",
            password_hash=hashlib.sha256(b"password123").hexdigest(),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info("Created default mock user: id=%s", user.id)
    return user.id


# --- Endpoint ----------------------------------------------------------------
@router.post(
    "/upload",
    response_model=ResumeUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a PDF resume",
    description=(
        "Accepts a PDF file via ``multipart/form-data``, validates the file "
        "type and size, stores it securely on disk, extracts the text content "
        "using PyMuPDF, and persists the metadata to the database."
    ),
)
async def upload_resume(
    file: UploadFile = File(..., description="The PDF resume file to upload"),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> ResumeUploadResponse:
    """Upload and process a PDF resume.

    The endpoint performs the following steps in order:

    1. Read the uploaded file bytes.
    2. Validate the file type (``.pdf`` extension + ``%PDF`` magic bytes)
       and enforce the 10 MB size limit.
    3. Save the file to disk under a UUID-based name.
    4. Extract text content with PyMuPDF (``fitz``).
    5. Persist file metadata to the ``resumes`` table.
    6. Return structured JSON with filename, page count, extracted text,
       and the upload timestamp.

    Args:
        file:   The uploaded PDF file (multipart/form-data).
        db:     Database session (injected by FastAPI).
        user_id: Authenticated user ID (injected by the auth dependency).

    Returns:
        ``ResumeUploadResponse`` with the extracted content and metadata.

    Raises:
        HTTPException 400: Invalid file type, corrupted PDF, empty PDF,
                           or password-protected PDF.
        HTTPException 413: File exceeds the maximum allowed size.
        HTTPException 500: File storage or database error.
    """
    upload_time = datetime.now(timezone.utc).isoformat()

    # --- Step 1: Read file content -------------------------------------------
    try:
        content = await file.read()
    except Exception as exc:
        logger.error("Failed to read uploaded file: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read the uploaded file. Please try again.",
        ) from exc

    filename: str = file.filename or "untitled.pdf"
    logger.info("Upload request: %s (%d bytes)", filename, len(content))

    # --- Step 2: Validate file -----------------------------------------------
    try:
        storage.validate_file(filename, content)
    except InvalidFileTypeError as exc:
        logger.warning("Rejected invalid file type: %s — %s", filename, exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except FileSizeExceededError as exc:
        logger.warning("Rejected oversized file: %s — %s", filename, exc)
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=str(exc),
        ) from exc

    # --- Step 3: Save file to disk -------------------------------------------
    try:
        saved_path = storage.save_file(filename, content)
        logger.debug("File saved to: %s", saved_path)
    except Exception as exc:
        logger.error("Failed to save file to disk: %s — %s", filename, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store the uploaded file. Please try again.",
        ) from exc

    # --- Step 4: Extract text from PDF ---------------------------------------
    try:
        parsed = parser.extract_text(saved_path)
    except FileNotFoundError as exc:
        logger.error("Saved file missing: %s — %s", saved_path, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Uploaded file could not be located after storage.",
        ) from exc
    except CorruptedPDFError as exc:
        logger.error("Corrupted PDF: %s — %s", filename, exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except PasswordProtectedPDFError as exc:
        logger.warning("Password-protected PDF rejected: %s — %s", filename, exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except EmptyPDFError as exc:
        logger.warning("Empty PDF rejected: %s — %s", filename, exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error("Unexpected parsing error: %s — %s", filename, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing the PDF.",
        ) from exc

    # --- Step 5: Persist to database -----------------------------------------
    try:
        resume_record = models.Resume(
            user_id=user_id,
            filename=filename,
            file_path=str(saved_path),
            parsed_data={
                "pages": parsed["pages"],
                "extracted_text": parsed["extracted_text"],
                "content_length": len(parsed["extracted_text"]),
            },
        )
        db.add(resume_record)
        db.commit()
        db.refresh(resume_record)
        logger.info(
            "Resume record saved: id=%s, filename=%s, pages=%d",
            resume_record.id,
            filename,
            parsed["pages"],
        )
    except Exception as exc:
        db.rollback()
        logger.error("Database error while saving resume: %s — %s", filename, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save resume metadata to the database.",
        ) from exc

    # --- Step 6: Return structured response ----------------------------------
    return ResumeUploadResponse(
        filename=filename,
        pages=parsed["pages"],
        extracted_text=parsed["extracted_text"],
        upload_time=upload_time,
    )
