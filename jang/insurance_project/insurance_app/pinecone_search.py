# insurance_app/pinecone_search.py

import os
import re
import unicodedata
from typing import List, Dict

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(), override=True)

# -----------------------
# 임베더 어댑터
# -----------------------
USE_BACKEND = os.getenv("EMBED_BACKEND", "st").lower()  # "st" | "openai"
EMBED_MODEL = os.getenv("EMBED_MODEL", "intfloat/multilingual-e5-large")

class Embedder:
    def __init__(self, backend: str, model_name: str):
        self.backend = backend
        self.model_name = model_name
        if backend == "openai":
            from openai import OpenAI
            self.client = OpenAI()
        else:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)

    def encode_one(self, text: str) -> List[float]:
        if self.backend == "openai":
            resp = self.client.embeddings.create(model=self.model_name, input=[text])
            return resp.data[0].embedding
        else:
            return self.model.encode([text], show_progress_bar=False)[0].tolist()

def is_e5(name: str) -> bool:
    return "e5" in name.lower()

DOC_PREFIX = "passage: " if (USE_BACKEND == "st" and is_e5(EMBED_MODEL)) else ""
Q_PREFIX   = "query: "   if (USE_BACKEND == "st" and is_e5(EMBED_MODEL)) else ""

embedder = Embedder(USE_BACKEND, EMBED_MODEL)

# -----------------------
# Pinecone
# -----------------------
from pinecone import Pinecone
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY") or ""
INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "insurance-clauses-new")
NAMESPACE = os.getenv("NAMESPACE") or None
if not PINECONE_API_KEY:
    raise RuntimeError("PINECONE_API_KEY가 비어 있습니다.")

pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(INDEX_NAME)

# -----------------------
# 선택적 재랭커
# -----------------------
USE_RERANKER = os.getenv("USE_RERANKER", "1") == "1"
RERANKER_MODEL = os.getenv("RERANKER_MODEL", "jinaai/jina-reranker-v2-base-multilingual")
reranker = None
if USE_RERANKER:
    try:
        from sentence_transformers import CrossEncoder
        reranker = CrossEncoder(RERANKER_MODEL)
    except Exception:
        reranker = None

# -----------------------
# 유틸/필터
# -----------------------
def normalize(s: str) -> str:
    s = unicodedata.normalize("NFC", s or "")
    s = re.sub(r"\s+", " ", s).strip()
    return s

def is_noise(text: str) -> bool:
    if not text: 
        return True
    t = text.strip()
    if len(t) < 25:
        return True
    toks = t.split()
    if toks:
        single_ko = sum(1 for w in toks if len(w) == 1 and re.match(r"[가-힣]", w))
        if single_ko / len(toks) > 0.30:
            return True
        if (len(set(toks)) / len(toks)) < 0.42:
            return True
    if re.search(r"(\b[\w가-힣]{1,20}\b)(?:\s+\1){2,}", t):  # 반복 어절
        return True
    punct_runs = re.findall(r"(?:[^\w\s가-힣]){3,}", t)
    if len(punct_runs) >= 2:
        return True
    digits = sum(ch.isdigit() for ch in t)
    if digits / len(t) > 0.35 and not re.search(r"[가-힣]{3,}", t):
        return True
    return False

def _looks_spaced_hangul(s: str, thresh: float = 0.28) -> bool:
    toks = s.split()
    if not toks: return False
    single_ko = sum(1 for t in toks if len(t) == 1 and re.match(r"[가-힣]", t))
    return (single_ko / max(len(toks), 1)) >= thresh

def _display_clean(s: str) -> str:
    if not s: return s
    if _looks_spaced_hangul(s, 0.28):
        s = re.sub(r"(?<=[가-힣])\s+(?=[가-힣])", "", s)
    s = re.sub(r"(\b[\w가-힣]{1,20}\b)(?:\s+\1){2,}", r"\1 \1", s)
    s = re.sub(r"(?:[^\w\s가-힣]){3,}", " ", s)
    s = re.sub(r"\s{2,}", " ", s).strip()
    return s

# -----------------------
# 검색
# -----------------------
def retrieve(query: str, top_k: int = 5, candidate_k: int = 20, company: str | None = None, min_score: float = 0.0) -> List[Dict]:
    q_emb = embedder.encode_one(Q_PREFIX + normalize(query))
    filt = {"company": company} if company else None

    res = index.query(
        vector=q_emb,
        top_k=max(candidate_k, top_k),
        include_metadata=True,
        filter=filt,
        namespace=NAMESPACE
    )

    matches = []
    for m in res.get("matches", []):
        meta = m.get("metadata", {}) or {}
        text = meta.get("text") or meta.get("chunk") or ""
        if is_noise(text):
            continue
        matches.append({
            "score": float(m.get("score", 0.0)),
            "text": _display_clean(text),   # 보기용 정리
            "company": meta.get("company", ""),
            "file": meta.get("file", ""),
            "page": meta.get("page", ""),
            "chunk_idx": meta.get("chunk_idx", ""),
            "id": m.get("id")
        })

    if min_score > 0:
        matches = [r for r in matches if r["score"] >= min_score]

    final = matches
    if reranker and len(matches) > top_k:
        pairs = [(query, r["text"]) for r in matches]
        try:
            scores = reranker.predict(pairs).tolist()
            for r, s in zip(matches, scores):
                r["rerank_score"] = float(s)
            final = sorted(matches, key=lambda x: x["rerank_score"], reverse=True)[:top_k]
        except Exception:
            final = matches[:top_k]
    else:
        final = matches[:top_k]
    return final

# 뷰 호환 alias
def retrieve_insurance_clauses(query: str, top_k: int = 5, company: str | None = None, candidate_k: int = 20, min_score: float = 0.0):
    return retrieve(query, top_k=top_k, candidate_k=candidate_k, company=company, min_score=min_score)
