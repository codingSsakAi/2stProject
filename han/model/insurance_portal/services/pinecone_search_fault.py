# -*- coding: utf-8 -*-
from typing import List, Dict, Any, Optional
from django.conf import settings
from pinecone import Pinecone
import requests, os

# ---- 설정값 ----
PINECONE_API_KEY = getattr(settings, "PINECONE_API_KEY_MY", os.getenv("PINECONE_API_KEY_MY"))
PINECONE_INDEX   = getattr(settings, "FAULT_INDEX_NAME", os.getenv("FAULT_INDEX_NAME"))

UPSTAGE_API_KEY     = getattr(settings, "UPSTAGE_API_KEY", os.getenv("UPSTAGE_API_KEY"))
UPSTAGE_EMBED_URL   = getattr(settings, "UPSTAGE_EMBED_URL", os.getenv("UPSTAGE_EMBED_URL"))
UPSTAGE_EMBED_MODEL = getattr(settings, "UPSTAGE_EMBED_MODEL", os.getenv("UPSTAGE_EMBED_MODEL", "solar-embedding-1-large"))

_pinecone_index = None

def _ensure_index():
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
    if not UPSTAGE_API_KEY:
        raise RuntimeError("UPSTAGE_API_KEY 설정이 없습니다.")

    base = _normalize_model(UPSTAGE_EMBED_MODEL)
    model_candidates = [
        base,
        f"{base}-query",
        f"{base}-passage",
        "embedding-query",
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
        text_or_table = meta.get("table_md") or meta.get("text") or meta.get("chunk") or ""
        matches.append({
            "score": m.get("score", 0.0),
            "type": meta.get("type", ""),
            "id":   meta.get("id", ""),
            "chapter": meta.get("chapter", ""),
            "topic": meta.get("topic", []),
            "text": text_or_table,            # 표면 table_md가 우선
            "table_md": meta.get("table_md"),
            "table_json": meta.get("table_json"),
            "file": meta.get("source", meta.get("file", "")),
            "page": meta.get("page_hint", meta.get("page", "")),
            "chunk_idx": meta.get("chunk_idx", ""),
        })
    return matches

# === 서비스 레이어용 alias: 표 우선 포맷/프롬프트 조립에서 일관되게 쓰기 위함 ===
def retrieve_fault_sources(query: str, top_k: int = 7) -> List[Dict[str, Any]]:
    """
    서비스 레이어(fault_answerer.py)에서 호출하는 기본 검색 함수.
    반환 형식은 retrieve_fault_ratio와 동일.
    """
    return retrieve_fault_ratio(query=query, top_k=top_k)
