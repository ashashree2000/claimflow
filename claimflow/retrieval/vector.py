"""Vector retrieval: Gemini embeddings stored in a persistent local Chroma collection."""
from __future__ import annotations

from .. import config
from ..llm import LLMClient
from .documents import Clause, load_policies, load_sops

POLICY_COLLECTION = "policy_clauses"
SOP_COLLECTION = "sop_sections"


def _client():
    import chromadb  # imported lazily so tests and the offline app do not need it

    return chromadb.PersistentClient(path=str(config.CHROMA_DIR))


def build_index(llm: LLMClient) -> dict:
    """(Re)build both collections. Embeddings come through the LLM cache, so a rebuild costs no API calls."""
    client = _client()
    counts = {}
    for name, clauses in ((POLICY_COLLECTION, load_policies()), (SOP_COLLECTION, load_sops())):
        try:
            client.delete_collection(name)
        except Exception:
            pass
        col = client.create_collection(name, embedding_function=None, metadata={"hnsw:space": "cosine"})
        items = list(clauses.values())
        vecs = llm.embed([c.render() for c in items], agent="index", task_type="RETRIEVAL_DOCUMENT")
        if len(vecs) != len(items) or any(not v for v in vecs):
            raise RuntimeError("embedding count does not match clause count")
        col.add(ids=[c.id for c in items], embeddings=vecs, documents=[c.render() for c in items],
                metadatas=[{"lob": c.lob or "sop", "source": c.source} for c in items])
        counts[name] = col.count()
    return counts


def search(llm: LLMClient, query: str, lob: str | None, k: int = config.TOP_K,
           collection: str = POLICY_COLLECTION, agent: str = "retrieval") -> list[tuple[str, float]]:
    """Return [(clause_id, similarity)] for the top-k clauses, filtered to one line of business."""
    col = _client().get_collection(collection, embedding_function=None)
    if col.count() == 0:
        raise RuntimeError(f"collection {collection} is empty; run scripts/build_index.py")
    qv = llm.embed([query], agent=agent, task_type="RETRIEVAL_QUERY")[0]
    where = {"lob": lob} if lob else None
    res = col.query(query_embeddings=[qv], n_results=k, where=where)
    return [(i, round(1 - d, 4)) for i, d in zip(res["ids"][0], res["distances"][0], strict=True)]


def clauses_by_id(ids: list[str]) -> list[Clause]:
    allc = {**load_policies(), **load_sops()}
    return [allc[i] for i in ids if i in allc]


def index_ready() -> bool:
    try:
        client = _client()
        return all(client.get_collection(n, embedding_function=None).count() > 0
                   for n in (POLICY_COLLECTION, SOP_COLLECTION))
    except Exception:
        return False


def ensure_index(llm: LLMClient) -> bool:
    """Build the index if it is missing. Returns False if it cannot be built (no key and no cached embeddings)."""
    if index_ready():
        return True
    try:
        build_index(llm)
        return True
    except Exception:
        return False
