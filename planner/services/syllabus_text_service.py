from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PyPdfError

from planner.services.syllabus_service import get_syllabus


MAX_PDF_PAGES = 50
MAX_TEXT_CHARACTERS = 100_000


class SyllabusExtractionError(Exception):
    """An extraction problem that can be explained to the user."""


def extract_syllabus_text(user, syllabus_id):
    """Extract text only from a syllabus owned by the current user."""
    syllabus = get_syllabus(user, syllabus_id)
    extension = Path(syllabus.original_filename).suffix.lower()

    try:
        with syllabus.file.open("rb") as file_handle:
            if extension == ".txt":
                text = _extract_txt(file_handle)
            elif extension == ".pdf":
                text = _extract_pdf(file_handle)
            else:
                raise SyllabusExtractionError(
                    "Only PDF and TXT files are supported."
                )
    except FileNotFoundError:
        raise SyllabusExtractionError(
            "The uploaded syllabus file could not be found."
        ) from None
    except OSError:
        raise SyllabusExtractionError(
            "The syllabus file could not be read. Please try again."
        ) from None

    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()

    if not text:
        raise SyllabusExtractionError(
            "No readable text was found. "
            "For scanned PDFs, upload a text-based PDF or UTF-8 TXT file."
        )

    if len(text) > MAX_TEXT_CHARACTERS:
        raise SyllabusExtractionError(
            "The syllabus contains too much text. "
            "Please upload a shorter document."
        )

    return syllabus, text


def _extract_txt(file_handle):
    """Read the UTF-8 text format already accepted by the upload form."""
    try:
        text = file_handle.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        raise SyllabusExtractionError(
            "The TXT file must use UTF-8 encoding."
        ) from None

    if "\x00" in text:
        raise SyllabusExtractionError(
            "The TXT file contains unsupported binary content."
        )

    return text


def _extract_pdf(file_handle):
    """Read text from a PDF without performing OCR."""
    try:
        reader = PdfReader(file_handle)

        if reader.is_encrypted:
            raise SyllabusExtractionError(
                "Password-protected PDFs are not supported. "
                "Please upload an unencrypted copy."
            )

        if len(reader.pages) > MAX_PDF_PAGES:
            raise SyllabusExtractionError(
                "The PDF must contain 50 pages or fewer."
            )

        parts = []
        character_count = 0

        for page in reader.pages:
            page_text = page.extract_text() or ""
            character_count += len(page_text)

            if character_count > MAX_TEXT_CHARACTERS:
                raise SyllabusExtractionError(
                    "The syllabus contains too much text. "
                    "Please upload a shorter document."
                )

            parts.append(page_text)

        return "\n\n".join(parts)
    except PyPdfError:
        raise SyllabusExtractionError(
            "The PDF could not be processed. "
            "Please upload a valid text-based PDF."
        ) from None