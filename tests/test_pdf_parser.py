import fitz
import pytest

from app.services.pdf_parser import PDFParsingError, extract_pages


def test_extract_pages_preserves_page_numbers(tmp_path):
    path = tmp_path / "two-pages.pdf"
    pdf = fitz.open()
    for text in ("First page text", "Second page text"):
        page = pdf.new_page()
        page.insert_text((72, 72), text)
    pdf.save(path)
    pdf.close()

    pages = extract_pages(path)

    assert [(page.page_number, page.text.strip()) for page in pages] == [
        (1, "First page text"),
        (2, "Second page text"),
    ]


def test_extract_pages_rejects_invalid_or_textless_pdfs(tmp_path):
    invalid = tmp_path / "invalid.pdf"
    invalid.write_bytes(b"not a PDF")
    with pytest.raises(PDFParsingError, match="valid PDF"):
        extract_pages(invalid)

    blank = tmp_path / "blank.pdf"
    pdf = fitz.open()
    pdf.new_page()
    pdf.save(blank)
    pdf.close()
    with pytest.raises(PDFParsingError, match="no extractable text"):
        extract_pages(blank)
