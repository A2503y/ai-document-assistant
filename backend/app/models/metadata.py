from dataclasses import dataclass
from typing import Optional


@dataclass
class ChunkMetadata:

    page: Optional[int] = None

    paragraph: Optional[int] = None

    heading: Optional[str] = None

    section: Optional[str] = None

    chunk_number: int = 0

    word_count: int = 0

    char_count: int = 0