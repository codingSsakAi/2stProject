# insurance_portal/services/pinecone_search_fault.py
from typing import List, Dict, Any, Optional
from django.conf import settings
from pinecone import Pinecone
import requests

# ---- 설정값 ----
PINECONE_API_KEY = getattr(settings, "PINECONE_API_KEY_MY", None)
PINECONE_INDEX   = getattr(settings, "FAULT_INDEX_NAME", None)

UPSTAGE_API_KEY     = getattr(settings, "UPSTAGE_API_KEY", None)
UPSTAGE_EMBED_URL   = getattr(settings, "UPSTAGE_EMBED_URL", None)  # None이면 기본 사용
UPSTAGE_EMBED_MODEL = getattr(settings, "UPSTAGE_EMBED_MODEL", "solar-embedding-1-large")

# ---- 내부 유틸 ----
_pinecone_index = None

def _ensure_index():
    """Pinecone Index 핸들 생성/캐싱"""
    global _pinecone_index
    if _pinecone_index is not None:
        return _pinecone_index
    if not PINECONE_API_KEY:
        raise RuntimeError("PINECONE_API_KEY_MY 설정이 없습니다.")
    if not PINECONE_INDEX:
        raise RuntimeError("FAULT_INDEX_NAME(파인콘 인덱스명) 설정이 없습니다.")
    pc = Pinecone(api_key=PINECONE_API_KEY)
    _pinecone_index = pc.Index(PINECONE_INDEX)
    return _pinecone_index

# ---------- Upstage Embedding ----------

def _normalize_model(name: Optional[str]) -> str:
    """
    기본 모델명을 정규화(접미사 제거/별칭 보정).
    """
    if not name:
        return "solar-embedding-1-large"
    base = name.strip()
    for suf in ("-query", "-passage"):
        if base.endswith(suf):
            base = base[: -len(suf)]
    aliases = {
        "embedding-query": "solar-embedding-1-large",
        "embedding": "solar-embedding-1-large",
        "solar-embedding-1": "solar-embedding-1-large",
        "solar-embedding-large": "solar-embedding-1-large",
    }
    return aliases.get(base, base)

def upstage_embed(text: str) -> List[float]:
    """
    Upstage 임베딩 호출.
    - 모델명 후보: base, base-query, base-passage, (레거시) embedding-query
    - URL 후보: /v1/embeddings → /v1/solar/embeddings
    둘 다 순차 시도하여 첫 성공 결과를 반환.
    """
    if not UPSTAGE_API_KEY:
        raise RuntimeError("UPSTAGE_API_KEY 설정이 없습니다.")

    base = _normalize_model(UPSTAGE_EMBED_MODEL)
    model_candidates = [
        base,
        f"{base}-query",
        f"{base}-passage",
        "embedding-query",      # 일부 SDK/문서 레거시
    ]

    url_candidates = [
        (UPSTAGE_EMBED_URL or "https://api.upstage.ai/v1/embeddings"),
        "https://api.upstage.ai/v1/solar/embeddings",
    ]

    headers = {"Authorization": f"Bearer {UPSTAGE_API_KEY}", "Content-Type": "application/json"}

    errors: List[str] = []
    for url in url_candidates:
        for model in model_candidates:
            try:
                payload = {"model": model, "input": [text]}
                r = requests.post(url, json=payload, headers=headers, timeout=(5, 20))
                if r.ok:
                    data = r.json()
                    vec = (data.get("data") or [{}])[0].get("embedding")
                    if not vec:
                        raise RuntimeError("Upstage 응답에 embedding이 없습니다.")
                    return vec
                # 에러 메시지 기록 후 다음 후보 시도
                try:
                    r.raise_for_status()
                except requests.HTTPError as e:
                    errors.append(f"{url} model={model} -> HTTP {e.response.status_code}: {e.response.text}")
                    continue
            except requests.RequestException as e:
                errors.append(f"{url} model={model} -> 연결 오류: {e}")
                continue

    raise RuntimeError("Upstage 임베딩 실패:\n" + "\n".join(errors))

# ---- 공개 함수 ----
def retrieve_fault_ratio(
    query: str,
    top_k: int = 10,
    namespace: Optional[str] = None,
    filters: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    과실비율 질의 검색
    반환: [{score, text, file, page, chunk_idx}, ...]
    """
    index = _ensure_index()
    vector = upstage_embed(query)

    kwargs: Dict[str, Any] = {
        "vector": vector,
        "top_k": max(1, min(int(top_k or 10), 50)),
        "include_metadata": True,
    }
    if namespace:
        kwargs["namespace"] = namespace
    if filters:
        kwargs["filter"] = filters

    result = index.query(**kwargs)
    matches: List[Dict[str, Any]] = []
    for m in (result.get("matches") or []):
        meta = m.get("metadata") or {}
        text = meta.get("text") or meta.get("chunk") or ""
        matches.append({
            "score": m.get("score", 0.0),
            "text": text,
            "file": meta.get("file", ""),
            "page": meta.get("page", ""),
            "chunk_idx": meta.get("chunk_idx", ""),
        })
    return matches
