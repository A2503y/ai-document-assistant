from dataclasses import dataclass

from app.models.document import Document
from app.models.metadata import ChunkMetadata


@dataclass
class Chunk:

    chunk_id: str

    document: Document

    text: str

    metadata: ChunkMetadata

    embedding: list[float] | None = None