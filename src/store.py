from pathlib import Path
from typing import Iterable
import chromadb
from sentence_transformers import SentenceTransformer
from .config import CHROMA_DIR, EMBEDDING_MODEL, EMBED_BATCH_SIZE, TOP_K

_COLLECTION = "documents"
_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
_collection = None
_encoder = None


def _get_encoder():
    global _encoder
    if _encoder is None:
        _encoder = SentenceTransformer(EMBEDDING_MODEL)
    return _encoder


def _get_collection():
    global _collection
    if _collection is None:
        _collection = _client.get_or_create_collection(
            name=_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def reset_index() -> None:
    global _collection
    try:
        _client.delete_collection(_COLLECTION)
    except Exception:
        pass
    _collection = _client.get_or_create_collection(
        name=_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )


def add_records(records: list[dict]) -> int:
    if not records:
        return 0
    collection = _get_collection()
    encoder = _get_encoder()
    texts = [r["text"] for r in records]
    for start in range(0, len(records), EMBED_BATCH_SIZE):
        batch = records[start:start + EMBED_BATCH_SIZE]
        batch_texts = texts[start:start + EMBED_BATCH_SIZE]
        vectors = encoder.encode(batch_texts, batch_size=EMBED_BATCH_SIZE, normalize_embeddings=True, show_progress_bar=False).tolist()
        collection.add(
            ids=[r["id"] for r in batch],
            documents=batch_texts,
            embeddings=vectors,
            metadatas=[r["metadata"] for r in batch],
        )
    return len(records)


def retrieve(query: str, top_k: int = TOP_K) -> list[dict]:
    collection = _get_collection()
    if collection.count() == 0:
        return []
    encoder = _get_encoder()
    vector = encoder.encode([query], normalize_embeddings=True, show_progress_bar=False)[0].tolist()
    result = collection.query(query_embeddings=[vector], n_results=min(top_k, collection.count()))
    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]
    evidence = []
    for text, metadata, distance in zip(documents, metadatas, distances):
        evidence.append({
            "text": text,
            "source": metadata.get("source", "unknown"),
            "page": metadata.get("page"),
            "distance": float(distance),
        })
    return evidence
