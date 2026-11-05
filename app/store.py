"""ChromaDB wrapper: one collection holds every chunk of every document."""
import chromadb

from . import config

_client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))
collection = _client.get_or_create_collection("documents", metadata={"hnsw:space": "cosine"})


def list_documents() -> list[dict]:
    metas = collection.get(include=["metadatas"])["metadatas"] or []
    docs: dict[str, dict] = {}
    for m in metas:
        d = docs.setdefault(m["source"], {"name": m["source"], "chunks": 0, "pages": 0})
        d["chunks"] += 1
        d["pages"] = max(d["pages"], m["page"])
    return sorted(docs.values(), key=lambda d: d["name"])


def delete_document(name: str) -> int:
    ids = collection.get(where={"source": name})["ids"]
    if ids:
        collection.delete(ids=ids)
    return len(ids)
