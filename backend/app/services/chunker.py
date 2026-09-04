import uuid

from ..models.chunk import Chunk
from ..models.document import Document
from ..models.metadata import ChunkMetadata
from .pdf_parser import PDFPage


class PageTextChunker:
    """Split page text into overlapping, word-based chunks."""

    def __init__(self, chunk_size: int = 512, overlap: int = 64):
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive.")
        if overlap < 0 or overlap >= chunk_size:
            raise ValueError("overlap must be at least 0 and smaller than chunk_size.")
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_pages(self, document: Document, pages: list[PDFPage]) -> list[Chunk]:
        chunks: list[Chunk] = []
        step = self.chunk_size - self.overlap
        chunk_number = 1
        for page in pages:
            words = page.text.split()
            for start in range(0, len(words), step):
                chunk_words = words[start : start + self.chunk_size]
                if not chunk_words:
                    continue
                text = " ".join(chunk_words)
                chunks.append(Chunk(
                    chunk_id=str(uuid.uuid4()),
                    document=document,
                    text=text,
                    metadata=ChunkMetadata(
                        page=page.page_number,
                        chunk_number=chunk_number,
                        word_count=len(chunk_words),
                        char_count=len(text),
                    ),
                ))
                chunk_number += 1
                if start + self.chunk_size >= len(words):
                    break
        return chunks
