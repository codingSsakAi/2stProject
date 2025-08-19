# insurance_app/views.py
import os
import json
import re
import math
from collections import defaultdict
import hashlib
import unicodedata
import difflib
from typing import Optional, Dict, Any, List, Tuple

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.views.decorators.http import require_POST
from django.conf import settings

from .models import CustomUser, GlossaryTerm  # ← GlossaryTerm 추가
from .forms import CustomUserCreationForm, UserProfileChangeForm, EmailPasswordChangeForm
from .pdf_processor import EnhancedPDFProcessor  # noqa: F401
from .pinecone_search import retrieve_insurance_clauses
from insurance_app import models
from django.db.models import Q


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

# ───── (검색/중복제거 유틸 그대로) ─────
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

def fuzzy_dedup_matches(matches: List[Dict[str, Any]], text_field: str = "text", threshold: float = 0.965, window: int = 80) -> List[Dict[str, Any]]:
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

def ensure_not_overpruned(original: List[Dict[str, Any]], pruned: List[Dict[str, Any]], min_ratio: float = 0.35, min_count: int = 5) -> List[Dict[str, Any]]:
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

_SENT_SPLIT = re.compile(r"((?:다\.)|[\.。!?])")

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

_NOISE_PAT = re.compile(r"^(?:\d+[\).]|\(?[가-힣A-Za-z]\)|[-–—•●■□▶▷])\s*$")
_ENUM_TOKENS = "①②③④⑤⑥⑦⑧⑨⑩ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ"
_BULLET_TOKENS = r"[•·●○■□▶▷\-\–\—•∙※▶️➤★☆◇◆]"

def _starts_with_enumerator(s: str) -> bool:
    s2 = s.strip()
    return bool(re.match(rf"^([{_ENUM_TOKENS}0-9]+[\.\)\-]|\(?[가-힣A-Za-z]\))\s+", s2))

def _contains_table_marks(s: str) -> bool:
    t = re.sub(r"\s+", "", s)
    return bool(re.fullmatch(r"[○◯●◎△▲▽▼□■◇◆✕×･·\-\–—\|]+", t)) or ("○" in s and "×" in s)

def _strip_list_artifacts(s: str) -> str:
    s = re.sub(rf"^{_BULLET_TOKENS}\s*", "", s.strip())
    s = re.sub(r"^\(?[0-9가-힣A-Za-z]+[\.\)]\s*", "", s)
    s = s.lstrip(_ENUM_TOKENS + " ").strip()
    return s

def to_bullet_style(q: str, sentences: List[str], max_bullets: int) -> List[str]:
    q_terms = [t for t in re.split(r"\s+", _normalize_spaces(q)) if len(t) >= 2]
    out, seen = [], set()
    for s in sentences:
        s = _strip_list_artifacts(s)
        if not s or len(s) < 12:
            continue
        if _contains_table_marks(s):
            continue
        key = _norm_text_for_key(s)
        if key in seen:
            continue
        seen.add(key)
        if q_terms and not any(t in s for t in q_terms):
            if len(out) >= max_bullets - 1:
                continue
        out.append(s)
        if len(out) >= max_bullets:
            break
    return out

def clean_and_pick_sentences(question: str, texts: List[Tuple[str, str, Any]], max_sent_total: int = 10) -> List[Tuple[str, str, Any, str]]:
    q = _normalize_spaces(question)
    q_terms = [t for t in re.split(r"\s+", q) if len(t) >= 2]
    scored = []
    seen_norm = set()
    for company, page, raw in texts:
        sents = split_sentences(raw)
        for s in sents:
            st = _normalize_spaces(s)
            if not st or len(st) < 6:
                continue
            if _NOISE_PAT.match(st):
                continue
            if _starts_with_enumerator(st) or _contains_table_marks(st):
                continue
            key = _norm_text_for_key(st)
            if key in seen_norm:
                continue
            score = 1.0
            for t in q_terms:
                if t in st:
                    score += 1.2
            if len(st) > 220:
                score -= 0.25
            if len(st) < 20:
                score -= 0.25
            seen_norm.add(key)
            scored.append((score, company, page, raw, st))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [(co, pg, raw, st) for _, co, pg, raw, st in scored[:max_sent_total]]

