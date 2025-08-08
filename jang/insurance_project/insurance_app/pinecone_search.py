import os
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
import re

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
# 환경변수로 인덱스 이름 관리
INDEX_NAME = os.environ.get("PINECONE_INDEX_NAME", "insurance-clauses-new")
# 업로드와 동일한 모델 사용
EMBED_MODEL = "jhgan/ko-sroberta-multitask"

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

def is_noise(text):
    if not text or len(text.strip()) < 15:
        return True
    if re.search(r'([가-힣])\1{1,}', text):
        return True
    if re.search(r'([a-zA-Z0-9])\1{3,}', text):
        return True
    if re.match(r'^[-=|.]{5,}$', text):
        return True
    return False

def filter_pinecone_results(results, query, min_score=0.55):
    keywords = [kw for kw in re.split(r"[ ,.?]", query) if kw and len(kw) > 1]
    def is_valid(chunk):
        if not chunk or is_noise(chunk):
            return False
        if keywords and not any(kw in chunk for kw in keywords):
            return False
        return True
    # 1. 유사도/노이즈/키워드 포함여부
    filtered = [
        r for r in results
        if r.get("score", 0) >= min_score
        and is_valid(r.get("text") or r.get("chunk") or "")
    ]
    # 2. 보험사별 최고점 하나씩
    best_by_company = {}
    for r in filtered:
        company = r.get("document") or r.get("company") or "기타"
        if company not in best_by_company or r["score"] > best_by_company[company]["score"]:
            best_by_company[company] = r
    return list(best_by_company.values())