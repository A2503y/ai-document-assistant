import fitz
from fastapi.testclient import TestClient

from app.main import app
from app.services.vectordb import get_collection


def _make_pdf_bytes() -> bytes:
    pdf = fitz.open()
    first = pdf.new_page()
    first.insert_text((72, 72), "Apples are red and grow in orchards.")
    second = pdf.new_page()
    second.insert_text((72, 72), "Bananas are yellow and contain potassium.")
    result = pdf.tobytes()
    pdf.close()
    return result


def _fake_embeddings(chunks):
    for index, chunk in enumerate(chunks):
        chunk.embedding = [1.0, float(index), 0.5]
    return chunks


def test_upload_indexes_chunks_with_metadata_and_blocks_duplicates(monkeypatch):
    monkeypatch.setattr("app.api.upload.generate_embeddings", _fake_embeddings)
    client = TestClient(app)
    pdf_bytes = _make_pdf_bytes()

    response = client.post(
        "/upload",
        files={"file": ("../../fruit report.pdf", pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["filename"] == "fruit report.pdf"
    stored = get_collection().get(where={"document_id": payload["document_id"]}, include=["metadatas"])
    assert len(stored["ids"]) == payload["total_chunks"]
    assert {metadata["page"] for metadata in stored["metadatas"]} == {1, 2}
    assert {metadata["document_name"] for metadata in stored["metadatas"]} == {"fruit report.pdf"}

    retrieved = get_collection().query(
        query_embeddings=[[1.0, 0.0, 0.5]],
        n_results=1,
        include=["documents", "metadatas"],
        where={"document_id": payload["document_id"]},
    )
    assert retrieved["documents"][0]
    assert retrieved["metadatas"][0][0]["document_name"] == "fruit report.pdf"
    assert retrieved["metadatas"][0][0]["page"] in {1, 2}

    duplicate = client.post(
        "/upload",
        files={"file": ("same-content.pdf", pdf_bytes, "application/pdf")},
    )
    assert duplicate.status_code == 409
    assert len(get_collection().get(where={"document_id": payload["document_id"]})["ids"]) == payload["total_chunks"]


def test_upload_rejects_fake_pdf_even_when_mime_type_is_pdf(monkeypatch):
    monkeypatch.setattr("app.api.upload.generate_embeddings", _fake_embeddings)
    response = TestClient(app).post(
        "/upload",
        files={"file": ("fake.pdf", b"not really a pdf", "application/pdf")},
    )
    assert response.status_code == 400
    assert "valid PDF" in response.json()["detail"]
