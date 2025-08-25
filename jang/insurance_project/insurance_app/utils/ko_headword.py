# insurance_app/utils/ko_headword.py
from __future__ import annotations
import re, hashlib
from typing import Tuple

# 조사/어미(문장 끝/명사 뒤에 흔히 붙는 꼬리표)
_TRAIL_PARTICLES = (
    "으로써|으로서|으로|로|에서|에게서|에게|께|에|의|은|는|이|가|을|를|과|와|도|만|까지|부터|마다|밖에|나|이나"
)
_TRAIL_ENDINGS = (
    "하는|하며|하여|하였|하였다|한|되는|되어|되었|되었다|된|될|한다|했다|하였다가|하였을|되었을"
)

RE_TAIL = re.compile(rf"({ _TRAIL_PARTICLES })$", re.UNICODE)
RE_ENDINGS = re.compile(rf"({ _TRAIL_ENDINGS })$", re.UNICODE)

# 사전 표제어로 두지 않을 쓰레기 후보
RE_BAD = re.compile(r"^(있다|없다|합니다|됩니다|등|및)$")

# 문제 표현 → 대표 표제어 매핑(직접 지정)
CANON_MAP = {
    # '공제*' 계열은 대표 표제어로 합침
    "공제액": "자기부담금(공제액)",
    "공제한": "자기부담금(공제액)",
    "공제": "자기부담금(공제액)",

    # 피보험자/피보험자동차/기명피보험자 활용형 정리
    "피보험자의": "피보험자", "피보험자를": "피보험자", "피보험자가": "피보험자",
    "피보험자에게": "피보험자", "피보험자는": "피보험자",
    "피보험자동차의": "피보험자동차", "피보험자동차를": "피보험자동차",
    "피보험자동차가": "피보험자동차", "피보험자동차에": "피보험자동차",
    "기명피보험자의": "기명피보험자", "기명피보험자를": "기명피보험자",
    "기명피보험자가": "기명피보험자", "기명피보험자와": "기명피보험자",

    # 기타 자주 튀는 반(半)토막
    "무보험자동차에": "무보험자동차",
    "긴급출동": "긴급출동 특약",
    "손해배상을": "손해배상",
    "손해배상책임을": "손해배상책임",
    "보험계약자가": "보험계약자", "보험계약자는": "보험계약자",
    "보험계약자의": "보험계약자", "보험계약자에게": "보험계약자",
}

def _strip_trailing_particles(s: str) -> str:
    prev = None
    cur = s
    while prev != cur:
        prev = cur
        cur = RE_TAIL.sub("", cur)
    return cur

def _strip_endings(s: str) -> str:
    return RE_ENDINGS.sub("", s)

def normalize_headword(term: str) -> Tuple[str, bool, str]:
    """
    표제어 정규화: 직접 매핑 → 조사/어미 제거 → 불용어/1글자 제거
    return: (대표표제어, 변경여부, 이유)
    """
    if not term:
        return term, False, "empty"
    t = term.strip()

    if t in CANON_MAP:
        return CANON_MAP[t], True, "CANON_MAP"

    base = _strip_trailing_particles(t)
    base2 = _strip_endings(base)

    if base2 in CANON_MAP:
        return CANON_MAP[base2], True, "CANON_MAP(after-strip)"

    if len(base2) <= 1 or RE_BAD.match(base2):
        return base2, True if base2 != t else False, "drop-candidate"

    return base2, (base2 != t), "strip"

def make_slug_from_korean(term: str) -> str:
    base = re.sub(r"[^a-zA-Z0-9\-]+", "-", term.lower()).strip("-")
    if base:
        return base
    h = hashlib.md5(term.encode("utf-8")).hexdigest()[:10]
    return f"ko-{h}"
