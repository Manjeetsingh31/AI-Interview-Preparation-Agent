"""Unit and integration tests for the Resume Upload and PDF Processing module.

Test coverage:
    - ``FileStorageService``: validation (type, magic bytes, size), save, delete.
    - ``ResumeParser``: extraction from valid / empty / corrupted PDFs.
    - API endpoint: full upload flow via ``TestClient`` with a real database.

Run with::

    cd backend
    pytest app/tests/test_resume_upload.py -v
"""

import logging
import os
from pathlib import Path

import fitz
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.core.db import Base as DbBase
from backend.app.models import models
from backend.app.services.file_storage import (
    FileStorageService,
    InvalidFileTypeError,
    FileSizeExceededError,
)
from backend.app.services.resume_parser import (
    ResumeParser,
    CorruptedPDFError,
    EmptyPDFError,
    PasswordProtectedPDFError,
)

logging.disable(logging.CRITICAL)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def storage_service(tmp_path):
    """Return a ``FileStorageService`` with a temp upload dir and 1 MB limit."""
    return FileStorageService(
        upload_dir=tmp_path / "uploads",
        max_file_size=1024 * 1024,  # 1 MB for testing
    )


@pytest.fixture
def parser():
    """Return a ``ResumeParser`` instance."""
    return ResumeParser()


@pytest.fixture
def valid_pdf_bytes():
    """Return bytes of a minimal valid PDF with extractable text."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "John Doe", fontsize=12)
    page.insert_text((72, 120), "Python Developer with 5 years experience", fontsize=12)
    result = doc.tobytes()
    doc.close()
    return result


@pytest.fixture
def two_page_pdf_bytes():
    """Return bytes of a two-page PDF with extractable text."""
    doc = fitz.open()
    page1 = doc.new_page()
    page1.insert_text((72, 72), "Page One Content", fontsize=12)
    page2 = doc.new_page()
    page2.insert_text((72, 72), "Page Two Content", fontsize=12)
    result = doc.tobytes()
    doc.close()
    return result


@pytest.fixture
def no_text_pdf_bytes():
    """Return bytes of a PDF that has a page but no text drawn on it."""
    doc = fitz.open()
    doc.new_page()  # page exists — no text
    result = doc.tobytes()
    doc.close()
    return result


@pytest.fixture
def zero_page_pdf_bytes():
    """Return bytes of a minimal valid PDF with zero pages.

    ``fitz`` refuses to save a document without pages, so we craft the
    raw PDF structure manually.
    """
    return (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\n"
        b"xref\n0 3\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"trailer\n<< /Size 3 /Root 1 0 R >>\n"
        b"startxref\n117\n"
        b"%%EOF"
    )


@pytest.fixture
def corrupted_pdf_bytes():
    """Return bytes that start with the PDF magic header but are structurally
    invalid — ``fitz`` will fail to open them."""
    return b"%PDF-1.4\n%%EOF"


@pytest.fixture
def non_pdf_bytes():
    """Return plain-text bytes (no PDF magic header)."""
    return b"This is not a PDF file at all."


@pytest.fixture
def large_pdf_bytes():
    """Return a PDF padded to ~2 MB (above the test limit of 1 MB)."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "x" * 500, fontsize=12)
    result = doc.tobytes()
    doc.close()
    return result + b"0" * (2 * 1024 * 1024)


# ============================================================================
# FileStorageService — Unit Tests
# ============================================================================


class TestFileStorageServiceValidate:
    """Tests for ``FileStorageService.validate_file()``."""

    def test_valid_pdf_passes(self, storage_service, valid_pdf_bytes):
        """Valid PDF (correct extension + magic bytes + size) should not raise."""
        storage_service.validate_file("resume.pdf", valid_pdf_bytes)

    def test_invalid_extension_raises(self, storage_service, valid_pdf_bytes):
        """A ``.txt`` file should be rejected even if its content is valid PDF."""
        with pytest.raises(InvalidFileTypeError, match="Only PDF files"):
            storage_service.validate_file("resume.txt", valid_pdf_bytes)

    def test_no_extension_raises(self, storage_service, valid_pdf_bytes):
        """A file without an extension should be rejected."""
        with pytest.raises(InvalidFileTypeError, match="Only PDF files"):
            storage_service.validate_file("resume", valid_pdf_bytes)

    def test_missing_magic_bytes_raises(self, storage_service, non_pdf_bytes):
        """A ``.pdf`` file that lacks the ``%PDF`` header should be rejected."""
        with pytest.raises(InvalidFileTypeError, match="missing PDF header"):
            storage_service.validate_file("resume.pdf", non_pdf_bytes)

    def test_size_exceeded_raises(self, storage_service, large_pdf_bytes):
        """A file above ``MAX_FILE_SIZE`` should raise ``FileSizeExceededError``."""
        with pytest.raises(FileSizeExceededError, match="exceeds the maximum"):
            storage_service.validate_file("resume.pdf", large_pdf_bytes)


