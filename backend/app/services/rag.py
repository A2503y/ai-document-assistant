from dataclasses import dataclass

from ..config import settings
from .llm import generate_grounded_answer
from .retrieval import retrieve_chunks


class NoContextError(ValueError):
    pass


@dataclass(frozen=True)
class ContextBuild:
    text: str
    chunks: list[dict]


def build_context(chunks: list[dict], max_characters: int | None = None) -> ContextBuild:
    """Add retrieved chunks in rank order until a fixed context budget is used."""
    limit = max_characters or settings.max_context_characters
    remaining = limit
    parts: list[str] = []
    included: list[dict] = []

    for index, chunk in enumerate(chunks, start=1):
        text = chunk["text"].strip()
        if not text or remaining <= 0:
            continue
        metadata = chunk["metadata"]
        page = metadata.get("page", -1)
        label = f"[Source {index}: {metadata.get('document_name', 'unknown')} | page {page}]\n"
        allowed_text = text[: max(0, remaining - len(label))]
        if not allowed_text:
            break
        included_chunk = {**chunk, "text": allowed_text}
        parts.append(label + allowed_text)
        included.append(included_chunk)
        remaining -= len(label) + len(allowed_text)

    if not included:
        raise NoContextError("No useful document context was retrieved.")
    return ContextBuild(text="\n\n".join(parts), chunks=included)


def format_sources(chunks: list[dict], excerpt_length: int = 500) -> list[dict]:
    sources = []
    seen = set()
    for chunk in chunks:
        metadata = chunk["metadata"]
        page = metadata.get("page")
        source = {
            "document_id": metadata["document_id"],
            "filename": metadata["document_name"],
            "page_number": page if page is not None and page >= 0 else None,
            "excerpt": chunk["text"][:excerpt_length],
        }
        identity = (source["document_id"], source["page_number"], source["excerpt"])
        if identity not in seen:
            seen.add(identity)
            sources.append(source)
    return sources


def answer_question(question: str, top_k: int, document_ids: list[str] | None = None) -> dict:
    chunks = retrieve_chunks(question, top_k=top_k, document_ids=document_ids)
    context = build_context(chunks)
    return {
        "answer": generate_grounded_answer(question, context.text),
        "sources": format_sources(context.chunks),
    }
