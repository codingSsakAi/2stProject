# -*- coding: utf-8 -*-
import re
from typing import Optional

# 한국어 종결 패턴 우선 (다., 요., …) → 일반 부호
_SENTENCE_END_PATTERNS = [
    r"다\.", r"요\.", r"임\.", r"음\.", r"함\.", r"됨\.",
    r"[.!?]"  # 최후의 보루
]

def _clean_ws(s: str) -> str:
    s = (s or "").strip()
    return re.sub(r"\s+", " ", s)

def first_sentence_ko(text: Optional[str], max_len: int = 160) -> str:
    """
    한국어 문장 1개를 '종결형+마침표'까지 포함해 안전하게 추출.
    이전 버그(다. 직전까지 잘려 '말한', '있'로 끝남) 방지.
    """
    t = _clean_ws(text)
    if not t:
        return ""

    ends = []
    for pat in _SENTENCE_END_PATTERNS:
        m = re.search(pat, t)
        if m:
            ends.append(m.end())  # 종결부호 포함
    if ends:
        s = t[:min(ends)]
    else:
        s = t

    if max_len and len(s) > max_len:
        s = s[:max_len].rstrip()
        if not re.search(r"[.!?…]$", s):
            s += "…"
    return s

def looks_truncated_ko(s: str) -> bool:
    """
    '말한', '있' 등 종결 없이 끊긴 흔적 탐지.
    종결부호가 없거나 흔한 어미 직전에서 멈춘 경우 True.
    """
    s = _clean_ws(s)
    if not s:
        return False
    # 종결부호로 끝나면 정상
    if re.search(r"[.!?…]$", s):
        return False
    # 흔한 끊김 어미
    if re.search(r"(있|한|된|함|됨|임|음|및|등|때|것|말한)$", s):
        return True
    # 한글로 끝나고 길면 끊긴 것으로 간주
    if re.search(r"[가-힣]$", s) and len(s) >= 8:
        return True
    return False
