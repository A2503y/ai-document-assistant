from functools import lru_cache

import chromadb

from ..config import settings
from ..models.chunk import Chunk


@lru_cache
def get_collection():
    """Return the configured persistent collection used by ingestion and retrieval."""
    settings.ensure_directories()
    client = chromadb.PersistentClient(path=str(settings.vector_db_dir))
    return client.get_or_create_collection(name="documents", metadata={"hnsw:space": "cosine"})


def document_exists(document_id: str) -> bool:
    return bool(get_collection().get(where={"document_id": document_id}, limit=1)["ids"])


def indexed_document_ids() -> set[str]:
    """Return the stable IDs currently represented in the vector store."""
    records = get_collection().get(include=["metadatas"])
    return {
        metadata["document_id"]
        for metadata in records["metadatas"]
        if metadata and metadata.get("document_id")
    }


def delete_document(document_id: str) -> None:
    get_collection().delete(where={"document_id": document_id})


def store_embeddings(chunks: list[Chunk]) -> None:
    """Store fully embedded chunks in one ChromaDB operation."""
    if not chunks:
        raise ValueError("Cannot store an empty chunk list.")
    if any(chunk.embedding is None for chunk in chunks):
        raise ValueError("Every chunk must have an embedding before storage.")
    metadatas = []
    for chunk in chunks:
        metadatas.append({
            "document_id": chunk.document.document_id,
            "document_name": chunk.document.document_name,
            "document_type": chunk.document.document_type,
            "source": chunk.document.source,
            "uploaded_at": chunk.document.uploaded_at.isoformat(),
            "page": chunk.metadata.page if chunk.metadata.page is not None else -1,
            "paragraph": chunk.metadata.paragraph if chunk.metadata.paragraph is not None else -1,
            "chunk_number": chunk.metadata.chunk_number,
            "word_count": chunk.metadata.word_count,
            "char_count": chunk.metadata.char_count,
        })
    get_collection().add(
        ids=[chunk.chunk_id for chunk in chunks],
        documents=[chunk.text for chunk in chunks],
        embeddings=[chunk.embedding for chunk in chunks],
        metadatas=metadatas,
    )