def build_answer(question: str, matches: List[Dict[str, Any]], max_refs: int = 5, answer_mode: str = "normal") -> Dict[str, Any]:
    if not matches:
        return {
            "answer": f"질문: {question}\n\n관련 약관을 찾지 못했습니다. 핵심 키워드(예: 면책, 음주, 도난 등)를 포함해 다시 질문해 주세요.",
            "references": [],
            "results": []
        }
    triples = []
    for r in matches:
        company = r.get("company") or r.get("document") or "보험사"
        page = r.get("page") or ""
        text = _normalize_spaces(r.get("text") or r.get("chunk") or "")
        if text:
            triples.append((company, str(page), text))
    picked = clean_and_pick_sentences(question, triples, max_sent_total=10)
    max_bul = 2 if answer_mode == "brief" else (0 if answer_mode == "clauses" else 4)
    bullets_raw = [st for _, _, _, st in picked]
    bullets = to_bullet_style(question, bullets_raw, max_bul)
    used_keys = {_norm_text_for_key(b) for b in bullets}
    grounds = []
    for _, _, _, st in picked:
        if _norm_text_for_key(st) in used_keys:
            continue
        grounds.append("· " + _strip_list_artifacts(st))
        if len(grounds) >= 5:
            break
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
            "file": r.get("file") or r.get("path") or r.get("source") or "",
            "page": r.get("page", ""),
            "score": float(r.get("rerank_score", r.get("score", 0.0)))
        })
        if len(refs) >= max_refs:
            break
    header = f"질문: {question}"
    body = ""
    if max_bul > 0 and bullets:
        body += "핵심 요약:\n" + "\n".join([f" - {b}" for b in bullets]) + "\n"
    if grounds:
        body += ("\n근거 문장:\n" + "\n".join(grounds)).rstrip()
    slim_results = []
    for r in matches[:max_refs]:
        slim_results.append({
            "company": r.get("company") or r.get("document") or "",
            "file": r.get("file") or r.get("path") or r.get("source") or "",
            "page": r.get("page") or "",
            "title": r.get("title") or "",
            "chunk": r.get("text") or r.get("chunk") or "",
            "chunk_idx": r.get("chunk_idx") or r.get("index") or ""
        })
    return {
        "answer": (header + "\n\n" + body).strip(),
        "references": refs,
        "results": slim_results
    }

@csrf_exempt
def insurance_recommendation(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
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
        try:
            matches = retrieve_insurance_clauses(
                query=query, top_k=top_k, company=company_name, candidate_k=cand_k, min_score=0.0
            )
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'검색 실패: {str(e)}'}, status=500)
        orig_matches = matches
        matches = dedup_matches_by_tuple(matches)
        matches = fuzzy_dedup_matches(matches, threshold=0.965, window=80)
        matches = ensure_not_overpruned(orig_matches, matches, min_ratio=0.35, min_count=5)
        summary = build_answer(query, matches, max_refs=5, answer_mode=answer_mode)
        return JsonResponse({
            'success': True,
            'answer': summary["answer"],
            'references': summary["references"],
            'results': summary["results"],
            'total_results': len(matches),
            'used_model': os.getenv("EMBED_MODEL", "unknown"),
            'media_url': settings.MEDIA_URL,
        })
    processor = EnhancedPDFProcessor()
    company_stats = processor.get_company_statistics()
    context = {
        'company_stats': company_stats,
        'insurance_companies': processor.insurance_companies,
        'MEDIA_URL': settings.MEDIA_URL,
    }
    return render(request, 'insurance_app/recommendation.html', context)

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


# ────────────────────────────────────────────────────────────────────────────────
# 용어 사전: 페이지 & API
# ────────────────────────────────────────────────────────────────────────────────
def glossary(request: HttpRequest) -> HttpResponse:
    """웹 UI: 검색/필터 가능한 용어 사전 페이지"""
    q = (request.GET.get("q") or "").strip()
    cat = (request.GET.get("cat") or "").strip()
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
    categories = list(GlossaryTerm.objects.order_by().values_list("category", flat=True).distinct())
    context = {
        "terms": terms[:500],
        "q": q,
        "cat": cat,
        "categories": categories
    }
    return render(request, "insurance_app/glossary.html", context)


def glossary_api(request: HttpRequest) -> HttpResponse:
    """JSON API: /api/glossary?q=...&cat=...&limit=50"""
    q = (request.GET.get("q") or "").strip()
    cat = (request.GET.get("cat") or "").strip()
    limit = int(request.GET.get("limit") or 100)
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
