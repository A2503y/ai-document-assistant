from dataclasses import dataclass

from .document import Document
from .metadata import ChunkMetadata


@dataclass
class Chunk:

    chunk_id: str

    document: Document

    text: str

    metadata: ChunkMetadata

    embedding: list[float] | None = None
