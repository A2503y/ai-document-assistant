from ..models.chunk import Chunk
from .embedding_service import get_embedding_model


def generate_embedding(chunk: Chunk) -> list[float]:
    return get_embedding_model().encode(chunk.text).tolist()


def generate_embeddings(chunks: list[Chunk]) -> list[Chunk]:
    for chunk in chunks:
        chunk.embedding = generate_embedding(chunk)
    return chunks
