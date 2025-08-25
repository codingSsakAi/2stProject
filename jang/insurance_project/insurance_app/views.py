# insurance_app/views.py
from __future__ import annotations

import os
import re
import json
import unicodedata
import hashlib
import difflib
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.views.decorators.http import require_POST
from django.template import TemplateDoesNotExist

# 인증/계정
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required

# 아카이브 폼/모델/검색/처리기
from .forms import CustomUserCreationForm, EmailPasswordChangeForm
from .models import GlossaryTerm
from django.db.models import Q
from .pdf_processor import EnhancedPDFProcessor
from .pinecone_search import retrieve_insurance_clauses

from insurance_app.utils.buckets import BUCKETS, infer_bucket

# ---------------------------------------------------------------------
# (중요) 아카이브 내 기존 llm_client 재사용: 다양한 함수/클래스 시그니처 자동 탐색
# ---------------------------------------------------------------------
def call_llm_via_project_client(prompt: str) -> str:
    """
    프로젝트에 포함된 llm_client 모듈을 '있는 그대로' 재사용하기 위한 어댑터.
    - 함수형 API 추정: llm_answer_ko / llm_answer / ask / chat / answer / generate / complete ...
    - 클래스형 API 추정: LLMClient/OpenAIClient/Client ... 의 ask/chat/answer 등
    가능한 조합을 순차적으로 시도해 가장 먼저 성공하는 것을 사용.
    실패 시 사용자에게 설정 점검 문구를 반환(서버 500 방지).
    """
    try:
        from . import llm_client as L  # 아카이브의 기존 모듈
    except Exception as e:
        return f"일반 요약/정리 답변 생성 모듈을 불러오지 못했습니다: {e}"

    last_err: Optional[Exception] = None

    # 1) 함수형 API 후보들
    func_names = [
        "llm_answer_ko", "llm_answer", "ask_ko", "ask", "chat", "answer",
        "generate", "complete", "respond", "response"
    ]
    for name in func_names:
        fn = getattr(L, name, None)
        if callable(fn):
            try:
                return fn(prompt)  # 인자 1개
            except TypeError:
                try:
                    return fn(prompt=prompt)  # 키워드 인자
                except Exception as e:
                    last_err = e
            except Exception as e:
                last_err = e

    # 2) 클래스형 API 후보들 (무인자 생성자 가정)
    cls_names = ["LLMClient", "OpenAIClient", "Client"]
    method_names = ["ask_ko", "ask", "chat", "answer", "generate", "complete", "respond"]
    for cls_name in cls_names:
        Cls = getattr(L, cls_name, None)
        if Cls is None:
            continue
        try:
            client = Cls()
        except Exception as e:
            last_err = e
            continue
        for m in method_names:
            meth = getattr(client, m, None)
            if callable(meth):
                try:
                    return meth(prompt)
                except TypeError:
                    try:
                        return meth(prompt=prompt)
                    except Exception as e:
                        last_err = e
                except Exception as e:
                    last_err = e

    # 3) 모두 실패 시
    msg = "일반 요약/정리 답변 생성 중 오류가 발생했습니다. LLM 설정(키/모델) 또는 llm_client API를 확인해주세요."
    if last_err:
        msg += f" 상세: {last_err}"
    return msg

# ────────────────────────────────────────────────────────────────────────────────
# 문서 경로 추정 유틸: 회사/파일.pdf 상대경로 생성
# ────────────────────────────────────────────────────────────────────────────────
DOCS_DIR = Path(__file__).resolve().parent / "documents"

def _norm_key_ko(s: str) -> str:
    t = unicodedata.normalize("NFKC", s or "")
    return re.sub(r"\s+", "", t).lower()

