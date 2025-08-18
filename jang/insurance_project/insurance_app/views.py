import os
import json
import re
import math
from collections import defaultdict
import hashlib
import unicodedata
import difflib
from typing import Optional, Dict, Any, List, Tuple

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.views.decorators.http import require_http_methods, require_POST

from .models import CustomUser  # noqa: F401
from .forms import CustomUserCreationForm, UserProfileChangeForm, EmailPasswordChangeForm
from .pdf_processor import EnhancedPDFProcessor  # noqa: F401
from .pinecone_search import retrieve_insurance_clauses
from django.views.decorators.csrf import csrf_exempt


# ────────────────────────────────────────────────────────────────────────────────
# 공용 페이지
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
# 유틸: 정규화 & 중복 제거
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
# 문장 분리 / 품질·안전 필터
# ────────────────────────────────────────────────────────────────────────────────

_SENT_SPLIT = re.compile(r"((?:다\.)|[\.。!?])")

_TABLE_MARKS = re.compile(r"[○●◯×✕✖︎□■△▷▶╳]|(?:\b[○×]\b)")
_NUM_BULLET = re.compile(r"[①-⑳㈠-㈩]+\s*")
_BOX_CHARS  = re.compile(r"[━│┝┥└┘┌┐╂╋┼─—]+")
_ARTIFACT_TAGS = re.compile(r"^(?:<.*?>|〈.*?〉|【.*?】|※)\s*")
_NOISE_HEAD = re.compile(r"^(?:·|•|∙|▶|▷|-\s*|—\s*|ㄱ\.?|ㄴ\.?|ㄷ\.?)\s*")
_SHORT_PAREN = re.compile(r"\s*[\(\[\{][^\)\]\}]{0,60}[\)\]\}]\s*")

_UNPLEASANT_HINTS = re.compile(r"(모욕|비하|혐오|천대|경멸|폭언|막말)")

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

def _hangul_ratio(s: str) -> float:
    total = len(s)
    if total == 0: return 0.0
    hangul = sum(1 for ch in s if '가' <= ch <= '힣')
    return hangul / total

def compress_sentence(s: str) -> str:
    s = _normalize_spaces(s)
    if _TABLE_MARKS.search(s):
        return ""
    s = _BOX_CHARS.sub(" ", s)
    s = _NUM_BULLET.sub("", s)
    s = _NOISE_HEAD.sub("", s)
    s = _ARTIFACT_TAGS.sub("", s)
    s = _SHORT_PAREN.sub(" ", s)
    if len(re.findall(r"[,/|:·•●○×]", s)) >= 3:
        return ""
    if re.search(r"\d\.\s*$", s):
        return ""
    s = re.sub(r"\s{2,}", " ", s).strip()
    return s

def is_readable_sentence(s: str) -> bool:
    if not s: return False
    if len(s) < 8 or len(s) > 260: return False
    if _hangul_ratio(s) < 0.3: return False
    if len(re.findall(r"[^\w\s\.\,\(\)·\-\uAC00-\uD7A3]", s)) > 3:
        return False
    if not re.search(r"(다\.|요\.|니다\.|\.|!|？|!)\s*$", s):
        if not re.search(r"(보상|면책|지급|특약|한정|범위|조건|가입|불가|제한|거절|무효)", s):
            return False
    if _UNPLEASANT_HINTS.search(s):
        return False
    return True

def to_bullet_style(s: str) -> str:
    s = compress_sentence(s)
    if not s or not is_readable_sentence(s):
        return ""
    s = re.sub(r"(회사|보험회사)(?:는|가)\s*", "", s)
    s = re.sub(r"(보상하지 않습니다|지급하지 않습니다)", " 보상 제외", s)
    s = re.sub(r"(보상하지 아니합니다)", " 보상 제외", s)
    s = re.sub(r"(가입할 수 없습니다|가입할 수 없|가입 불가)", " 가입 불가", s)
    s = re.sub(r"(계약이 무효가 됩니다|무효가 됩니다|무효입니다)", " 계약 무효", s)
    s = s.replace("보상하지 않는 손해", "보상 제외 항목")
    s = re.sub(r"\s{2,}", " ", s).strip()
    return s


