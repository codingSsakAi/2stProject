import os
import re
import unicodedata
import difflib
from typing import List, Dict, Optional, Any

# -----------------------
# .env
# -----------------------
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(), override=True)

USE_BACKEND = (os.getenv("EMBED_BACKEND", "st") or "st").lower()   # "st" | "openai"
EMBED_MODEL = os.getenv("EMBED_MODEL", "intfloat/multilingual-e5-large")
INDEX_NAME  = os.getenv("PINECONE_INDEX_NAME", "")
NAMESPACE   = os.getenv("NAMESPACE") or None
INDEX_DIM   = int(os.getenv("INDEX_DIM", "1024"))  # Pinecone 인덱스 차원 (검증용)

# e5 시리즈 차원별 권장 모델 맵
E5_DIM_TO_MODEL = {
    1024: "intfloat/multilingual-e5-large",
    768:  "intfloat/multilingual-e5-base",
    384:  "intfloat/multilingual-e5-small",  # 필요시
}

def _is_e5(name: str) -> bool:
    return "e5" in (name or "").lower()

DOC_PREFIX = "passage: " if (USE_BACKEND == "st" and _is_e5(EMBED_MODEL)) else ""
Q_PREFIX   = "query: "   if (USE_BACKEND == "st" and _is_e5(EMBED_MODEL)) else ""

# -----------------------
# 임베딩 로더
# -----------------------
class Embedder:
    """
    - sentence-transformers: 모델 로드 실패 시 안전 폴백.
    - e5 시리즈인 경우 INDEX_DIM과 불일치하면 자동으로 dim에 맞는 모델로 교체.
    - OpenAI: 그대로 사용(차원은 호출 결과로 확인).
    """
    def __init__(self, backend: str, model_name: str, target_dim: int):
        self.backend = backend
        self.model_name = model_name
        self.dim: Optional[int] = None

        if backend == "openai":
            from openai import OpenAI
            self.client = OpenAI()
        else:
            from sentence_transformers import SentenceTransformer
            # 1) 일단 시도
            try:
                self.model = SentenceTransformer(model_name)
            except Exception as e:
                # 잘못된 ID 등 → e5-large로 기본 폴백
                fallback = E5_DIM_TO_MODEL.get(target_dim, "intfloat/multilingual-e5-large")
                print(f"[WARN] Failed to load '{model_name}': {e}\n"
                      f"       Falling back to '{fallback}'.")
                self.model = SentenceTransformer(fallback)
                self.model_name = fallback

            # 2) 현재 모델 차원
            try:
                self.dim = self.model.get_sentence_embedding_dimension()
            except Exception:
                self.dim = len(self.model.encode(["dim_probe"], show_progress_bar=False)[0])

            # 3) e5 시리즈이고 차원이 다르면, 타깃 차원에 맞는 모델로 자동 교체
            if _is_e5(self.model_name) and self.dim != target_dim:
                wanted = E5_DIM_TO_MODEL.get(target_dim)
                if wanted and wanted != self.model_name:
                    try:
                        print(f"[INFO] Auto-switch model to match index dim: {self.model_name}({self.dim}) → {wanted}({target_dim})")
                        self.model = SentenceTransformer(wanted)
                        self.model_name = wanted
                        self.dim = self.model.get_sentence_embedding_dimension()
                    except Exception as e:
                        raise RuntimeError(
                            f"임베딩 모델을 인덱스 차원({target_dim})에 맞게 로드하지 못했습니다: {e}"
                        )

    def encode_one(self, text: str) -> List[float]:
        if self.backend == "openai":
            resp = self.client.embeddings.create(model=self.model_name, input=[text])
            return resp.data[0].embedding
        else:
            return self.model.encode([text], show_progress_bar=False)[0].tolist()

embedder = Embedder(USE_BACKEND, EMBED_MODEL, INDEX_DIM)

# -----------------------
# Pinecone
# -----------------------
from pinecone import Pinecone
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY") or ""
if not PINECONE_API_KEY:
    raise RuntimeError("PINECONE_API_KEY가 비어 있습니다.")
if not INDEX_NAME:
    raise RuntimeError("PINECONE_INDEX_NAME(.env)이 비어 있습니다.")

pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(INDEX_NAME)

