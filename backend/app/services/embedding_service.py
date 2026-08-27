from functools import lru_cache

@lru_cache
def get_embedding_model():
    """Load the embedding model only when embeddings are actually required."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer("all-MiniLM-L6-v2")
