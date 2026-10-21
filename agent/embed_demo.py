"""
embed_demo.py: first RAG building block for reqcheck-eval.

Embeds a handful of requirements with a local Ollama model, stores the vectors
in Qdrant, then retrieves the closest requirements for plain-English questions.

Prereqs:
  - Ollama running, with `nomic-embed-text` pulled
  - Qdrant listening on localhost:6333
  - pip install ollama qdrant-client
"""
import ollama
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

EMBED_MODEL = "nomic-embed-text"
COLLECTION = "requirements_demo"
QDRANT_URL = "http://localhost:6333"

# A deliberately mixed set: some good, some vague, some that depend on
# another requirement for their meaning (REQ-006 refers to "the standard timeout").
REQUIREMENTS = [
    ("REQ-001", "The system shall allow registered users to log in with an email address and password."),
    ("REQ-002", "The system shall lock an account after five consecutive failed login attempts."),
    ("REQ-003", "A user session shall expire after 15 minutes of inactivity."),
    ("REQ-004", "Search results should be returned quickly."),
    ("REQ-005", "The system shall be user-friendly and intuitive."),
    ("REQ-006", "Exported reports shall use the standard timeout when generation takes too long."),
    ("REQ-007", "The system shall send a confirmation email within 60 seconds of order placement."),
    ("REQ-008", "Administrators shall be able to deactivate user accounts as appropriate."),
    ("REQ-009", "All passwords shall be stored using a salted hash."),
    ("REQ-010", "The system shall handle errors gracefully."),
]

QUERIES = [
    "How long until a user is logged out for inactivity?",
    "What is the standard timeout?",
    "Which requirements have no measurable pass/fail criterion?",
    "How are credentials protected?",
]


def embed(texts, prefix):
    """Embed a list of strings. nomic-embed-text expects a task prefix on each side."""
    resp = ollama.embed(model=EMBED_MODEL, input=[prefix + t for t in texts])
    return resp.embeddings


def main():
    client = QdrantClient(url=QDRANT_URL)

    # 1. Turn every requirement into a vector.
    doc_vectors = embed([text for _, text in REQUIREMENTS], "search_document: ")
    dim = len(doc_vectors[0])

    # 2. Create a fresh collection sized to the model's vector length.
    if client.collection_exists(COLLECTION):
        client.delete_collection(COLLECTION)
    client.create_collection(
        COLLECTION,
        vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
    )

    # 3. Store vectors with the original text as payload.
    client.upsert(
        COLLECTION,
        points=[
            PointStruct(id=i, vector=vec, payload={"req_id": rid, "text": text})
            for i, ((rid, text), vec) in enumerate(zip(REQUIREMENTS, doc_vectors), start=1)
        ],
    )
    print(f"Stored {len(REQUIREMENTS)} requirements ({dim}-dim vectors) in '{COLLECTION}'\n")

    # 4. Search by meaning.
    for q in QUERIES:
        qvec = embed([q], "search_query: ")[0]
        hits = client.query_points(COLLECTION, query=qvec, limit=3).points
        print(f"Q: {q}")
        for h in hits:
            print(f"   {h.score:.3f}  {h.payload['req_id']}  {h.payload['text']}")
        print()


if __name__ == "__main__":
    main()