def _guess_pdf_relpath(company: str = "", file_hint: str = "") -> Optional[str]:
    try:
        _ = DOCS_DIR.exists()
    except Exception:
        return None

    # 1) file_hint가 .pdf면 우선 확인
    if file_hint:
        hint = (file_hint or "").strip()
        if hint.lower().endswith(".pdf"):
            p = (DOCS_DIR / hint)
            if p.exists():
                return str(p.relative_to(DOCS_DIR)).replace("\\", "/")
            for d in DOCS_DIR.iterdir():
                if d.is_dir():
                    cand = d / hint
                    if cand.exists():
                        return f"{d.name}/{hint}"

    # 2) 회사 폴더명 일치
    key = _norm_key_ko(company)
    if key:
        for d in DOCS_DIR.iterdir():
            if d.is_dir() and _norm_key_ko(d.name) == key:
                pdfs = list(d.glob("*.pdf"))
                if pdfs:
                    return f"{d.name}/{pdfs[0].name}"

    # 3) 느슨 탐색
    loose = _norm_key_ko(company or file_hint)
    if loose:
        for f in DOCS_DIR.rglob("*.pdf"):
            stem = _norm_key_ko(f.stem)
            if loose in stem:
                try:
                    return str(f.relative_to(DOCS_DIR)).replace("\\", "/")
                except Exception:
                    pass
    return None

# ────────────────────────────────────────────────────────────────────────────────
# 검색 결과 정제/요약(노이즈 차단 강화)
# ────────────────────────────────────────────────────────────────────────────────
def _normalize_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())

def _norm_text_for_key(s: str) -> str:
    return re.sub(r"[^가-힣A-Za-z0-9]+", "", unicodedata.normalize("NFKC", s or "")).lower()

def _make_tuple_key(r: Dict[str, Any]) -> Tuple[str, str, str]:
    return (
        (r.get("company") or r.get("document") or ""),
        (r.get("file") or r.get("path") or r.get("source") or ""),
        str(r.get("page") or "")
    )

