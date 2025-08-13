import os
import re
import unicodedata
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(), override=True)

# ────────────────────────────────────────────────────────────────────────────────
# 임베딩 어댑터
# ────────────────────────────────────────────────────────────────────────────────
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

# ────────────────────────────────────────────────────────────────────────────────
# Pinecone
# ────────────────────────────────────────────────────────────────────────────────
from pinecone import Pinecone

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY") or ""
INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "insurance-clauses-second")
NAMESPACE = os.getenv("NAMESPACE") or None

if not PINECONE_API_KEY:
    raise RuntimeError("PINECONE_API_KEY가 비어 있습니다.")
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(INDEX_NAME)

# (선택) 재랭커: 점수는 rerank_score에만 반영하고, 클라이언트 노출 score는 Pinecone 점수 유지
USE_RERANKER = os.getenv("USE_RERANKER", "0") == "1"
RERANKER_MODEL = os.getenv("RERANKER_MODEL", "jinaai/jina-reranker-v2-base-multilingual")
reranker = None
if USE_RERANKER:
    try:
        from sentence_transformers import CrossEncoder
        reranker = CrossEncoder(RERANKER_MODEL)
    except Exception:
        reranker = None

# ────────────────────────────────────────────────────────────────────────────────
# 경량 텍스트 정리(과하지 않게)
# ────────────────────────────────────────────────────────────────────────────────
def _normalize(s: str) -> str:
    s = unicodedata.normalize("NFC", s or "")
    s = re.sub(r"\s+", " ", s).strip()
    return s

# "무 면 허" / "뺑 소 니" 같은 2~3글자 쪼개짐만 붙여주기
def _join_short_chopped_hangul(s: str) -> str:
    def _join_once(txt: str, n: int) -> str:
        pattern = r"(?:\b[가-힣]\b(?:\s+\b[가-힣]\b){" + str(n-1) + r"})"
        def repl(m): return re.sub(r"\s+", "", m.group(0))
        return re.sub(pattern, repl, txt)
    s = _join_once(s, 3)
    s = _join_once(s, 2)
    return s

# 인접한 동일 단어(2글자 이상 한/영)만 1회로 축소
def _collapse_adjacent_word_dups(s: str) -> str:
    return re.sub(r"\b([가-힣A-Za-z]{2,})\b(?:\s+\1\b)+", r"\1", s)

def _clean_for_display(s: str) -> str:
    if not s:
        return s
    s = _join_short_chopped_hangul(s)
    s = _collapse_adjacent_word_dups(s)
    s = re.sub(r"\s{2,}", " ", s).strip()
    return s

# 너무 짧은/노이즈성 청크만 컷 (보수적)
def _is_noise(text: str) -> bool:
    if not text:
        return True
    t = text.strip()
    if len(t) < 20:
        return True
    toks = t.split()
    if not toks:
        return True
    # 한글 단글자 토큰 비중이 과도하게 크면 컷
    single_ko = sum(1 for w in toks if len(w) == 1 and re.match(r"[가-힣]", w))
    if len(toks) >= 10 and (single_ko / len(toks) > 0.40):
        return True
    return False

# ────────────────────────────────────────────────────────────────────────────────
# 검색 (키워드 게이트/가점 없음 = 순수 RAG)
# ────────────────────────────────────────────────────────────────────────────────
def retrieve(
    query: str,
    top_k: int = 10,
    candidate_k: int = 40,
    company: Optional[str] = None,
    filters: Optional[Dict[str, Any]] = None,
    min_score: float = 0.0
) -> List[Dict[str, Any]]:
    """
    - 임베딩 기반 최근접 검색만 사용 (키워드 게이트/가점 제거)
    - 필요 시 CrossEncoder로 rerank_score만 계산 (score는 Pinecone 점수 그대로 유지)
    """
    q = _normalize(query)
    q_emb = embedder.encode_one(Q_PREFIX + q)

    pine_filter = {}
    if company:
        pine_filter["company"] = {"$eq": company}
    if isinstance(filters, dict):
        pine_filter.update(filters)
    if not pine_filter:
        pine_filter = None

    res = index.query(
        vector=q_emb,
        top_k=max(candidate_k, top_k),
        include_metadata=True,
        filter=pine_filter,
        namespace=NAMESPACE
    )

    prelim: List[Dict[str, Any]] = []
    for m in res.get("matches", []):
        meta = m.get("metadata", {}) or {}
        raw = meta.get("text") or meta.get("chunk") or ""
        if _is_noise(raw):
            continue
        cleaned = _clean_for_display(raw)
        prelim.append({
            "score": float(m.get("score", 0.0)),  # 그대로 노출
            "text": cleaned,
            "company": meta.get("company", ""),
            "file": meta.get("file", ""),
            "page": meta.get("page", ""),
            "chunk_idx": meta.get("chunk_idx", ""),
            "id": m.get("id")
        })

    if min_score > 0:
        prelim = [r for r in prelim if r["score"] >= min_score]

    if not prelim:
        return []

    # (선택) CrossEncoder 재랭크: rerank_score만 부여, 최종 선택은 rerank_score 우선
    final = prelim
    if reranker and len(prelim) > top_k:
        try:
            ce_scores = reranker.predict([(q, r["text"]) for r in prelim]).tolist()
        except Exception:
            ce_scores = [0.0] * len(prelim)

        # 배치 내 min-max 정규화 (0~1). score에는 손대지 않음.
        mn, mx = float(min(ce_scores)), float(max(ce_scores))
        span = (mx - mn) if (mx > mn) else 1.0
        for r, s in zip(prelim, ce_scores):
            r["rerank_score"] = (float(s) - mn) / span

        final = sorted(prelim, key=lambda x: x.get("rerank_score", 0.0), reverse=True)[:top_k]
    else:
        # reranker 미사용: pinecone score로 컷
        final = sorted(prelim, key=lambda x: x["score"], reverse=True)[:top_k]

    return final

# 뷰에서 쓰는 래퍼
def retrieve_insurance_clauses(
    query: str,
    top_k: int = 10,
    company: Optional[str] = None,
    candidate_k: int = 40,
    filters: Optional[Dict[str, Any]] = None,
    min_score: float = 0.0
) -> List[Dict[str, Any]]:
    return retrieve(
        query=query,
        top_k=top_k,
        candidate_k=candidate_k,
        company=company,
        filters=filters,
        min_score=min_score
    )
