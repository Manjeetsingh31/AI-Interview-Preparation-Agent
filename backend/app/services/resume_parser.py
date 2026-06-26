"""PDF resume parsing service.

Extracts text content from PDF resume files using PyMuPDF (``fitz``).
Handles various edge cases including empty PDFs, corrupted documents,
and password-protected files.

Design decisions:
    - PyMuPDF (``fitz``) is chosen over alternatives such as ``pdfplumber``
      because it is faster, does not require numpy, and handles a wider
      range of malformed PDFs without crashing.
    - Each failure mode (corrupted, password-protected, empty) has its own
      exception class so callers can differentiate and respond appropriately.
    - The extractor returns a flat dict rather than a custom object to keep
      the service lightweight and JSON-serialisable.
"""

import logging
from pathlib import Path
from typing import Any, Dict

import fitz

logger = logging.getLogger(__name__)


class ResumeParsingError(Exception):
    """Base exception for resume-parsing errors."""


class CorruptedPDFError(ResumeParsingError):
    """Raised when the PDF file is corrupted or cannot be opened."""


class PasswordProtectedPDFError(ResumeParsingError):
    """Raised when the PDF is password-protected and cannot be read."""


class EmptyPDFError(ResumeParsingError):
    """Raised when the PDF contains no extractable text."""


class ResumeParser:
    """Extracts structured text content from PDF resume files.

    Uses PyMuPDF (``fitz``) under the hood. The public interface is a single
    static method (``extract_text``) that accepts a file path and returns
    a dictionary with the extracted text and page count.

    Usage::

        parser = ResumeParser()
        result = parser.extract_text("/path/to/resume.pdf")
        print(result["pages"])          # 2
        print(result["extracted_text"])  # Full text content
    """

    @staticmethod
    def extract_text(file_path: str | Path) -> Dict[str, Any]:
        """Extract text content from a PDF resume.

        Opens the PDF, iterates through all pages, concatenates the text,
        and returns structured results.

        Args:
            file_path: Path to the PDF file on disk.

        Returns:
            A dictionary containing:
                - ``extracted_text`` (str):  Full text from all pages.
                - ``pages`` (int):           Total number of pages.

        Raises:
            FileNotFoundError:         The path does not point to an existing file.
            CorruptedPDFError:         The file cannot be opened by ``fitz``.
            PasswordProtectedPDFError: The file requires a password to open.
            EmptyPDFError:             The file has no pages or no extractable text.
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        # --- Open the document ------------------------------------------------
        try:
            doc: fitz.Document = fitz.open(str(file_path))
        except Exception as exc:
            raise CorruptedPDFError(
                f"Failed to open PDF: {file_path.name}. "
                "The file may be corrupted or is not a valid PDF.",
            ) from exc

        # --- Password check ---------------------------------------------------
        if doc.needs_pass:
            doc.close()
            raise PasswordProtectedPDFError(
                f"PDF is password-protected: {file_path.name}. "
                "Password-protected PDFs are not supported.",
            )

        pages: int = doc.page_count
        logger.debug("PDF opened: %s (%d pages)", file_path.name, pages)

        if pages == 0:
            doc.close()
            raise EmptyPDFError(
                f"PDF has no pages: {file_path.name}.",
            )

        # --- Extract text page by page ----------------------------------------
        texts: list[str] = []
        for page_num in range(pages):
            page = doc[page_num]
            page_text = page.get_text()
            texts.append(page_text)

        doc.close()

        extracted_text = "\n\n".join(texts).strip()

        if not extracted_text:
            raise EmptyPDFError(
                f"No extractable text found in PDF: {file_path.name}. "
                "The file may be a scanned image (OCR is not supported).",
            )

        logger.info(
            "Text extracted: %s (%d pages, %d characters)",
            file_path.name,
            pages,
            len(extracted_text),
        )

        return {
            "extracted_text": extracted_text,
            "pages": pages,
        }
