from dataclasses import dataclass, field
from datetime import datetime
import hashlib
from pathlib import Path


@dataclass
class Document:
    document_id: str
    document_name: str
    document_type: str
    file_path: Path
    source: str = "local"
    uploaded_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def create(
        cls,
        file_path: Path,
        content_hash: str | None = None,
        document_name: str | None = None,
    ) -> "Document":
        """Create a stable identity from the PDF's SHA-256 content hash."""
        if content_hash is None:
            hasher = hashlib.sha256()
            with file_path.open("rb") as file:
                for block in iter(lambda: file.read(1024 * 1024), b""):
                    hasher.update(block)
            content_hash = hasher.hexdigest()
        return cls(
            content_hash,
            document_name or file_path.name,
            "pdf",
            file_path,
        )
