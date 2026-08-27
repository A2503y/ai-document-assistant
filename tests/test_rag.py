import fitz
from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.prompts.grounded_answer import SYSTEM_PROMPT, build_user_prompt
from app.services.rag import NoContextError, build_context, format_sources
from app.services.retrieval import retrieve_chunks


def _pdf_bytes(text: str) -> bytes:
    pdf = fitz.open()
    page = pdf.new_page()
    page.insert_text((72, 72), text)
    content = pdf.tobytes()
    pdf.close()
    return content


def _fake_embeddings(chunks):
    for index, chunk in enumerate(chunks):
        chunk.embedding = [1.0, float(index), 0.5]
    return chunks


class _Vector(list):
    def tolist(self):
        return list(self)


class _FakeEmbeddingModel:
    def encode(self, _question):
        return _Vector([1.0, 0.0, 0.5])


def test_ask_returns_grounded_answer_and_page_source(monkeypatch):
    monkeypatch.setattr("app.api.upload.generate_embeddings", _fake_embeddings)
    monkeypatch.setattr("app.services.retrieval.get_embedding_model", lambda: _FakeEmbeddingModel())

    def fake_llm(question, context):
        assert "Paris is the capital of France" in context
        assert question == "What is the capital of France?"
        return "The document states that Paris is the capital of France."

    monkeypatch.setattr("app.services.rag.generate_grounded_answer", fake_llm)
    client = TestClient(app)
    upload = client.post(
        "/upload",
        files={"file": ("sample.pdf", _pdf_bytes("Paris is the capital of France."), "application/pdf")},
    )
    document_id = upload.json()["document_id"]

    response = client.post("/ask", json={"question": "What is the capital of France?", "document_id": document_id})

    assert response.status_code == 200, response.text
    assert response.json()["answer"] == "The document states that Paris is the capital of France."
    assert response.json()["sources"] == [{
        "document_id": document_id,
        "filename": "sample.pdf",
        "page_number": 1,
        "excerpt": "Paris is the capital of France.",
    }]


def test_ask_unanswerable_question_uses_grounded_fallback(monkeypatch):
    monkeypatch.setattr("app.api.upload.generate_embeddings", _fake_embeddings)
    monkeypatch.setattr("app.services.retrieval.get_embedding_model", lambda: _FakeEmbeddingModel())
    monkeypatch.setattr(
        "app.services.rag.generate_grounded_answer",
        lambda _question, _context: "The information could not be found in the uploaded documents.",
    )
    client = TestClient(app)
    upload = client.post(
        "/upload",
        files={"file": ("sample.pdf", _pdf_bytes("This document describes apples."), "application/pdf")},
    )

    response = client.post("/ask", json={"question": "What is the company revenue?", "document_id": upload.json()["document_id"]})

    assert response.status_code == 200
    assert response.json()["answer"] == "The information could not be found in the uploaded documents."
    assert response.json()["sources"][0]["page_number"] == 1


def test_retrieval_filters_to_selected_document(monkeypatch):
    monkeypatch.setattr("app.api.upload.generate_embeddings", _fake_embeddings)
    monkeypatch.setattr("app.services.retrieval.get_embedding_model", lambda: _FakeEmbeddingModel())
    client = TestClient(app)
    first = client.post(
        "/upload",
        files={"file": ("first.pdf", _pdf_bytes("Alpha document content."), "application/pdf")},
    ).json()
    second = client.post(
        "/upload",
        files={"file": ("second.pdf", _pdf_bytes("Beta document content."), "application/pdf")},
    ).json()

    filtered = retrieve_chunks("content", document_ids=[second["document_id"]])
    selected = retrieve_chunks("content", document_ids=[first["document_id"], second["document_id"]])

    assert filtered
    assert {chunk["metadata"]["document_id"] for chunk in filtered} == {second["document_id"]}
    assert {chunk["metadata"]["document_id"] for chunk in selected} == {
        first["document_id"], second["document_id"]
    }


def test_ask_validates_request_and_document_selection(monkeypatch):
    monkeypatch.setattr("app.api.upload.generate_embeddings", _fake_embeddings)
    client = TestClient(app)
    assert client.post("/ask", json={"question": "   "}).status_code == 422
    assert client.post("/ask", json={"question": "test", "top_k": 0}).status_code == 422
    assert client.post("/ask", json={"question": "test"}).status_code == 404
    client.post(
        "/upload",
        files={"file": ("sample.pdf", _pdf_bytes("Indexed sample."), "application/pdf")},
    )
    invalid_selection = client.post("/ask", json={"question": "test", "document_id": "not-indexed"})
    assert invalid_selection.status_code == 404


def test_prompt_context_and_source_formatting_are_bounded_and_grounded():
    chunks = [{
        "text": "abcdefghij",
        "metadata": {"document_id": "doc-1", "document_name": "guide.pdf", "page": 3},
        "distance": 0.1,
    }]
    context = build_context(chunks, max_characters=50)
    prompt = build_user_prompt("What does it say?", context.text)

    assert "ONLY the supplied document context" in SYSTEM_PROMPT
    assert "guide.pdf" in context.text
    assert "Question: What does it say?" in prompt
    assert format_sources(context.chunks) == [{
        "document_id": "doc-1", "filename": "guide.pdf", "page_number": 3, "excerpt": "abcdefghij"
    }]
    with pytest.raises(NoContextError):
        build_context([])
