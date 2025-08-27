# C:\Users\Admin\Desktop\insurance_project\insurance_app\pinecone_client.py
from __future__ import annotations
import os
from typing import Any

try:
    from django.conf import settings
except Exception:
    class _S:
        USE_MOCK_API = True
        PINECONE_API_KEY = None
        PINECONE_ENV = None
    settings = _S()  # type: ignore

def _get_env(name: str, default: str | None = None) -> str | None:
    v = getattr(settings, name, None)
    if v:
        return v
    return os.getenv(name, default)

PINECONE_API_KEY = _get_env("PINECONE_API_KEY")
PINECONE_ENV     = _get_env("PINECONE_ENV")
USE_MOCK_API     = bool(getattr(settings, "USE_MOCK_API", False))

class MockIndex:
    def __init__(self, name: str = "mock-index"):
        self.name = name
    def upsert(self, vectors: Any = None, **kwargs) -> dict:
        return {"upserted_count": len(vectors or [])}
    def query(self, vector: Any = None, top_k: int = 5, **kwargs) -> dict:
        return {"matches": [], "top_k": top_k}
    def describe_index_stats(self, **kwargs) -> dict:
        return {"dimension": 1536, "namespaces": {}}

_pc = None  # lazy cache

def _ensure_client():
    global _pc
    if _pc is not None:
        return _pc
    if USE_MOCK_API or not PINECONE_API_KEY:
        _pc = None
        return None
    try:
        from pinecone import Pinecone  # >=3
        _pc = Pinecone(api_key=PINECONE_API_KEY)
        return _pc
    except Exception:
        try:
            import pinecone  # legacy
            pinecone.init(api_key=PINECONE_API_KEY, environment=PINECONE_ENV or "us-east-1-aws")
            _pc = pinecone
            return _pc
        except Exception:
            _pc = None
            return None

def get_index(index_name: str = "clauses"):
    client = _ensure_client()
    if client is None:
        return MockIndex(index_name)

    try:
        from pinecone import Pinecone  # type: ignore
        if isinstance(client, Pinecone):
            return client.Index(index_name)
    except Exception:
        pass

    try:
        import pinecone  # type: ignore
        if client is pinecone:
            return pinecone.Index(index_name)
    except Exception:
        pass

    return MockIndex(index_name)
