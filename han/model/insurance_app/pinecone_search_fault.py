# insurance_app/pinecone_search_fault.py
from django.conf import settings
from pinecone import Pinecone
import requests
from typing import List, Dict, Any, Optional

# ---- 설정값(엔드포인트/모델/인덱스) 가변화 ----
PINECONE_API_KEY = getattr(settings, "PINECONE_API_KEY_MY", None)
UPSTAGE_API_KEY = getattr(settings, "UPSTAGE_API_KEY", None)
PINECONE_INDEX = getattr(settings, "FAULT_INDEX_NAME", "solar-embedding-index")

# Upstage: 환경에 따라 바꿀 수 있게 설정으로 분리
UPSTAGE_EMBED_URL = getattr(
    settings,
    "UPSTAGE_EMBED_URL",
    "https://api.upstage.ai/v1/solar/embeddings"
)
UPSTAGE_EMBED_MODEL = getattr(
    settings,
    "UPSTAGE_EMBED_MODEL",
    "embedding-query"
)

_pc = None
_index = None

def _ensure_clients():
    """지연 초기화: 앱 기동 시점 실패 방지"""
    global _pc, _index
    if not PINECONE_API_KEY:
        raise RuntimeError("PINECONE_API_KEY_MY 미설정")
    if not UPSTAGE_API_KEY:
        raise RuntimeError("UPSTAGE_API_KEY 미설정")

    if _pc is None:
        _pc = Pinecone(api_key=PINECONE_API_KEY)
    if _index is None:
        _index = _pc.Index(PINECONE_INDEX)
    return _index

def upstage_query_embedding(text: str) -> List[float]:
    """Upstage에서 질의 임베딩 생성"""
    if not text or not text.strip():
        raise ValueError("빈 쿼리입니다.")

    headers = {
        "Authorization": f"Bearer {UPSTAGE_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {"model": UPSTAGE_EMBED_MODEL, "input": [text]}
    try:
        resp = requests.post(UPSTAGE_EMBED_URL, headers=headers, json=payload, timeout=(5, 20))
        resp.raise_for_status()
        data = resp.json()
        # 응답 스키마 방어적 파싱
        emb = data.get("data", [{}])[0].get("embedding")
        if not emb:
            raise RuntimeError("Upstage 응답에 embedding이 없습니다.")
        return emb
    except requests.HTTPError as e:
        # 엔드포인트/모델 문제시 빠르게 원인 파악 가능하게
        raise RuntimeError(f"Upstage HTTPError: {e.response.status_code} {e.response.text}") from e
    except requests.RequestException as e:
        raise RuntimeError(f"Upstage 연결 오류: {e}") from e

def retrieve_fault_ratio(query: str, top_k: int = 10, namespace: Optional[str] = None, filters: Optional[Dict[str, Any]] = None):
    """
    과실비율 질의 검색
    - query: 사용자 질문
    - top_k: 상위 결과 개수
    - namespace/filters: Pinecone 고급 검색 옵션(선택)
    """
    index = _ensure_clients()
    vec = upstage_query_embedding(query)

    kwargs = {
        "vector": vec,
        "top_k": max(1, min(int(top_k or 10), 50)),
        "include_metadata": True,
    }
    if namespace:
        kwargs["namespace"] = namespace
    if filters:
        kwargs["filter"] = filters

    result = index.query(**kwargs)
    matches = []
    for m in (result.get("matches") or []):
        meta = m.get("metadata") or {}
        # 항상 text 필드로 통일
        text = meta.get("text") or meta.get("chunk") or ""
        matches.append({
            "score": m.get("score", 0.0),
            "text": text,
            "file": meta.get("file", ""),
            "page": meta.get("page", ""),
            "chunk_idx": meta.get("chunk_idx", ""),
        })
    return matches
