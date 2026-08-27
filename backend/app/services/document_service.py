from pathlib import Path

from app.config import settings
from app.services.vectordb import delete_document, get_collection


def list_documents() -> list[dict]:
    """Build document summaries from the metadata stored with indexed chunks."""
    records = get_collection().get(include=["metadatas"])
    documents: dict[str, dict] = {}
    for metadata in records["metadatas"]:
        if not metadata:
            continue
        document_id = metadata["document_id"]
        summary = documents.setdefault(document_id, {
            "document_id": document_id,
            "filename": metadata["document_name"],
            "document_type": metadata.get("document_type"),
            "uploaded_at": metadata.get("uploaded_at"),
            "page_count": None,
            "chunk_count": 0,
        })
        summary["chunk_count"] += 1
        page = metadata.get("page", -1)
        if page >= 0:
            summary["page_count"] = max(summary["page_count"] or 0, page)

    return sorted(documents.values(), key=lambda document: document["uploaded_at"] or "", reverse=True)


def remove_document(document_id: str) -> bool:
    """Remove a document's vectors and its managed upload, when it still exists."""
    matches = get_collection().get(where={"document_id": document_id}, include=["metadatas"])
    if not matches["ids"]:
        return False

    filenames = {metadata["document_name"] for metadata in matches["metadatas"] if metadata}
    for filename in filenames:
        stored_path = (settings.upload_dir / f"{document_id[:12]}_{filename}").resolve()
        if stored_path.parent == settings.upload_dir.resolve():
            stored_path.unlink(missing_ok=True)

    delete_document(document_id)
    return True
