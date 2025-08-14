import os
import json
import re
import math
import hashlib
import unicodedata
import difflib
from typing import Optional, Dict, Any, List, Tuple, Set

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.views.decorators.http import require_POST

from .models import CustomUser  # noqa: F401
from .forms import CustomUserCreationForm, UserProfileChangeForm, EmailPasswordChangeForm
from .pdf_processor import EnhancedPDFProcessor  # noqa: F401
from .pinecone_search import retrieve_insurance_clauses

# ────────────────────────────────────────────────────────────────────────────────
# 기본 페이지
# ────────────────────────────────────────────────────────────────────────────────

def home(request: HttpRequest) -> HttpResponse:
    return render(request, 'insurance_app/home.html')


def signup(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'{username}님의 계정이 성공적으로 생성되었습니다!')
            return redirect('login')
    else:
        form = CustomUserCreationForm()
    return render(request, 'insurance_app/signup.html', {'form': form})


def login_view(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.info(request, f"{username}님, 환영합니다!")
                return redirect('home')
            else:
                messages.error(request, "로그인에 실패했습니다.")
        else:
            messages.error(request, "아이디 또는 비밀번호가 올바르지 않습니다.")
    else:
        form = AuthenticationForm()
    return render(request, 'insurance_app/login.html', {'form': form})


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
# 텍스트 정규화/중복 제거 유틸
# ────────────────────────────────────────────────────────────────────────────────

def _normalize_spaces(s: str) -> str:
    s = unicodedata.normalize("NFC", s or "")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\s*\n\s*", " ", s)
    s = re.sub(r"\s{2,}", " ", s)
    return s.strip()

def _norm_text_for_key(t: str) -> str:
    t = unicodedata.normalize("NFC", t or "")
    t = re.sub(r"[■□※▷▶●○・∙·…•\u2022]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip().lower()
    return t

def _make_tuple_key(m: Dict[str, Any]) -> tuple:
    company = (m.get("company") or m.get("document") or "").strip()
    file_   = (m.get("file") or "").strip()
    page    = str(m.get("page") or "")
    text    = _norm_text_for_key((m.get("text") or m.get("chunk") or "")[:200])
    score   = float(m.get("rerank_score", m.get("score", 0.0)))
    score_bucket = round(score, 2)
    return (company, file_, page, text, score_bucket)

def dedup_matches_by_tuple(matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    uniq = []
    for m in matches:
        key = _make_tuple_key(m)
        if key in seen:
            continue
        seen.add(key)
        uid_src = "|".join(map(str, key))
        m["uid"] = hashlib.md5(uid_src.encode("utf-8")).hexdigest()
        uniq.append(m)
    return uniq

def fuzzy_dedup_matches(matches: List[Dict[str, Any]],
                        text_field: str = "text",
                        threshold: float = 0.965,
                        window: int = 80) -> List[Dict[str, Any]]:
    kept, norms = [], []
    for m in matches:
        t = _norm_text_for_key(m.get(text_field) or m.get("chunk") or "")
        is_dup = False
        for prev in norms[-window:]:
            if t == prev or difflib.SequenceMatcher(None, t, prev).ratio() >= threshold:
                is_dup = True
                break
        if not is_dup:
            kept.append(m)
            norms.append(t)
    return kept

def ensure_not_overpruned(original: List[Dict[str, Any]],
                          pruned: List[Dict[str, Any]],
                          min_ratio: float = 0.35,
                          min_count: int = 5) -> List[Dict[str, Any]]:
    need = max(min_count, math.ceil(len(original) * min_ratio))
    if len(pruned) >= need:
        return pruned
    have = {m.get("uid") for m in pruned if m.get("uid")}
    fill = []
    for m in original:
        if m.get("uid") in have:
            continue
        fill.append(m)
        if len(pruned) + len(fill) >= need:
            break
    return pruned + fill

# ────────────────────────────────────────────────────────────────────────────────
# 토픽 키워드 & 문장 필터/스코어러
# ────────────────────────────────────────────────────────────────────────────────

# 안전한 문장 분리(lookbehind 금지)
_SENT_SPLIT = re.compile(r"((?:다\.)|[\.。!?])")

_TABLE_TOKENS = {"구분", "비고", "표", "요율", "할인율", "등급", "등급표", "요금", "기명1인"}
_BULLET_GLYPHS = set("○●■□▲▶▷▸•・∙·※")
_JUNK_PATS = [
    re.compile(r"(?:\d{1,3}(?:,\d{3})+|[0-9]+)\s*(?:원|만원|억원|%|㎞|km)"),
    re.compile(r"(?:기명1인|부부|자녀|가족)\s*[○×]"),
    re.compile(r"^\s*(?:Q|A)\s*[:·]"),
]
_NOISE_PREFIX = (
    "가입하는 경우 가입 가능합니다",
    "잠깐만",
    "비고 구분",
)

_POLICY_CORE = [
    "보상", "지급", "면책", "예외", "제외", "한도", "공제", "자기부담",
    "책임", "의무", "위반", "손해", "담보", "특약", "약관", "보험증권", "청구",
    "사고부담금", "음주", "무면허", "도난", "대여", "대인", "대물"
]

def extract_topic(question: str) -> str:
    q = question
    if any(k in q for k in ("음주", "무면허", "마약", "약물")): return "impaired"
    if any(k in q for k in ("무사고", "할인", "마일리지", "안전운전")): return "discount"
    if any(k in q for k in ("면책", "제외", "지급하지")): return "exclusion"
    if any(k in q for k in ("도난", "절도")): return "theft"
    if any(k in q for k in ("가족", "운전자범위", "특약")): return "family"
    return "generic"

def topic_keywords(topic: str) -> Set[str]:
    if topic == "impaired":
        return {"음주", "무면허", "사고부담금", "약물", "음주운전"}
    if topic == "discount":
        return {"할인", "마일리지", "안전운전", "점수", "후할인", "주행거리"}
    if topic == "exclusion":
        return {"면책", "지급하지", "제외", "전쟁", "지진", "고의"}
    if topic == "theft":
        return {"도난", "절도", "발견될", "자기차량손해", "대여자동차"}
    if topic == "family":
        return {"가족", "운전자범위", "한정운전", "부부", "자녀", "지정1인"}
    return set()

def split_sentences(text: str) -> List[str]:
    text = _normalize_spaces(text)
    if not text:
        return []
    parts = _SENT_SPLIT.split(text)
    sents = []
    i = 0
    while i < len(parts):
        seg = parts[i].strip()
        if i + 1 < len(parts) and _SENT_SPLIT.fullmatch(parts[i+1] or ""):
            seg += parts[i+1]
            i += 2
        else:
            i += 1
        seg = seg.strip()
        if seg:
            sents.append(seg)
    return sents

def _is_table_like(s: str, topic_hint: str) -> bool:
    t = _normalize_spaces(s)
    relaxed = (topic_hint == "discount")
    tok_hit = any(tok in t for tok in _TABLE_TOKENS)
    glyph_hit = any(g in t for g in _BULLET_GLYPHS)
    numbers = len(re.findall(r"\d", t))
    punct = len(re.findall(r"[|/·•∙%㎡㎞]", t))
    junk_pat = any(p.search(t) for p in _JUNK_PATS)
    if junk_pat and not relaxed:
        return True
    if (tok_hit or glyph_hit) and (numbers + punct) >= 3 and not relaxed:
        return True
    if numbers / max(1, len(t)) > 0.12 and not relaxed:
        return True
    if any(t.startswith(pfx) for pfx in _NOISE_PREFIX):
        return True
    return False

def _policy_core_bonus(s: str) -> float:
    return sum(0.35 for k in _POLICY_CORE if k in s)

def _length_penalty(n: int) -> float:
    if n > 240: return -0.6
    if n < 18:  return -0.35
    return 0.0

def _law_citation_penalty(s: str) -> float:
    if re.search(r"제\d+조", s) and not any(w in s for w in ("약관", "담보", "보상", "지급", "면책")):
        return -0.6
    return 0.0

def _stitch_pair(s1: str, s2: str) -> Optional[str]:
    if len(s1) < 40 and len(s2) < 140:
        if any(p.search(s1) for p in _JUNK_PATS): return None
        if any(p.search(s2) for p in _JUNK_PATS): return None
        return _normalize_spaces(f"{s1} {s2}")
    return None

def clean_and_pick_sentences(question: str,
                             texts: List[Tuple[str, str, Any]],
                             max_sent_total: int = 8) -> List[Tuple[str, str, Any, str]]:
    topic = extract_topic(question)
    kws = topic_keywords(topic)

    q = _normalize_spaces(question)
    q_terms = [t for t in re.split(r"\s+", q) if len(t) >= 2]

    scored = []
    seen_norm = set()

    for company, page, raw in texts:
        sents = split_sentences(raw)
        i = 0
        while i < len(sents):
            s = _normalize_spaces(sents[i])
            i += 1
            if not s:
                continue

            st = s
            if i < len(sents):
                stitched = _stitch_pair(s, _normalize_spaces(sents[i]))
                if stitched and len(stitched) <= 220:
                    st = stitched
                    i += 1

            # 토픽 키워드 매칭(없으면 큰 감점)
            topic_hit = any(kw in st for kw in kws) if kws else True

            # 표/라벨/잡음 억제
            if _is_table_like(st, topic):
                topic_hit = False  # 사실상 제외

            score = 0.7 if topic_hit else 0.1
            for t in q_terms:
                if t in st:
                    score += 0.8
            score += _policy_core_bonus(st)
            score += _length_penalty(len(st))
            score += _law_citation_penalty(st)

            key = _norm_text_for_key(st)
            if key in seen_norm:
                continue
            seen_norm.add(key)
            scored.append((score, company, page, raw, st))

    scored.sort(key=lambda x: x[0], reverse=True)
    picked = [x for x in scored if x[0] > 0.6][:max_sent_total]  # 저품질 컷
    if not picked:  # 너무 엄격하면 백업
        picked = scored[:max_sent_total]
    out = [(co, pg, raw, st) for _, co, pg, raw, st in picked]
    return out

# ────────────────────────────────────────────────────────────────────────────────
# 규칙형 요약기(LLM 미사용 시)
# ────────────────────────────────────────────────────────────────────────────────

def _simplify_phrase(s: str) -> str:
    """표/라벨 흔적, 불필요 숫자 삭제 등 문장 정리(근거엔 적용하지 않음)."""
    s = _normalize_spaces(s)
    s = re.sub(r"\[[^\]]{0,40}\]", "", s)  # [비고], [형사합의금 ...] 제거
    s = re.sub(r"[▶▷•·∙■□○●]+", " ", s)
    s = re.sub(r"\(.*?표\)", "", s)  # (별표 X)류
    s = re.sub(r"\s{2,}", " ", s)
    return s.strip(" -·")

def summarise_policy_from_sentences(question: str,
                                    picked: List[Tuple[str, str, Any, str]]) -> List[str]:
    """증거문장 집합을 보고 조건/한도/면책/부담금/절차 중심으로 3~5개 규칙형 요약 생성."""
    topic = extract_topic(question)
    text_all = " ".join(st for _, _, _, st in picked)
    bullets: List[str] = []

    def has(*keys): return all(k in text_all for k in keys)
    def anyof(*keys): return any(k in text_all for k in keys)

    # 공통 규칙
    if anyof("보험증권", "가입금액", "한도"):
        bullets.append("지급 한도는 보험증권에 기재된 담보별 가입금액(한도) 내에서 산정됩니다.")
    if anyof("자기부담", "공제", "사고부담금"):
        bullets.append("약관상 공제(자기부담·사고부담금)가 있는 경우 해당 금액을 차감합니다.")
    if anyof("방지", "경감", "변호사", "법률비용", "방어비용"):
        bullets.append("손해의 방지·경감 또는 방어에 필요한 비용은 약관이 허용하는 범위에서 인정될 수 있습니다.")

    # 토픽별 규칙
    if topic == "impaired":
        if anyof("음주", "무면허", "약물"):
            bullets.append("음주·무면허·약물 운전은 보상 범위가 제한되며, 사고부담금이 부과되거나 면책될 수 있습니다.")
        if anyof("대인배상", "대물배상", "자기신체", "자동차상해"):
            bullets.append("적용 담보(대인·대물·자기신체/자동차상해)에 따라 보상 방식과 한도가 달라집니다.")
    elif topic == "discount":
        if anyof("마일리지", "주행거리"):
            bullets.append("마일리지(주행거리) 특약은 약정 주행거리·정산 요건 충족 시에만 할인 적용이 가능합니다.")
        if anyof("안전운전점수", "점수"):
            bullets.append("안전운전 점수 기반 할인은 회사가 정한 인증·확인 절차에 협조해야 유효합니다.")
        if anyof("최초 1회", "추가 적용하지"):
            bullets.append("특약 규정상 할인은 가입 시점 1회 적용 등 제한이 있을 수 있습니다.")
    elif topic == "exclusion":
        if anyof("면책", "지급하지"):
            bullets.append("약관에 정한 면책 사유(예: 고의, 일정 법령 위반, 일부 자연재해 등)에는 보험금이 지급되지 않습니다.")
    elif topic == "theft":
        if anyof("도난", "발견될"):
            bullets.append("도난의 경우, 도난 시점부터 발견 시점까지 발생한 손해 중 약관에 정한 담보 범위 내에서 보상됩니다.")
        if anyof("자기차량손해"):
            bullets.append("일부 부속품만의 단독 도난 등은 자기차량손해 담보에서 제외될 수 있습니다.")
    elif topic == "family":
        if anyof("운전자범위", "한정운전", "가족"):
            bullets.append("운전자범위를 가족/부부/기명1인 등으로 한정한 경우, 약정 범위 밖 운전자의 사고는 보상에서 제외됩니다.")
        if anyof("증명서", "등본", "서류"):
            bullets.append("가족범위 확인을 위해 회사가 요구하는 증빙서류(예: 가족관계증명서)를 제출해야 할 수 있습니다.")

    # 중복 제거 및 3~5개로 정리
    uniq = []
    seen = set()
    for b in bullets:
        k = _norm_text_for_key(b)
        if k in seen or len(_normalize_spaces(b)) < 10:
            continue
        seen.add(k)
        uniq.append(_simplify_phrase(b))
    return uniq[:5] if uniq else []

# ────────────────────────────────────────────────────────────────────────────────
# LLM 정제(옵션)
# ────────────────────────────────────────────────────────────────────────────────

def _get_llm_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None, None
    model = os.getenv("LLM_REFINE_MODEL", "gpt-4o-mini")
    try:
        from openai import OpenAI  # type: ignore
        client = OpenAI(api_key=api_key)
        return client, model
    except Exception:
        try:
            import openai  # type: ignore
            openai.api_key = api_key
            return openai, model
        except Exception:
            return None, None

def refine_with_llm(question: str,
                    candidates: List[Dict[str, Any]],
                    allow_tables: bool) -> Optional[Dict[str, Any]]:
    use_llm = os.getenv("USE_LLM_REFINE", "0") in ("1", "true", "True")
    if not use_llm or not candidates:
        return None
    client, model = _get_llm_client()
    if not client or not model:
        return None

    system = (
        "You are a careful assistant for Korean motor insurance clauses.\n"
        "Given a question and evidence sentences with IDs, output 3-5 policy-style bullets (paraphrased) "
        "and pick 3-5 evidence IDs. Avoid table fragments unless the user asks about discounts/mileage. "
        "Output strict JSON with keys: bullets, evidence_ids, notes."
    )
    topic = extract_topic(question)
    allow_tables = allow_tables or (topic == "discount")

    trimmed = candidates[:10]
    user = (
        f"[질문]\n{question}\n\n"
        f"[후보 근거 문장]\n" +
        "\n".join([f"- {c['id']}: {c['sentence']}  (src={c.get('company','')} p={c.get('page','')})" for c in trimmed]) +
        "\n\n[지침]\n- Bullets: 3~5개, 중복 금지, 숫자나 표 라벨 나열은 피하기.\n"
        f"- 표/라벨/숫자조각 배제{'(할인/마일리지이면 허용)' if allow_tables else ''}.\n"
        "- 반드시 JSON만 출력."
    )

    try:
        if hasattr(client, "chat"):
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role":"system","content":system},
                          {"role":"user","content":user}],
                temperature=0.2,
            )
            content = resp.choices[0].message.content
        else:
            content = client.ChatCompletion.create(
                model=model,
                messages=[{"role":"system","content":system},
                          {"role":"user","content":user}],
                temperature=0.2,
            )["choices"][0]["message"]["content"]
        data = json.loads(content)
        if not isinstance(data, dict):
            return None
        data["bullets"] = [str(x).strip() for x in data.get("bullets", []) if str(x).strip()]
        data["evidence_ids"] = [str(x).strip() for x in data.get("evidence_ids", []) if str(x).strip()]
        data["notes"] = str(data.get("notes", "")).strip()
        if not data["bullets"]:
            return None
        return data
    except Exception:
        return None

# ────────────────────────────────────────────────────────────────────────────────
# 답변 생성(휴리스틱 + 옵션 LLM 정제)
# ────────────────────────────────────────────────────────────────────────────────

def build_answer(question: str,
                 matches: List[Dict[str, Any]],
                 max_refs: int = 5) -> Dict[str, Any]:
    if not matches:
        return {
            "answer": "관련 약관을 찾지 못했습니다. 핵심 키워드(예: 면책, 음주, 도난 등)를 포함해 다시 질문해 주세요.",
            "references": []
        }

    # 문장 후보 추출
    triples = []
    for r in matches:
        company = r.get("company") or r.get("document") or "보험사"
        page = r.get("page") or ""
        text = _normalize_spaces(r.get("text") or r.get("chunk") or "")
        if not text:
            continue
        triples.append((company, str(page), text))

    picked = clean_and_pick_sentences(question, triples, max_sent_total=8)

    # 후보 → LLM 정제 or 규칙형 요약
    candidates = []
    for idx, (co, pg, raw, st) in enumerate(picked, 1):
        candidates.append({"id": f"E{idx}", "sentence": st, "company": co, "page": pg})

    allow_tables = ("할인" in question) or ("마일리지" in question)
    llm_out = refine_with_llm(question, candidates, allow_tables)

    if llm_out:
        bullets = llm_out.get("bullets", [])[:5]
        chosen_ids = set(llm_out.get("evidence_ids", [])[:5])
        grounds = [f" · {c['sentence']}" for c in candidates if c["id"] in chosen_ids][:5]
        llm_refine = True
    else:
        bullets = summarise_policy_from_sentences(question, picked)
        # 근거 문장: 상위 3~5개(요약과 동일하지 않게 원문 유지)
        grounds = [f" · {st}" for _, _, _, st in picked[:5]]
        llm_refine = False

    # 레퍼런스(회사/파일/페이지) 고유화
    refs = []
    seen_ref = set()
    for r in matches:
        k = (r.get("company", ""), r.get("file", ""), str(r.get("page", "")))
        if k in seen_ref:
            continue
        seen_ref.add(k)
        refs.append({
            "uid": r.get("uid"),
            "company": r.get("company", ""),
            "file": r.get("file", ""),
            "page": r.get("page", ""),
            "score": float(r.get("rerank_score", r.get("score", 0.0)))
        })
        if len(refs) >= max_refs:
            break

    # 최소 3줄 이상 보장(너무 텅빈 출력 방지)
    if len(bullets) < 3:
        # 근거 기반 백업 문장 추가
        for _, _, _, st in picked:
            if st not in bullets:
                bullets.append(_simplify_phrase(st))
            if len(bullets) >= 3:
                break

    header = f"질문: {question}\n"
    body = "핵심 요약:\n" + "\n".join([f" - {b}" for b in bullets])
    if grounds:
        body += "\n\n근거 문장(요약):\n" + "\n".join(grounds)

    out = {
        "answer": (header + "\n" + body).strip(),
        "references": refs,
        "llm_refine": llm_refine
    }
    return out

# ────────────────────────────────────────────────────────────────────────────────
# RAG 챗봇 전용 엔드포인트
# ────────────────────────────────────────────────────────────────────────────────

@csrf_exempt
def insurance_recommendation(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            return JsonResponse({'success': False, 'error': '잘못된 요청 본문입니다.'}, status=400)

        query: str = (data.get('query') or data.get('question') or "").strip()
        company_name: Optional[str] = data.get('company')
        top_k: int = int(data.get("top_k") or 12)
        cand_k: int = max(2 * top_k, 20)
        if not query:
            return JsonResponse({'success': False, 'error': '질문을 입력해주세요.'}, status=400)

        try:
            matches = retrieve_insurance_clauses(
                query=query,
                top_k=top_k,
                company=company_name,
                candidate_k=cand_k,
                min_score=0.0
            )
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'검색 실패: {str(e)}'}, status=500)

        # 중복/잡음 정리
        orig_matches = matches
        matches = dedup_matches_by_tuple(matches)
        matches = fuzzy_dedup_matches(matches, threshold=0.965, window=80)
        min_ratio = float(os.getenv("RAG_MIN_RATIO", "0.35"))
        min_count = int(os.getenv("RAG_MIN_COUNT", "5"))
        matches = ensure_not_overpruned(orig_matches, matches, min_ratio=min_ratio, min_count=min_count)

        # 답변 생성
        summary = build_answer(query, matches, max_refs=5)

        return JsonResponse({
            'success': True,
            'answer': summary["answer"],
            'references': summary["references"],
            'total_results': len(matches),
            'used_model': os.getenv("EMBED_MODEL", "unknown"),
            'llm_refine': bool(summary.get("llm_refine", False)),
        })

    # GET: 챗봇 페이지
    processor = EnhancedPDFProcessor()
    company_stats = processor.get_company_statistics()
    context = {
        'company_stats': company_stats,
        'insurance_companies': processor.insurance_companies
    }
    return render(request, 'insurance_app/recommendation.html', context)

# ────────────────────────────────────────────────────────────────────────────────
# 계정 관련
# ────────────────────────────────────────────────────────────────────────────────

@require_POST
@csrf_protect
def logout_view(request: HttpRequest) -> HttpResponse:
    storage = messages.get_messages(request)
    for _ in storage:
        pass
    storage.used = True
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
