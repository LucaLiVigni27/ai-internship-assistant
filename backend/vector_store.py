import chromadb
from chromadb.utils import embedding_functions
from backend.chunking import Chunk, build_chunks_for_document, build_chunks_for_job_posting

CHROMA_PERSIST_DIR = "chroma_db"
COLLECTION_NAME = "internship_assistant"

_client = None
_collection = None

def get_collection():
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        _collection = _client.get_or_create_collection(name=COLLECTION_NAME, embedding_function=embedding_fn) # type: ignore[arg-type]
    return _collection

def index_chunks(chunks: list[Chunk], source_type:str, source_id: int) -> dict:
    """
    Sync Chroma's stored chunks for one source to exactly match 'chunks'. Only adds what's missing and removes what's stale, while unchanged chunks are left untouched.
    """
    collection = get_collection()

    existing = collection.get(where={"$and": [{"source_type": source_type}, {"source_id": source_id}]})
    existing_ids = set(existing["ids"])
    desired_ids = {c.chunk_id for c in chunks}

    ids_to_add = desired_ids - existing_ids
    ids_to_remove = existing_ids - desired_ids

    if ids_to_remove:
        collection.delete(ids=list(ids_to_remove))

    chunks_to_add = [c for c in chunks if c.chunk_id in ids_to_add]
    if chunks_to_add:
        collection.add(
            ids=[c.chunk_id for c in chunks_to_add],
            documents=[c.text for c in chunks_to_add],
            metadatas=[c.metadata for c in chunks_to_add],
        )

    return {
        "added": len(chunks_to_add),
        "removed": len(ids_to_remove),
        "unchanged": len(existing_ids & desired_ids),
    }

def index_document(document) -> dict:
    chunks = build_chunks_for_document(document)
    return index_chunks(chunks, source_type="document", source_id=document.id)

def index_job_posting(job_posting) -> dict:
    chunks = build_chunks_for_job_posting(job_posting)
    return index_chunks(chunks, source_type="job_posting", source_id=job_posting.id)

def search_vector(query: str, top_k: int = 5, source_type: str | None = None) -> list[dict]:
    collection = get_collection()

    where_filter = {"source_type": source_type} if source_type is not None else None
    results = collection.query(query_texts=[query], n_results=top_k, where=where_filter) # type: ignore[arg-type]

    ids = results.get("ids")
    documents = results.get("documents")
    metadatas = results.get("metadatas")
    distances = results.get("distances")

    if not ids or not documents or not metadatas or not distances:
        return []

    return [
        {
            "chunk_id": ids[0][i],
            "text": documents[0][i],
            "source_type": metadatas[0][i].get("source_type"),
            "source_id": metadatas[0][i].get("source_id"),
            "score": distances[0][i]
        }
        for i in range(len(ids[0]))
    ]