from pathlib import Path

from app.models.document import Document
from app.services.chunker import PageTextChunker
from app.services.pdf_parser import PDFPage


def test_chunker_applies_overlap_and_retains_page_metadata():
    document = Document.create(Path("example.pdf"), content_hash="document-hash")
    chunks = PageTextChunker(chunk_size=5, overlap=2).chunk_pages(
        document,
        [PDFPage(7, "one two three four five six seven eight nine")],
    )

    assert [chunk.text for chunk in chunks] == [
        "one two three four five",
        "four five six seven eight",
        "seven eight nine",
    ]
    assert [chunk.metadata.page for chunk in chunks] == [7, 7, 7]
    assert [chunk.metadata.chunk_number for chunk in chunks] == [1, 2, 3]
    assert all(chunk.document.document_id == "document-hash" for chunk in chunks)


def test_chunker_rejects_invalid_window_settings():
    import pytest
    with pytest.raises(ValueError):
        PageTextChunker(chunk_size=5, overlap=5)
