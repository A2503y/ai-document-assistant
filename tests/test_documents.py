import fitz
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.services.vectordb import document_exists


def _pdf_bytes() -> bytes:
    pdf = fitz.open()
    page = pdf.new_page()
    page.insert_text((72, 72), "Document management test content.")
    result = pdf.tobytes()
    pdf.close()
    return result


def _fake_embeddings(chunks):
    for index, chunk in enumerate(chunks):
        chunk.embedding = [1.0, float(index), 0.5]
    return chunks


def test_list_documents_and_delete_removes_vectors_and_pdf(monkeypatch):
    monkeypatch.setattr("app.api.upload.generate_embeddings", _fake_embeddings)
    client = TestClient(app)
    upload = client.post(
        "/upload",
        files={"file": ("managed.pdf", _pdf_bytes(), "application/pdf")},
    )
    assert upload.status_code == 200
    document_id = upload.json()["document_id"]
    stored_pdf = settings.upload_dir / f"{document_id[:12]}_managed.pdf"
    assert stored_pdf.exists()

    documents = client.get("/documents")
    assert documents.status_code == 200
    assert documents.json() == [{
        "document_id": document_id,
        "filename": "managed.pdf",
        "document_type": "pdf",
        "uploaded_at": documents.json()[0]["uploaded_at"],
        "page_count": 1,
        "chunk_count": upload.json()["total_chunks"],
    }]

    deleted = client.delete(f"/documents/{document_id}")
    assert deleted.status_code == 204
    assert not document_exists(document_id)
    assert not stored_pdf.exists()
    assert client.get("/documents").json() == []
    assert client.delete(f"/documents/{document_id}").status_code == 404
