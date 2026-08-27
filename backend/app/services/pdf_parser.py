from dataclasses import dataclass
from pathlib import Path

import fitz


class PDFParsingError(ValueError):
    """Raised when an upload is not a usable text-based PDF."""


@dataclass(frozen=True)
class PDFPage:
    page_number: int
    text: str


def extract_pages(pdf_path: Path) -> list[PDFPage]:
    """Extract text from each page while retaining its one-based page number."""
    try:
        document = fitz.open(stream=pdf_path.read_bytes(), filetype="pdf")
    except (fitz.FileDataError, RuntimeError, OSError) as error:
        raise PDFParsingError("The uploaded file is not a valid PDF.") from error
    try:
        if document.page_count == 0:
            raise PDFParsingError("The uploaded PDF has no pages.")
        pages = [PDFPage(index, page.get_text("text")) for index, page in enumerate(document, start=1)]
    except (fitz.FileDataError, RuntimeError, OSError) as error:
        raise PDFParsingError("Text could not be extracted from the uploaded PDF.") from error
    finally:
        document.close()
    if not any(page.text.strip() for page in pages):
        raise PDFParsingError("The PDF contains no extractable text.")
    return pages


def extract_text(pdf_path: Path) -> str:
    return "\n\n".join(page.text for page in extract_pages(pdf_path))
