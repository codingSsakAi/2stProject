from .pinecone_client import get_index
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
index = get_index()

def rag_search(query, insurer=None, top_k=5):
    q_vec = model.encode([query])[0].tolist()
    res = index.query(vector=q_vec, top_k=top_k, include_metadata=True)
    matches = [m for m in res["matches"] if insurer is None or m["metadata"]["insurer"] == insurer]
    return matches
