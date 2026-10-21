"""Load requirements (text only, never labels) and index them in Qdrant for context retrieval."""
import json

import ollama
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

EMBED_MODEL = "nomic-embed-text"
QDRANT_URL = "http://localhost:6333"


def load_requirements(path):
    """Return [(req_id, text)]. Deliberately ignores the 'labels' field so the agent can't see the answer key."""
    with open(path) as f:
        data = json.load(f)
    return [(r["req_id"], r["text"]) for r in data["requirements"]]


def embed(texts, prefix):
    return ollama.embed(model=EMBED_MODEL, input=[prefix + t for t in texts]).embeddings


def build_index(client, collection, reqs):
    vecs = embed([t for _, t in reqs], "search_document: ")
    if client.collection_exists(collection):
        client.delete_collection(collection)
    client.create_collection(collection, vectors_config=VectorParams(size=len(vecs[0]), distance=Distance.COSINE))
    client.upsert(collection, points=[
        PointStruct(id=i, vector=v, payload={"req_id": rid, "text": t})
        for i, ((rid, t), v) in enumerate(zip(reqs, vecs), start=1)
    ])


def related(client, collection, req_id, text, k):
    """Top-k most similar other requirements. The requirement itself is excluded."""
    qvec = embed([text], "search_query: ")[0]
    hits = client.query_points(collection, query=qvec, limit=k + 1).points
    return [(h.payload["req_id"], h.payload["text"]) for h in hits if h.payload["req_id"] != req_id][:k]