# -----------------------
# (선택) 재랭커
# -----------------------
USE_RERANKER = os.getenv("USE_RERANKER", "0") == "1"
reranker = None
if USE_RERANKER:
    try:
        from sentence_transformers import CrossEncoder
        RERANKER_MODEL = os.getenv("RERANKER_MODEL", "jinaai/jina-reranker-v2-base-multilingual")
        reranker = CrossEncoder(RERANKER_MODEL)
    except Exception as e:
        print(f"[WARN] Reranker load failed: {e}")
        reranker = None

# -----------------------
# 텍스트 정리(가볍게)
# -----------------------
def _normalize(s: str) -> str:
    s = unicodedata.normalize("NFC", s or "")
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _join_short_chopped_hangul(s: str) -> str:
    def _join_once(txt: str, n: int) -> str:
        pattern = r"(?:\b[가-힣]\b(?:\s+\b[가-힣]\b){" + str(n-1) + r"})"
        def repl(m): return re.sub(r"\s+", "", m.group(0))
        return re.sub(pattern, repl, txt)
    s = _join_once(s, 3)
    s = _join_once(s, 2)
    return s

def _collapse_adjacent_word_dups(s: str) -> str:
    return re.sub(r"\b([가-힣A-Za-z]{2,})\b(?:\s+\1\b)+", r"\1", s)

def _display_clean(s: str) -> str:
    if not s: return s
    s = _join_short_chopped_hangul(s)
    s = _collapse_adjacent_word_dups(s)
    s = re.sub(r"\s{2,}", " ", s).strip()
    return s

def _is_noise(text: str) -> bool:
    if not text: return True
    t = text.strip()
    if len(t) < 25: return True
    toks = t.split()
    if not toks: return True
    single_ko = sum(1 for w in toks if len(w) == 1 and re.match(r"[가-힣]", w))
    if single_ko / len(toks) > 0.30: return True
    return False

# -----------------------
# 검색
# -----------------------
def retrieve(query: str,
             top_k: int = 5,
             candidate_k: int = 20,
             company: Optional[str] = None,
             filters: Optional[Dict[str, Any]] = None,
             min_score: float = 0.0) -> List[Dict[str, Any]]:
    """
    순수 RAG용 조회. 결과는 정리된 텍스트와 메타데이터 포함.
    """
    # 1) 쿼리 임베딩 + 차원 검증
    q_text = Q_PREFIX + _normalize(query)
    q_emb = embedder.encode_one(q_text)
    q_dim = len(q_emb)
    if q_dim != INDEX_DIM:
        raise RuntimeError(
            f"임베딩 차원({q_dim})과 인덱스 차원({INDEX_DIM})이 다릅니다. "
            f"EMBED_MODEL='{getattr(embedder, 'model_name', 'unknown')}' ↔ INDEX_DIM={INDEX_DIM}(.env) 확인 필요"
        )

    # 2) 필터
    pine_filter = {"company": company} if company else None

    # 3) Pinecone 질의
    res = index.query(
        vector=q_emb,
        top_k=max(candidate_k, top_k),
        include_metadata=True,
        filter=pine_filter,
        namespace=NAMESPACE
    )

    # 4) 후처리 / 노이즈 컷
    prelim: List[Dict[str, Any]] = []
    for m in res.get("matches", []) or []:
        meta = m.get("metadata", {}) or {}
        raw = meta.get("text") or meta.get("chunk") or ""
        if _is_noise(raw):
            continue

        cleaned = _display_clean(raw)
        prelim.append({
            "score": float(m.get("score", 0.0)),
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

    # 5) (선택) 재랭크
    final = prelim
    if reranker and len(prelim) > top_k:
        try:
            ce_scores = reranker.predict([(query, r["text"]) for r in prelim]).tolist()
        except Exception:
            ce_scores = [0.0] * len(prelim)
        for r, s in zip(prelim, ce_scores):
            r["rerank_score"] = float(s) + float(r["score"])
        final = sorted(prelim, key=lambda x: x.get("rerank_score", x["score"]), reverse=True)[:top_k]
    else:
        final = sorted(prelim, key=lambda x: x["score"], reverse=True)[:top_k]

    return final

def retrieve_insurance_clauses(query: str,
                               top_k: int = 5,
                               company: Optional[str] = None,
                               candidate_k: int = 20,
                               filters: Optional[Dict[str, Any]] = None,
                               min_score: float = 0.0) -> List[Dict[str, Any]]:
    return retrieve(query, top_k=top_k, candidate_k=candidate_k,
                    company=company, filters=filters, min_score=min_score)