class TestFileStorageServiceSaveDelete:
    """Tests for ``FileStorageService.save_file()`` and ``delete_file()``."""

    def test_save_file_returns_existing_path(self, storage_service, valid_pdf_bytes):
        """Saved file should exist on disk with the correct content."""
        path = storage_service.save_file("resume.pdf", valid_pdf_bytes)
        assert path.exists(), f"File not found at {path}"
        assert path.suffix == ".pdf"
        assert path.read_bytes() == valid_pdf_bytes

    def test_save_file_unique_names(self, storage_service, valid_pdf_bytes):
        """Consecutive saves should produce different filenames."""
        path1 = storage_service.save_file("resume.pdf", valid_pdf_bytes)
        path2 = storage_service.save_file("resume.pdf", valid_pdf_bytes)
        assert path1.name != path2.name, "UUID-based names must be unique"

    def test_delete_existing_file(self, storage_service, valid_pdf_bytes):
        """``delete_file`` should return ``True`` and remove the file."""
        path = storage_service.save_file("resume.pdf", valid_pdf_bytes)
        assert storage_service.delete_file(path) is True
        assert not path.exists()

    def test_delete_nonexistent_file(self, storage_service):
        """``delete_file`` should return ``False`` for a missing file."""
        assert storage_service.delete_file("/nonexistent/file.pdf") is False


# ============================================================================
# ResumeParser — Unit Tests
# ============================================================================


class TestResumeParserExtractText:
    """Tests for ``ResumeParser.extract_text()``."""

    def test_valid_pdf_returns_text_and_page_count(self, parser, tmp_path, valid_pdf_bytes):
        """Should return extracted text and the correct page count."""
        pdf_path = tmp_path / "valid.pdf"
        pdf_path.write_bytes(valid_pdf_bytes)

        result = parser.extract_text(pdf_path)
        assert "John Doe" in result["extracted_text"]
        assert "Python Developer" in result["extracted_text"]
        assert result["pages"] == 1

    def test_two_page_pdf(self, parser, tmp_path, two_page_pdf_bytes):
        """Text from all pages should be concatenated."""
        pdf_path = tmp_path / "two.pdf"
        pdf_path.write_bytes(two_page_pdf_bytes)

        result = parser.extract_text(pdf_path)
        assert "Page One Content" in result["extracted_text"]
        assert "Page Two Content" in result["extracted_text"]
        assert result["pages"] == 2

    def test_no_text_on_page_raises_empty(self, parser, tmp_path, no_text_pdf_bytes):
        """A PDF with pages but no text should raise ``EmptyPDFError``."""
        pdf_path = tmp_path / "notext.pdf"
        pdf_path.write_bytes(no_text_pdf_bytes)

        with pytest.raises(EmptyPDFError, match="No extractable text"):
            parser.extract_text(pdf_path)

    def test_zero_pages_raises_empty(self, parser, tmp_path, zero_page_pdf_bytes):
        """A PDF with zero pages should raise ``EmptyPDFError``."""
        pdf_path = tmp_path / "zeropages.pdf"
        pdf_path.write_bytes(zero_page_pdf_bytes)

        with pytest.raises(EmptyPDFError, match="has no pages"):
            parser.extract_text(pdf_path)

    def test_corrupted_pdf_raises_corrupted(self, parser, tmp_path, corrupted_pdf_bytes):
        """Structurally invalid PDF should raise ``CorruptedPDFError``."""
        pdf_path = tmp_path / "corrupted.pdf"
        pdf_path.write_bytes(corrupted_pdf_bytes)

        with pytest.raises(CorruptedPDFError, match="Failed to open PDF"):
            parser.extract_text(pdf_path)

    def test_nonexistent_file_raises_filenotfound(self, parser):
        """A path that does not exist should raise ``FileNotFoundError``."""
        with pytest.raises(FileNotFoundError, match="PDF file not found"):
            parser.extract_text("/nonexistent/file.pdf")

    def test_random_bytes_raises_corrupted(self, parser, tmp_path):
        """Random bytes with ``.pdf`` extension should raise error."""
        pdf_path = tmp_path / "random.pdf"
        pdf_path.write_bytes(os.urandom(256))

        with pytest.raises(CorruptedPDFError):
            parser.extract_text(pdf_path)


