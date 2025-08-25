# insurance_app/utils/glossary_tools.py
from __future__ import annotations
import hashlib, re
from typing import Iterable, List, Tuple, Any

_HANGUL_RE = re.compile(r"[가-힣]")

def detect_lang(term: str) -> str:
    return "ko" if _HANGUL_RE.search(term or "") else "en"

def _hash_base36(s: str) -> str:
    n = int(hashlib.md5(s.encode("utf-8")).hexdigest()[:12], 16)
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    if n == 0:
        return "0"
    out = []
    while n:
        n, r = divmod(n, 36)
        out.append(digits[r])
    return "".join(reversed(out))

def slugify_term(term: str, lang: str | None = None, slug_hint: str | None = None) -> str:
    if slug_hint:
        s = str(slug_hint).strip().lower()
        if s:
            return s
    t = (term or "").strip()
    if not t:
        return f"term-{_hash_base36('')}"
    # 영문/숫자는 간단 치환
    basic = re.sub(r"[^a-zA-Z0-9\-]+", "-", t.lower()).strip("-")
    if basic:
        return basic
    lang = lang or detect_lang(t)
    return f"{lang}-{_hash_base36(t)}"

def parse_list_field(val: Any) -> List[str]:
    if val is None:
        return []
    if isinstance(val, list):
        return [str(x).strip() for x in val if str(x).strip()]
    s = str(val).strip()
    if not s:
        return []
    if (s.startswith("[") and s.endswith("]")) or (s.startswith("(") and s.endswith(")")):
        s = s.strip("[]()")
    parts = re.split(r"[;,]", s)
    return [p.strip() for p in parts if p.strip()]

def build_short_def(long_def: str, fallback: str = "") -> str:
    text = (long_def or "").strip() or (fallback or "").strip()
    if len(text) <= 120:
        return text
    cut = text[:120]
    for sep in ["다.", ".", "요.", "임."]:
        pos = cut.rfind(sep)
        if pos >= 60:
            return cut[:pos+len(sep)]
    return cut

def normalize_category(cat: str) -> str:
    s = (cat or "").strip()
    return s or "기타"
