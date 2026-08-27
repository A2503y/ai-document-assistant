"""Central application paths and upload settings."""

from dataclasses import dataclass
import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    upload_dir: Path
    vector_db_dir: Path
    max_upload_bytes: int
    max_retrieved_chunks: int
    max_context_characters: int
    openai_model: str

    @classmethod
    def from_environment(cls) -> "Settings":
        data_dir = Path(os.getenv("AI_DOCUMENT_ASSISTANT_DATA_DIR", PROJECT_ROOT / "data")).resolve()
        max_upload_mb = int(os.getenv("AI_DOCUMENT_ASSISTANT_MAX_UPLOAD_MB", "15"))
        if max_upload_mb <= 0:
            raise ValueError("AI_DOCUMENT_ASSISTANT_MAX_UPLOAD_MB must be positive.")
        max_retrieved_chunks = int(os.getenv("AI_DOCUMENT_ASSISTANT_MAX_TOP_K", "8"))
        max_context_characters = int(os.getenv("AI_DOCUMENT_ASSISTANT_MAX_CONTEXT_CHARS", "12000"))
        if max_retrieved_chunks <= 0 or max_context_characters <= 0:
            raise ValueError("RAG limits must be positive.")
        return cls(
            data_dir,
            data_dir / "uploads",
            data_dir / "chroma",
            max_upload_mb * 1024 * 1024,
            max_retrieved_chunks,
            max_context_characters,
            os.getenv("AI_DOCUMENT_ASSISTANT_OPENAI_MODEL", "gpt-4.1-mini"),
        )

    def ensure_directories(self) -> None:
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.vector_db_dir.mkdir(parents=True, exist_ok=True)


settings = Settings.from_environment()