# ────────────────────────────────────────────────────────────────────────────────
# 의도 인식 + 토큰 필터
# ────────────────────────────────────────────────────────────────────────────────

def infer_topic_filters(question: str):
    q = _normalize_spaces(question)

    include, exclude, title_regex = set(), set(), None

    # 면책/보상 제외 의도
    if any(t in q for t in ["면책", "면책사항", "보상 제외", "보상하지", "지급하지 않는"]):
        include.update(["면책", "보상하지", "지급하지 않", "제외", "면책사항"])
        title_regex = re.compile(r"(보상하지.*손해|면책|지급하지.*않는)", re.I)
        exclude.update([
            "농업", "어업", "수산", "식품산업", "양식", "염전",
            "도로교통법", "어린이 보호구역", "경찰공무원", "호흡조사",
            "마일리지", "안전운전점수", "할인"
        ])

    # 가입 불가/인수 제한 의도  ← 추가
    if any(t in q for t in ["가입 불가", "가입불가", "가입 제한", "인수 제한", "인수제한", "인수 거절", "계약 무효", "특약 무효", "계약 취소"]):
        include.update([
            "가입 불가", "가입할 수 없", "가입 제한", "인수 제한", "인수거절", "계약 거절",
            "무효", "취소", "부적격", "허위", "거짓", "중대 과실", "의무 위반"
        ])
        title_regex = re.compile(r"(가입\s*불가|인수\s*(제한|거절)|계약\s*(무효|취소)|특약\s*무효)", re.I)
        # '가입대상/가입가능/할인/점수' 등 긍정·할인성 문구는 제외
        exclude.update([
            "가입대상", "가입할 수 있", "가입 가능합니다", "가능", "할인", "마일리지",
            "안전운전점수", "점수", "의무보험", "대물배상", "대인배상"
        ])

    return list(include), list(exclude), title_regex


# ────────────────────────────────────────────────────────────────────────────────
# 문장 선별(부정 의도 가중치/가산·감점 포함)
# ────────────────────────────────────────────────────────────────────────────────

_NEG_PAT = re.compile(r"(불가|제한|거절|무효|취소|제외|지급하지|보상하지|허위|거짓|의무 위반)")
_POS_ALLOW_PAT = re.compile(r"(가입(할 수)? 있|가능|허용|할인|우대)")

def clean_and_pick_sentences(
    question: str,
    texts: List[Tuple[str, str, Any]],
    max_sent_total: int = 8,
    include_tokens: Optional[List[str]] = None,
    exclude_tokens: Optional[List[str]] = None,
    title_regex: Optional[re.Pattern] = None
) -> List[Tuple[str, str, Any, str]]:
    include_tokens = include_tokens or []
    exclude_tokens = exclude_tokens or []
    q = _normalize_spaces(question)
    q_terms = [t for t in re.split(r"\s+", q) if len(t) >= 2]

    asking_negative = any(t in q for t in ["불가","제한","거절","무효","취소","면책","제외","지급하지","보상하지"])

    scored = []
    seen_norm = set()

    for company, page, raw in texts:
        raw_norm = _normalize_spaces(raw)
        must_keep = bool(title_regex and title_regex.search(raw_norm))

        for s in split_sentences(raw_norm):
            st = compress_sentence(s)
            if not st or not is_readable_sentence(st):
                continue

            # 제외 토큰
            if any(tok in st for tok in exclude_tokens):
                if not must_keep:
                    continue

            # 포함 토큰
            if include_tokens:
                if not (any(tok in st for tok in include_tokens) or must_keep):
                    continue

            key = _norm_text_for_key(st)
            if key in seen_norm:
                continue

            score = 1.0

            # 기본 쿼리 키워드 매칭
            for t in q_terms:
                if t in st:
                    score += 0.7

            # 의도: 부정(불가/제한/면책) 강화
            if asking_negative:
                if _NEG_PAT.search(st):
                    score += 1.2  # 불가·면책 표현 가산
                if _POS_ALLOW_PAT.search(st):
                    score -= 1.0  # '가입 가능/할인' 등은 감점

            # 표/나열 성향 약화
            if len(re.findall(r"[,:/|·•○●×]", st)) >= 2:
                score -= 0.4

            # 길이 조정
            if 40 <= len(st) <= 180:
                score += 0.2
            if len(st) > 220:
                score -= 0.3
            if len(st) < 18:
                score -= 0.2

            # 제목 정규식 히트는 강한 가산
            if must_keep:
                score += 0.8

            seen_norm.add(key)
            scored.append((score, company, page, raw, st))

    scored.sort(key=lambda x: x[0], reverse=True)
    picked = scored[:max_sent_total]
    return [(co, pg, raw, st) for _, co, pg, raw, st in picked]


