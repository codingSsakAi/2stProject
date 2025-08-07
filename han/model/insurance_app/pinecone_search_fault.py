from django.conf import settings
from pinecone import Pinecone
import requests

PINECONE_API_KEY_MY = settings.PINECONE_API_KEY_MY
UPSTAGE_API_KEY = settings.UPSTAGE_API_KEY
INDEX_NAME = "solar-embedding-index"

pc = Pinecone(api_key=PINECONE_API_KEY_MY)
index = pc.Index(INDEX_NAME)

def upstage_query_embedding(text):
    url = "https://api.upstage.ai/v1/solar/embeddings"
    headers = {
        "Authorization": f"Bearer {UPSTAGE_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "embedding-query",
        "input": [text]
    }
    resp = requests.post(url, headers=headers, json=payload)
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]

def retrieve_fault_ratio(query, top_k=10):
    query_emb = upstage_query_embedding(query)
    result = index.query(
        vector=query_emb,
        top_k=top_k,
        include_metadata=True,
    )
    matches = []
    for m in result.get("matches", []):
        meta = m.get("metadata", {})
        matches.append({
            "score": m.get("score", 0),
            "chunk": meta.get("text", ""),
            "file": meta.get("file", ""),
            "page": meta.get("page", ""),
            "chunk_idx": meta.get("chunk_idx", ""),
            "text": meta.get("text", ""),
        })
    return matches