from app.services.embedding_service import get_embedding_model
from app.services.vectordb import get_collection


def retrieve_chunks(
    query: str,
    top_k: int = 5,
    document_id: str | None = None,
    document_ids: list[str] | None = None,
) -> list[dict]:
    """Return nearest chunks from the shared persistent Chroma collection."""
    if not query.strip():
        raise ValueError("Query cannot be empty.")
    if top_k <= 0:
        raise ValueError("top_k must be positive.")
    selected_ids = list(dict.fromkeys(([document_id] if document_id else []) + (document_ids or [])))
    where = None
    if len(selected_ids) == 1:
        where = {"document_id": selected_ids[0]}
    elif selected_ids:
        where = {"document_id": {"$in": selected_ids}}

    results = get_collection().query(
        query_embeddings=[get_embedding_model().encode(query).tolist()],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
        **({"where": where} if where else {}),
    )
    return [
        {"text": document, "metadata": metadata, "distance": distance}
        for document, metadata, distance in zip(
            results["documents"][0], results["metadatas"][0], results["distances"][0]
        )
    ]
