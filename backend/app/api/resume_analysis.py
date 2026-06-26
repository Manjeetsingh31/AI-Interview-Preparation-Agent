"""ADK Resume Analysis API router.

Provides a single endpoint ``POST /api/resumes/analyze`` that:
1. Accepts a PDF or plain-text resume file via ``multipart/form-data``.
2. Extracts text using the existing ``ResumeParser`` service.
3. Sends the extracted text to the **Google ADK Resume Agent** for
   structured analysis.
4. Persists the raw text and structured JSON to the database.
5. Returns the structured analysis as JSON.

Architecture
------------
::

    Client  ──POST──►  FastAPI Route  ──►  ADK Agent  ──►  Gemini 2.5 Flash
                                │                     │
                                ▼                     ▼
                          Database (raw_text     Structured ResumeData
                           + extracted_json)       (Pydantic JSON)

Every step is logged: upload, parsing, Gemini request, Gemini response,
database save, and any errors.
"""

import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.user import User
from backend.app.schemas.resume_analysis_adk import (
    ResumeData,
    ResumeAnalysisADKCreate,
    ResumeAnalysisADKResponse,
)
from backend.app.crud.crud_resume_analysis_adk import resume_analysis_adk as crud
from backend.app.services.resume_parser import (
    ResumeParser,
    CorruptedPDFError,
    PasswordProtectedPDFError,
    EmptyPDFError,
)
from backend.app.services.agents.resume_agent import (
    ResumeAnalysisAgent,
    ResumeAnalysisError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/resumes", tags=["resumes"])

# --- Singleton service instances -------------------------------------------
_parser = ResumeParser()
_agent = ResumeAnalysisAgent()


# --- Auth dependency (mirrors main.py logic) --------------------------------
def _get_current_user_id(db: Session = Depends(get_db)) -> str:
    """Return the ID of the default mock user.

    Uses the same logic as ``main.py``: if the mock user does not exist
    yet, it is created on the fly.
    """
    user = db.query(User).filter(User.email == "candidate@example.com").first()
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


# --- Endpoint ---------------------------------------------------------------


@router.post(
    "/analyze",
    response_model=ResumeAnalysisADKResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Analyse a resume using the Google ADK agent",
    description=(
        "Upload a PDF or plain-text resume. The file is parsed, sent to the "
        "Google ADK Resume Analysis Agent (powered by Gemini 2.5 Flash), and "
        "the structured extraction (name, contact, skills, education, "
        "experience, projects, certifications, languages) is saved and returned."
    ),
)
async def analyze_resume(
    file: UploadFile = File(..., description="Resume file (PDF or .txt)"),
    db: Session = Depends(get_db),
    user_id: str = Depends(_get_current_user_id),
) -> ResumeAnalysisADKResponse:
    """Analyse a resume and return structured extraction data.

    Args:
        file:    The uploaded resume file (``multipart/form-data``).
        db:      Database session (injected by FastAPI).
        user_id: Authenticated user ID (injected by auth dependency).

    Returns:
        ``ResumeAnalysisADKResponse`` with the extracted data.

    Raises:
        HTTPException 400: Invalid file, empty content, or parsing error.
        HTTPException 500: Agent failure or database error.
    """
    # --- Step 1: Read file --------------------------------------------------
    try:
        content = await file.read()
    except Exception as exc:
        logger.error("Failed to read uploaded file: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read the uploaded file.",
        ) from exc

    filename: str = file.filename or "untitled"
    logger.info("Upload: %s (%d bytes)", filename, len(content))

    if not content or len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    # --- Step 2: Extract text -----------------------------------------------
    raw_text: str = ""
    is_pdf = filename.lower().endswith(".pdf")

    if is_pdf:
        raw_text = await _extract_pdf_text(content, filename)
    else:
        raw_text = _extract_text_content(content, filename)

    if not raw_text or not raw_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No extractable text found in the uploaded file.",
        )

    logger.info("Parsing complete: %d characters extracted", len(raw_text))

    # --- Step 3: Analyse via ADK agent --------------------------------------
    try:
        resume_data: ResumeData = await _agent.analyze(raw_text)
    except ResumeAnalysisError as exc:
        logger.error("ADK agent analysis failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Resume analysis failed: {exc}",
        ) from exc

    # --- Step 4: Save to database -------------------------------------------
    try:
        obj_in = ResumeAnalysisADKCreate(
            user_id=user_id,
            resume_filename=filename,
            raw_text=raw_text,
            extracted_json=resume_data.model_dump(),
        )
        db_obj = crud.create(db=db, obj_in=obj_in)
        logger.info(
            "Database save complete: id=%s, user_id=%s", db_obj.id, user_id
        )
    except Exception as exc:
        logger.error("Database save failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save analysis to the database.",
        ) from exc

    # --- Step 5: Return structured response ---------------------------------
    return ResumeAnalysisADKResponse(
        id=db_obj.id,
        user_id=db_obj.user_id,
        resume_filename=db_obj.resume_filename,
        raw_text=db_obj.raw_text,
        extracted_json=db_obj.extracted_json,
        created_at=db_obj.created_at,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _extract_pdf_text(content: bytes, filename: str) -> str:
    """Save PDF bytes to a temp file and extract text with ``ResumeParser``.

    Args:
        content: Raw PDF file bytes.
        filename: Original filename (used for logging only).

    Returns:
        Extracted text as a single string.

    Raises:
        HTTPException 400: For corrupted, password-protected, or empty PDFs.
    """
    suffix = Path(filename).suffix
    with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = _parser.extract_text(tmp_path)
        return result["extracted_text"]
    except CorruptedPDFError as exc:
        logger.error("Corrupted PDF: %s — %s", filename, exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except PasswordProtectedPDFError as exc:
        logger.warning("Password-protected PDF: %s — %s", filename, exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except EmptyPDFError as exc:
        logger.warning("Empty PDF: %s — %s", filename, exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def _extract_text_content(content: bytes, filename: str) -> str:
    """Decode plain-text file bytes to a string.

    Args:
        content: Raw file bytes assumed to be UTF-8 (or latin-1 fallback).
        filename: Original filename (used for logging only).

    Returns:
        Decoded text string.
    """
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        logger.warning(
            "UTF-8 decode failed for %s, falling back to latin-1", filename
        )
        return content.decode("latin-1")
