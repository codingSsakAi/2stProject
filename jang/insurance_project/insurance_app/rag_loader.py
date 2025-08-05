from sentence_transformers import SentenceTransformer
from .models import Clause
from .pinecone_client import get_index

model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
index = get_index()

def upload_clauses_to_pinecone():
    clauses = Clause.objects.all()
    embeddings = model.encode([c.text for c in clauses])
    vectors = [
        {"id": str(c.id), "values": emb.tolist(), "metadata": {
            "insurer": c.insurer, "title": c.title,
            "clause_number": c.clause_number, "page": c.page, "pdf_link": c.pdf_link
        }} for c, emb in zip(clauses, embeddings)
    ]
    index.upsert(vectors=vectors)