# ============================================================================
# Full-Flow Integration: API endpoint via TestClient
# ============================================================================


class TestResumeUploadAPI:
    """Integration tests for ``POST /api/resumes/upload``.

    Uses an isolated SQLite file database with the same schema as the
    production application.  Both the ``get_db`` and ``get_current_user_id``
    dependencies are overridden so no external database is needed.
    """

    @pytest.fixture
    def api_client(self, tmp_path):
        """Build a FastAPI ``TestClient`` with overridden dependencies."""

        # --- Create an isolated test database ---------------------------------
        db_path = tmp_path / "test.db"
        engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
        )
        DbBase.metadata.create_all(bind=engine)
        TestSession = sessionmaker(bind=engine)

        # --- Seed a mock user ------------------------------------------------
        session = TestSession()
        user = models.User(
            email="test_resume@example.com",
            password_hash="test_hash",
        )
        session.add(user)
        session.commit()
        user_id = user.id
        session.close()

        # --- Build app with overridden deps ----------------------------------
        from backend.app.api.resume import (
            router as resume_router,
            get_current_user_id,
            get_db,
            storage,
        )

        app = FastAPI()
        app.include_router(resume_router)

        def _override_get_db():
            db = TestSession()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = _override_get_db
        app.dependency_overrides[get_current_user_id] = lambda: user_id

        # Redirect file storage to a temp directory and use 1 MB limit
        original_upload_dir = storage.UPLOAD_DIR
        original_max_size = storage.MAX_FILE_SIZE
        storage.UPLOAD_DIR = tmp_path / "uploads"
        storage.MAX_FILE_SIZE = 1024 * 1024  # 1 MB for testing
        storage.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

        client = TestClient(app)

        yield client, user_id

        # Restore
        storage.UPLOAD_DIR = original_upload_dir
        storage.MAX_FILE_SIZE = original_max_size

    def test_upload_valid_pdf_returns_201(self, api_client, valid_pdf_bytes):
        """Happy-path: a valid PDF should return 201 with extracted text."""
        client, _ = api_client
        response = client.post(
            "/api/resumes/upload",
            files={"file": ("resume.pdf", valid_pdf_bytes, "application/pdf")},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["filename"] == "resume.pdf"
        assert data["pages"] == 1
        assert "John Doe" in data["extracted_text"]
        assert "upload_time" in data

    def test_upload_invalid_file_type_returns_400(self, api_client, non_pdf_bytes):
        """A non-PDF file should return 400."""
        client, _ = api_client
        response = client.post(
            "/api/resumes/upload",
            files={"file": ("resume.txt", non_pdf_bytes, "text/plain")},
        )
        assert response.status_code == 400
        assert "Only PDF files" in response.json()["detail"]

    def test_upload_large_file_returns_413(self, api_client, large_pdf_bytes):
        """An oversized file should return 413."""
        client, _ = api_client
        response = client.post(
            "/api/resumes/upload",
            files={"file": ("resume.pdf", large_pdf_bytes, "application/pdf")},
        )
        assert response.status_code == 413
        assert "exceeds the maximum" in response.json()["detail"]

    def test_upload_corrupted_pdf_returns_400(
        self, api_client, corrupted_pdf_bytes
    ):
        """A corrupted PDF should return 400."""
        client, _ = api_client
        response = client.post(
            "/api/resumes/upload",
            files={
                "file": ("corrupted.pdf", corrupted_pdf_bytes, "application/pdf"),
            },
        )
        assert response.status_code == 400
        assert "Failed to open PDF" in response.json()["detail"]

    def test_upload_empty_pdf_returns_400(
        self, api_client, zero_page_pdf_bytes
    ):
        """A PDF with zero pages should return 400."""
        client, _ = api_client
        response = client.post(
            "/api/resumes/upload",
            files={"file": ("empty.pdf", zero_page_pdf_bytes, "application/pdf")},
        )
        assert response.status_code == 400
        assert "has no pages" in response.json()["detail"]

    def test_upload_no_text_pdf_returns_400(
        self, api_client, no_text_pdf_bytes
    ):
        """A PDF with no extractable text should return 400."""
        client, _ = api_client
        response = client.post(
            "/api/resumes/upload",
            files={"file": ("notext.pdf", no_text_pdf_bytes, "application/pdf")},
        )
        assert response.status_code == 400
        assert "No extractable text" in response.json()["detail"]
