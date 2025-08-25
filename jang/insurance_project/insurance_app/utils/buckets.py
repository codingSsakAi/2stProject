# -*- coding: utf-8 -*-
# insurance_app/utils/buckets.py

from typing import Any, Dict

# 웹 드롭다운에 노출될 3개 카테고리(버킷) 고정
BUCKETS = [
    "보험용어",
    "과실비율/용어해설",
    "과실비율/FAQ",
]

def _get(obj: Any, attr: str, default: str = "") -> str:
    try:
        v = getattr(obj, attr)
    except Exception:
        v = obj.get(attr) if isinstance(obj, dict) else None
    if v is None:
        return default
    return str(v).strip()

def infer_bucket(term_obj: Any) -> str:
    """
    DB 모델(GlossaryTerm) 인스턴스 or dict 를 받아
    카테고리를 3개 버킷 중 하나로 **강제 매핑**합니다.
    규칙:
      - slug 가 'faq-' 로 시작하거나, category/meta.source 에 'FAQ' 가 포함 → '과실비율/FAQ'
      - slug 가 'nhi-' 로 시작하거나, category/meta.source 에 '용어해설' 포함 → '과실비율/용어해설'
      - 그 외 전부 → '보험용어'
    """
    cat = _get(term_obj, "category").lower()
    slug = _get(term_obj, "slug").lower()

    # meta.source 검사 (dict/JSONField 모두 대응)
    meta = getattr(term_obj, "meta", None)
    if meta is None and isinstance(term_obj, dict):
        meta = term_obj.get("meta")
    source = ""
    if isinstance(meta, dict):
        source = str(meta.get("source", "")).lower()

    if slug.startswith("faq-") or "faq" in cat or "faq" in source:
        return BUCKETS[2]  # 과실비율/FAQ
    if slug.startswith("nhi-") or ("용어해설" in _get(term_obj, "category")) or ("용어해설" in (meta or {}).get("source", "")):
        return BUCKETS[1]  # 과실비율/용어해설
    return BUCKETS[0]      # 보험용어