# ────────────────────────────────────────────────────────────────────────────────
# 최종 답변 생성(요약 vs 근거 분리 + 중복 방지)
# ────────────────────────────────────────────────────────────────────────────────

def build_answer(question: str,
                 matches: List[Dict[str, Any]],
                 max_refs: int = 5) -> Dict[str, Any]:
    if not matches:
        return {
            "answer": "관련 약관을 찾지 못했습니다. 핵심 키워드(예: 면책, 불가, 인수 제한 등)를 포함해 다시 질문해 주세요.",
            "references": []
        }

    triples = []
    for r in matches:
        company = r.get("company") or r.get("document") or "보험사"
        page = r.get("page") or ""
        text = _normalize_spaces(r.get("text") or r.get("chunk") or "")
        if text:
            triples.append((company, str(page), text))

    inc, exc, title_rx = infer_topic_filters(question)
    picked = clean_and_pick_sentences(
        question, triples, max_sent_total=8,
        include_tokens=inc, exclude_tokens=exc, title_regex=title_rx
    )

    bullets, grounds = [], []
    seen_bullet = set()

    for _, _, _, st in picked:
        b = to_bullet_style(st)
        if not b:
            continue
        k = _norm_text_for_key(b)
        if k in seen_bullet:
            continue
        seen_bullet.add(k)
        bullets.append(" - " + b)
        if len(bullets) >= 4:
            break

    seen_ground = set()
    for co, pg, raw, st in picked:
        if any(_norm_text_for_key(st) == _norm_text_for_key(b.replace(" - ", "")) for b in bullets):
            continue
        k = _norm_text_for_key(st)
        if k in seen_ground:
            continue
        grounds.append(f" · {st}")
        seen_ground.add(k)
        if len(grounds) >= 5:
            break

    if not bullets and picked:
        for _, _, _, st in picked[:3]:
            if is_readable_sentence(st):
                bullets.append(" - " + compress_sentence(st))
    if not grounds and picked:
        for _, _, _, st in picked[:3]:
            if is_readable_sentence(st):
                grounds.append(" · " + st)

    refs, seen_ref = [], set()
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

    header = f"질문: {question}\n"
    body = "핵심 요약:\n" + ("\n".join(bullets) if bullets else " - 관련 조항을 충분히 찾지 못했습니다.")
    if grounds:
        body += "\n\n근거 문장(요약):\n" + "\n".join(grounds)

    return {"answer": (header + "\n\n" + body).strip(), "references": refs}


# ────────────────────────────────────────────────────────────────────────────────
# RAG 챗봇 엔드포인트
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

        # 중복 제어
        orig_matches = matches
        matches = dedup_matches_by_tuple(matches)
        matches = fuzzy_dedup_matches(matches, threshold=0.965, window=80)
        matches = ensure_not_overpruned(orig_matches, matches, min_ratio=0.35, min_count=5)

        summary = build_answer(query, matches, max_refs=5)

        return JsonResponse({
            'success': True,
            'answer': summary["answer"],
            'references': summary["references"],
            'total_results': len(matches),
            'used_model': os.getenv("EMBED_MODEL", "unknown")
        })

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