def dedup_matches_by_tuple(matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen, out = set(), []
    for r in matches:
        k = _make_tuple_key(r)
        if k in seen: continue
        seen.add(k); out.append(r)
    return out

def fuzzy_dedup_matches(matches: List[Dict[str, Any]], threshold: float = 0.965, window: int = 80) -> List[Dict[str, Any]]:
    out, sigs = [], []
    for r in matches:
        text = _normalize_spaces(r.get("text") or r.get("chunk") or "")
        sig = hashlib.md5((_norm_text_for_key(text)[:window]).encode("utf-8")).hexdigest()
        if any(difflib.SequenceMatcher(None, sig, s).ratio() >= threshold for s in sigs):
            continue
        sigs.append(sig); out.append(r)
    return out

def ensure_not_overpruned(orig: List[Dict[str, Any]], cur: List[Dict[str, Any]], min_ratio: float = 0.35, min_count: int = 5) -> List[Dict[str, Any]]:
    if not cur or len(cur) < max(min_count, int(len(orig) * min_ratio)):
        return orig
    return cur

# ─────────────── 토픽 키워드 (도난 포함)
_DUI_KEYS   = ["음주", "무면허", "약물", "마약", "뺑소니", "사고부담금", "자기부담금", "면책"]
_DISC_KEYS  = ["무사고", "할인", "할인율", "마일리지", "주행거리", "후할인", "정산"]
_FAM_KEYS   = ["가족", "가족운전자", "운전자범위", "한정", "부부", "자녀", "배우자", "형제자매"]
_THEFT_KEYS = ["도난", "절도", "강도", "절취", "도난손해", "차량도난", "무단사용", "침입", "손괴", "파손", "분실"]

# “약관형” 판별용 광의 키워드
_POLICY_HINTS = set(_DUI_KEYS + _DISC_KEYS + _FAM_KEYS + _THEFT_KEYS + [
    "약관","특별약관","보상","담보","면책","대인","대물","자차","자기신체","의무보험","보험금","청구","배상"
])

_RHETORICAL = re.compile(r"(?:\?|있을까요|가능할까요|절약하려면|알아볼까요|해볼까요)")
_MARKETING  = re.compile(r"(?:지금|간편|쉽게|Tip|TIP|유의하세요|참고하세요)")
_GENERIC_ALLOW = re.compile(r"(?:가입\s*가능|가입\s*할\s*수\s*있습니다)")

_NUM_UNIT   = re.compile(r"(?:\d[\d,\.]*)\s*(?:원|만원|억원|%|㎞|km|KM)")
_REP_WORDS  = re.compile(r"(보상|면책|할인율|보험증권|보험가입금액)")
_KO_CHAR    = re.compile(r"[가-힣]")

def _hangul_ratio(s: str) -> float:
    if not s: return 0.0
    total = len(s); ko = len(_KO_CHAR.findall(s))
    return ko / max(1, total)

def _too_many_numbers_or_units(s: str) -> bool:
    return len(_NUM_UNIT.findall(s)) >= 3

def _too_repetitive_terms(s: str) -> bool:
    return len(_REP_WORDS.findall(s)) >= 3

def _looks_like_table_fragment(s: str) -> bool:
    t = re.sub(r"\s+", "", s)
    if re.search(r"[│┤├┬┴┼╋ㅡ─━\|]{3,}", t): return True
    if re.fullmatch(r"[○◯●◎△▲▽▼□■◇◆✕×･·\-\–—\|]+", t): return True
    return False

# ─────────────── 안전한 문장 분리기(lookbehind 미사용)
def split_sentences(text: str) -> List[str]:
    if not text: return []
    t = unicodedata.normalize("NFKC", text)
    t = re.sub(r"([\.!?])\s*", r"\1§", t)                 # 영문 구두점 뒤
    t = re.sub(r"(다|요)(?=[\s\)\]\}\"\']|$)", r"\1§", t)  # 한국어 어말어미 뒤
    parts = [seg.strip() for seg in t.split("§") if seg and seg.strip()]
    return parts

def _strip_list_artifacts(s: str) -> str:
    s = re.sub(r"^[•·●○■□▶▷\-\–\—•∙※▶️➤★☆◇◆]\s*", "", s.strip())
    s = re.sub(r"^\(?[0-9가-힣A-Za-z]+[\.\)]\s*", "", s)
    return s.strip()

def _topic_for_query(q: str) -> str:
    qn = _normalize_spaces(q)
    scores = {"theft":0, "dui":0, "discount":0, "family":0}
    for k in _THEFT_KEYS:
        if k in qn: scores["theft"] += 3
    for k in _DUI_KEYS:
        if k in qn: scores["dui"] += 2
    for k in _DISC_KEYS:
        if k in qn: scores["discount"] += 2
    for k in _FAM_KEYS:
        if k in qn: scores["family"] += 2
    order = ["theft", "dui", "discount", "family"]
    return max(order, key=lambda t: (scores[t], -order.index(t)))

def _topic_match(topic: str, s: str) -> bool:
    if topic == "theft":    return any(k in s for k in _THEFT_KEYS)
    if topic == "dui":      return any(k in s for k in _DUI_KEYS)
    if topic == "discount": return any(k in s for k in _DISC_KEYS)
    if topic == "family":   return any(k in s for k in _FAM_KEYS)
    return True

def _accept_sentence(s: str, topic: str) -> bool:
    sc = s.strip()
    if len(sc) < 12: return False
    if _looks_like_table_fragment(sc): return False
    if _RHETORICAL.search(sc): return False
    if _MARKETING.search(sc): return False
    if _GENERIC_ALLOW.search(sc) and not _topic_match(topic, sc): return False
    # 숫자/단위 과다: 도난 주제에서는 허용 폭 넓힘
    if _too_many_numbers_or_units(sc) and topic != "theft" and not any(k in sc for k in ["사고부담금","자기부담금","면책"]):
        return False
    if _too_repetitive_terms(sc): return False
    if _hangul_ratio(sc) < 0.4: return False
    if not _topic_match(topic, sc): return False
    return True

def clean_and_pick_sentences(question: str, triples: List[Tuple[str, str, str]], max_sent_total: int = 12) -> List[Tuple[str, str, str, str]]:
    topic = _topic_for_query(question)
    picked: List[Tuple[str, str, str, str]] = []
    for company, page, text in triples:
        for s in split_sentences(text):
            s = _strip_list_artifacts(s)
            if _accept_sentence(s, topic):
                picked.append((company, page, text, s))
                if len(picked) >= max_sent_total:
                    return picked
    if not picked:
        for company, page, text in triples:
            for s in split_sentences(text):
                s = _strip_list_artifacts(s)
                if len(s) >= 8 and not _looks_like_table_fragment(s):
                    picked.append((company, page, text, s))
                    if len(picked) >= max_sent_total:
                        return picked
    return picked

def to_bullet_style(q: str, sentences: List[str], max_bullets: int) -> List[str]:
    topic = _topic_for_query(q)
    q_terms = [t for t in re.split(r"\s+", _normalize_spaces(q)) if len(t) >= 2]
    out, seen = [], set()
    for s in sentences:
        s = _strip_list_artifacts(s)
        if not _accept_sentence(s, topic): continue
        key = _norm_text_for_key(s)
        if key in seen: continue
        seen.add(key)
        if q_terms and not any(t in s for t in q_terms):
            if len(out) >= max_bullets - 1: continue
        out.append(s)
        if len(out) >= max_bullets: break
    return out

def _as_page_int(val) -> Optional[int]:
    try:
        f = float(val); i = int(f); return i
    except Exception:
        return None

def build_answer(question: str, matches: List[Dict[str, Any]], max_refs: int = 5, answer_mode: str = "normal") -> Dict[str, Any]:
    if not matches:
        return {
            "answer": f"질문: {question}\n\n관련 약관을 찾지 못했습니다. 핵심 키워드(예: 면책, 음주, 도난 등)를 포함해 다시 질문해 주세요.",
            "references": [], "results": []
        }

    triples = []
    for r in matches:
        company = r.get("company") or r.get("document") or "보험사"
        page_val = r.get("page")
        page = _as_page_int(page_val)
        page_str = str(page if page is not None else (page_val or ""))
        text = _normalize_spaces(r.get("text") or r.get("chunk") or "")
        if text:
            triples.append((company, page_str, text))

    picked = clean_and_pick_sentences(question, triples, max_sent_total=12)
    max_bul = 3 if answer_mode == "normal" else (2 if answer_mode == "brief" else 0)
    bullets_raw = [st for _, _, _, st in picked]
    bullets = to_bullet_style(question, bullets_raw, max_bul)

    used_keys = {_norm_text_for_key(b) for b in bullets}
    grounds = []
    for _, _, _, st in picked:
        if _norm_text_for_key(st) in used_keys: continue
        if _accept_sentence(st, _topic_for_query(question)):
            grounds.append("· " + st)
            if len(grounds) >= 5: break

    refs = []
    seen_ref = set()
    for r in matches:
        k = (r.get("company", ""), r.get("file", ""), str(r.get("page", "")))
        if k in seen_ref: continue
        seen_ref.add(k)
        page_i = _as_page_int(r.get("page"))
        refs.append({
            "uid": r.get("uid"),
            "company": r.get("company", ""),
            "file": r.get("file") or r.get("path") or r.get("source") or "",
            "page": page_i if page_i is not None else (r.get("page") or ""),
            "score": float(r.get("rerank_score", r.get("score", 0.0)))
        })
        if len(refs) >= max_refs: break

    header = f"질문: {question}"
    parts = [header]
    if max_bul > 0 and bullets:
        parts.append("핵심 요약:\n" + "\n".join([f" - {b}" for b in bullets]))
    if grounds:
        parts.append("근거 문장:\n" + "\n".join(grounds))
    answer_text = "\n\n".join(parts).strip()

    slim_results = []
    for r in matches[:max_refs]:
        page_i = _as_page_int(r.get("page"))
        slim_results.append({
            "company": r.get("company") or r.get("document") or "",
            "file": r.get("file") or r.get("path") or r.get("source") or "",
            "page": page_i if page_i is not None else (r.get("page") or ""),
            "title": r.get("title") or "",
            "chunk": r.get("text") or r.get("chunk") or "",
            "chunk_idx": r.get("chunk_idx") or r.get("index") or ""
        })

    return {"answer": answer_text, "references": refs, "results": slim_results}

# ────────────────────────────────────────────────────────────────────────────────
# 자연어 결론(도난/음주/무사고/가족 전용) + 정리
# ────────────────────────────────────────────────────────────────────────────────
def _sanitize_korean_text(text: str) -> str:
    if not text: return ""
    t = unicodedata.normalize("NFKC", text)
    t = re.sub(r"</?w:[^>]+>|<w:[^>]+/?>", "", t)
    t = re.sub(r"\(\s*\*+\s*\d+\s*\)", "", t)
    t = re.sub(r"\[\s*\*+\s*\d+\s*\]", "", t)
    def _rm_round(m): return m.group(0) if m.group(1) else ""
    t = re.sub(r"(제)?\(\s*\d+\s*\)", _rm_round, t)
    def _rm_square(m): return m.group(0) if m.group(1) else ""
    t = re.sub(r"(제)?\[\s*\d+\s*\]", _rm_square, t)
    t = re.sub(r"[\(\[]\s*(?:주석|각주)\s*\d+\s*[\)\]]", "", t, flags=re.I)
    t = re.sub(r"\b(?:잠깐만!?|테스트|임시|샘플)\b", " ", t, flags=re.I)
    t = re.sub(r"[\u0300-\u036F\u20D0-\u20FF]", "", t)
    t = re.sub(r"([!?~….,])\1{1,}", r"\1", t)
    t = re.sub(r"[ \t]{2,}", " ", t)
    t = re.sub(r"[ \t]+\n", "\n", t)
    lines = [ln for ln in t.splitlines() if ln.strip() and not re.match(r"^[·•\-\*]\s*$", ln)]
    return "\n".join(lines).strip()

def _normalize_ko(s: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", s or "")).strip()

def _detect_topic(query: str, body_text: str) -> str:
    q = _normalize_ko(query); b = _normalize_ko(body_text)
    KEYS = {"family":_FAM_KEYS, "dui":_DUI_KEYS, "discount":_DISC_KEYS, "theft":_THEFT_KEYS}
    def score(keys):
        s=0
        for k in keys:
            if k in q: s+=3
            if k in b: s+=1
        return s
    scores = {k:score(v) for k,v in KEYS.items()}
    if any(k in q for k in _THEFT_KEYS): scores["theft"] += 4
    if any(k in q for k in ["무사고","무사고 할인"]): scores["discount"] += 3
    if any(k in q for k in ["음주","무면허","음주운전"]): scores["dui"] += 3
    order = ["theft","dui","discount","family"]
    return max(order, key=lambda t: (scores[t], -order.index(t)))

def _page_list_text(refs: List[Dict[str, Any]], max_n: int = 3) -> str:
    pages: List[str] = []
    for r in refs or []:
        p = r.get("page")
        if p is None or p == "": continue
        try: pages.append(str(int(float(p))))
        except Exception: pages.append(str(p))
        if len(pages) >= max_n: break
    return ", p.".join(pages)

def _format_natural_korean_answer(query: str, raw_answer: str, references: List[Dict[str, Any]], answer_mode: str) -> str:
    t = _sanitize_korean_text(raw_answer or "")
    t = re.sub(r"^\s*(핵심\s*요약|근거\s*문장|근거)\s*:?\s*$", "", t, flags=re.M)
    t = re.sub(r"^\s*질문\s*:\s*.*$", "", t, flags=re.M)

    lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
    if answer_mode == "clauses":
        return "\n".join(lines[:10])

    body_text = " ".join(lines)
    topic = _detect_topic(query, body_text)

    if topic == "family":
        return ("결론: ‘가족운전자 한정’(가족 특약)을 가입하면 약정된 가족 범위(예: 본인·배우자·자녀·부모 등) 내 운전자에 한해 보장이 적용되고, "
                "가족 범위 밖 운전자의 사고는 보상 대상에서 제외됩니다. 회사·상품별로 가족의 정의와 예외, 제출서류(가족관계증명서 등)가 다를 수 있으니 해당 약관 본문을 확인하세요.")
    if topic == "dui":
        pages = _page_list_text(references); ref_hint = (f" (예: p.{pages})" if pages else "")
        return ("결론: 음주·약물 또는 무면허 운전 중 발생한 사고는 약관상 보상 제외(면책) 또는 제한 보상에 해당하는 경우가 많습니다. "
                "다만 의무보험이나 일부 특별약관으로 최소한의 보상이 이뤄질 수 있으며, 사고부담금/자기부담금이 부과될 수 있습니다." + ref_hint)
    if topic == "discount":
        return ("결론: 무사고 할인은 특별약관 가입 시점에 1회 적용되며, 계약 중 점수 변경으로 추가 할인은 적용되지 않습니다. "
                "또한 1년 미만 계약 등 일부 조건에서는 가입이 제한될 수 있습니다. 자세한 요건은 회사별 보통·특별약관을 확인하세요.")
    if topic == "theft":
        pages = _page_list_text(references); ref_hint = (f" (예: p.{pages})" if pages else "")
        return ("결론: 차량 ‘도난/절도’ 손해는 보통 ‘자기차량손해(자차)’ 또는 ‘도난손해’ 관련 특별약관으로 담보됩니다. "
                "도난 사실 확인서류(경찰신고 접수 등) 제출이 필요하며, 보관/열쇠관리 소홀, 가족·동거인 등의 절취, 불법주정차 중 방치 등은 면책될 수 있습니다. "
                "감가 및 약정 자기부담금이 적용됩니다." + ref_hint)

    bullets = [re.sub(r"^[·•\-\*]\s*", "", ln) for ln in lines if re.match(r"^[·•\-\*]\s*", ln)]
    plain   = [ln for ln in lines if not re.match(r"^[·•\-\*]\s*", ln)]
    paras: List[str] = []
    if plain:   paras.append(" ".join(plain[:3]))
    if bullets: paras.append(" ".join(bullets[:2]))
    out = " ".join(paras).strip()
    return out or (t[:500] + ("…" if len(t) > 500 else ""))

# ────────────────────────────────────────────────────────────────────────────────
# (NEW) 의도 라우팅: 약관형 vs 일반형
# ────────────────────────────────────────────────────────────────────────────────
_GENERAL_HINTS = re.compile(r"(정리|요약|개요|설명해줘|비교|차이|가이드|원리|왜|무엇|어떻게)")
_REF_PATTERN   = re.compile(r"(?:^|\s)(결론\s*:|근거\s*:|근거\s*문장|p\.\d{1,4})", re.I)

def detect_intent_for_router(q: str, force: Optional[str] = None) -> str:
    if force in {"policy","general"}:
        return force
    qn = _normalize_spaces(q)
    if _REF_PATTERN.search(qn) or _GENERAL_HINTS.search(qn):
        if any(k in qn for k in _POLICY_HINTS) and not ("정리" in qn or "요약" in qn):
            return "policy"
        return "general"
    hit = sum(1 for k in _POLICY_HINTS if k in qn)
    if hit >= 2 or "약관" in qn or "보상" in qn or "면책" in qn:
        return "policy"
    return "general"

# ────────────────────────────────────────────────────────────────────────────────
# 페이지: 홈/인증/마이페이지
# ────────────────────────────────────────────────────────────────────────────────
def home(request: HttpRequest) -> HttpResponse:
    processor = EnhancedPDFProcessor()
    context = {
        'company_stats': processor.get_company_statistics(),
        'insurance_companies': processor.insurance_companies,
        'MEDIA_URL': settings.MEDIA_URL,
    }
    try:
        return render(request, 'insurance_app/home.html', context)
    except TemplateDoesNotExist:
        return render(request, 'insurance_app/recommendation.html', context)

def signup(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'{user.username}님의 계정이 생성되었습니다.')
            return redirect('login')
    else:
        form = CustomUserCreationForm()
    return render(request, 'insurance_app/signup.html', {'form': form})

def login_view(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            messages.info(request, "로그인되었습니다.")
            return redirect('home')
        else:
            messages.error(request, "아이디/비밀번호를 확인해주세요.")
    else:
        form = AuthenticationForm()
    return render(request, 'insurance_app/login.html', {'form': form})

@require_POST
@csrf_protect
def logout_view(request: HttpRequest) -> HttpResponse:
    logout(request)
    return redirect('login')

@login_required
def mypage(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = EmailPasswordChangeForm(request.POST, user=request.user, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "회원정보가 수정되었습니다.")
            return redirect('mypage')
    else:
        form = EmailPasswordChangeForm(user=request.user, instance=request.user)
    return render(request, 'insurance_app/mypage.html', {'form': form})

# ────────────────────────────────────────────────────────────────────────────────
# 추천 페이지/API
# ────────────────────────────────────────────────────────────────────────────────
@login_required
def recommend_insurance(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        try:
            user_profile = {
                'birth_date': str(getattr(request.user, 'birth_date', '1990-01-01')),
                'gender': getattr(request.user, 'gender', 'M'),
                'residence_area': request.POST.get('region', '서울'),
                'driving_experience': int(request.POST.get('driving_experience', 5)),
                'accident_history': int(request.POST.get('accident_history', 0)),
                'annual_mileage': int(request.POST.get('annual_mileage', 12000)),
                'car_info': {'type': request.POST.get('car_type', '준중형')},
                'coverage_level': request.POST.get('coverage_level', '표준'),
            }
            from .insurance_mock_server import InsuranceService
            service = InsuranceService()
            result = service.calculate_insurance_premium(user_profile)
            return JsonResponse({'success': True, 'data': result})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    else:
        context = {
            'user': request.user,
            'car_types': ['경차', '소형', '준중형', '중형', '대형', 'SUV'],
            'regions': ['서울', '부산', '대구', '인천', '광주', '대전', '울산', '기타'],
            'coverage_levels': ['기본', '표준', '고급', '프리미엄'],
            'insurance_companies': [
                '삼성화재', '현대해상', 'KB손해보험', '메리츠화재', 'DB손해보험',
                '롯데손해보험', '하나손해보험', '흥국화재', 'AXA손해보험', 'MG손해보험', '캐롯손해보험'
            ]
        }
        return render(request, 'insurance_app/recommend.html', context)

# ────────────────────────────────────────────────────────────────────────────────
# 챗봇 RAG + LLM 하이브리드 엔드포인트
# ────────────────────────────────────────────────────────────────────────────────
@csrf_exempt
def insurance_recommendation(request: HttpRequest) -> HttpResponse:
    if request.method != 'POST':
        processor = EnhancedPDFProcessor()
        context = {
            'company_stats': processor.get_company_statistics(),
            'insurance_companies': processor.insurance_companies,
            'MEDIA_URL': settings.MEDIA_URL,
        }
        return render(request, 'insurance_app/recommendation.html', context)

    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'success': False, 'error': '잘못된 요청 본문입니다.'}, status=400)

    query: str = (data.get('query') or data.get('question') or "").strip()
    company_name: Optional[str] = data.get('company')
    answer_mode: str = (data.get('answer_mode') or "normal").strip().lower()
    top_k: int = int(data.get("top_k") or 12)
    cand_k: int = max(2 * top_k, 20)

    if not query:
        return JsonResponse({'success': False, 'error': '질문을 입력해주세요.'}, status=400)

    # 1) 라우팅 결정 (강제옵션: force_mode=policy|general)
    force_mode = (data.get("force_mode") or "").strip().lower() or None
    intent = detect_intent_for_router(query, force=force_mode)

    # 2) 약관형 → RAG
    if intent == "policy" or answer_mode == "clauses":
        try:
            matches = retrieve_insurance_clauses(
                query=query, top_k=top_k, company=company_name,
                candidate_k=cand_k, min_score=0.0
            )
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'검색 실패: {str(e)}'}, status=500)

        orig_matches = matches
        matches = dedup_matches_by_tuple(matches)
        matches = fuzzy_dedup_matches(matches, threshold=0.965, window=80)
        matches = ensure_not_overpruned(orig_matches, matches, min_ratio=0.35, min_count=5)

        summary = build_answer(query, matches, max_refs=5, answer_mode=answer_mode)
        summary["answer"] = _format_natural_korean_answer(
            query=query,
            raw_answer=summary.get("answer", ""),
            references=summary.get("references", []),
            answer_mode=answer_mode
        )

        # 링크 보정
        refs_out: List[Dict[str, Any]] = []
        for _r in summary.get("references", []):
            _company = (_r.get("company") or "").strip()
            _fileval = (_r.get("file") or _r.get("path") or _r.get("source") or "").strip()
            _rel = _fileval
            if not _fileval.lower().endswith(".pdf") or "/" not in _fileval:
                _guess = _guess_pdf_relpath(company=_company, file_hint=_fileval)
                if _guess: _rel = _guess
            _r2 = dict(_r); _r2["file"] = _rel or _fileval; _r2["url"]  = f"/documents/{_rel}" if _rel else None
            refs_out.append(_r2)

        results_out: List[Dict[str, Any]] = []
        for _r in summary.get("results", []):
            _company = (_r.get("company") or "").strip()
            _fileval = (_r.get("file") or _r.get("path") or _r.get("source") or "").strip()
            _rel = _fileval
            if not _fileval.lower().endswith(".pdf") or "/" not in _fileval:
                _guess = _guess_pdf_relpath(company=_company, file_hint=_fileval)
                if _guess: _rel = _guess
            _r2 = dict(_r); _r2["file"] = _rel or _fileval; _r2["url"]  = f"/documents/{_rel}" if _rel else None
            results_out.append(_r2)

        return JsonResponse({
            'success': True,
            'answer': summary["answer"],
            'references': refs_out,
            'results': results_out,
            'total_results': len(matches),
            'used_model': os.getenv("EMBED_MODEL", "unknown"),
            'media_url': settings.MEDIA_URL,
        })

    # 3) 일반형 → 아카이브 기존 llm_client로 답변
    answer = call_llm_via_project_client(query)
    return JsonResponse({
        'success': True,
        'answer': answer,
        'references': [],
        'results': [],
        'total_results': 0,
        'used_model': os.getenv("OPENAI_MODEL", "project-llm"),
        'media_url': settings.MEDIA_URL,
    })

# ────────────────────────────────────────────────────────────────────────────────
# 용어 사전 페이지 & API
# ────────────────────────────────────────────────────────────────────────────────
def glossary(request):
    q = (request.GET.get("q") or "").strip()
    cat = (request.GET.get("cat") or "").strip()

    # 기본 조회(사전 정렬)
    qs = GlossaryTerm.objects.all().order_by("term")

    # 검색어 적용 (term/short/long + aliases 대충 포함검색)
    if q:
        qs = qs.filter(
            Q(term__icontains=q) |
            Q(short_def__icontains=q) |
            Q(long_def__icontains=q) |
            Q(aliases__icontains=q)
        )

    # 파이썬 레벨에서 3개 버킷 필터링(데이터 규모가 수백건 수준이라 충분히 가볍습니다)
    terms_all = list(qs)
    if cat and cat in BUCKETS:
        terms = [t for t in terms_all if infer_bucket(t) == cat]
    else:
        terms = terms_all

    context = {
        "terms": terms,
        "categories": BUCKETS,  # 드롭다운에 3개만 노출
        "q": q,
        "cat": cat,
    }
    return render(request, "insurance_app/glossary.html", context)

def glossary_api(request: HttpRequest) -> HttpResponse:
    q = (request.GET.get("q") or "").strip()
    cat = (request.GET.get("cat") or "").strip()
    limit = int(request.GET.get("limit") or 50)
    terms = GlossaryTerm.objects.all()
    if q:
        qs = q.lower()
        terms = terms.filter(
            Q(term__icontains=q) |
            Q(short_def__icontains=q) |
            Q(long_def__icontains=q) |
            Q(aliases__icontains=qs)
        )
    if cat:
        terms = terms.filter(category=cat)
    payload = [{
        "slug": t.slug,
        "term": t.term,
        "short_def": t.short_def,
        "long_def": t.long_def,
        "category": t.category,
        "aliases": t.aliases,
        "related": t.related,
        "meta": t.meta,
        "updated_at": t.updated_at.isoformat(),
    } for t in terms[:max(1, min(500, limit))]]
    return JsonResponse({"success": True, "count": len(payload), "results": payload})





