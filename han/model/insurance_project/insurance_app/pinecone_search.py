import os
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME = "insurance-clauses"
EMBED_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(INDEX_NAME)
model = SentenceTransformer(EMBED_MODEL)

def retrieve_insurance_clauses(query, top_k=5, company=None):
    query_emb = model.encode(query).tolist()
    filter_dict = {"company": company} if company else None
    result = index.query(
        vector=query_emb,
        top_k=top_k,
        include_metadata=True,
        filter=filter_dict
    )
    matches = []
    for m in result.get("matches", []):
        meta = m.get("metadata", {})
        matches.append({
            "score": m.get("score", 0),
            "chunk": meta.get("text", ""),
            "company": meta.get("company", ""),
            "file": meta.get("file", ""),
            "page": meta.get("page", ""),
            "chunk_idx": meta.get("chunk_idx", ""),
            "text": meta.get("text", ""),
        })
    return matches
