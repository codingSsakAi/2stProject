import os
import json
from typing import Dict, List, Any, Optional

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
                '삼성화재','현대해상','KB손해보험','메리츠화재','DB손해보험',
                '롯데손해보험','하나손해보험','흥국화재','AXA손해보험','MG손해보험','캐롯손해보험'
            ]
        }
        return render(request, 'insurance_app/recommend.html', context)

# ────────────────────────────────────────────────────────────────────────────────
# 보조 API
# ────────────────────────────────────────────────────────────────────────────────

@csrf_exempt
def get_company_detail(request: HttpRequest, company_name: str) -> JsonResponse:
    try:
        return JsonResponse({"company_name": company_name, "detail": f"{company_name} 보험사 상세 정보"})
    except Exception as e:
        return JsonResponse({'error': f'보험사 정보 조회 중 오류: {str(e)}'}, status=500)

def get_market_analysis(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"market_summary": "자동차보험 시장 동향 및 보험사별 경쟁력 분석 예시"})

def clause_summary(request: HttpRequest, clause_id: int) -> JsonResponse:
    return JsonResponse({
        'success': True,
        'clause_id': clause_id,
        'summary': f'약관 {clause_id}번에 대한 요약입니다.'
    })

# ────────────────────────────────────────────────────────────────────────────────
# 검색 (키워드 게이트 제거, 순수 RAG)
# ────────────────────────────────────────────────────────────────────────────────

@csrf_exempt
def insurance_recommendation(request: HttpRequest) -> HttpResponse:
    """
    POST: 자연어 쿼리 → Pinecone 검색(순수 RAG) → Top-K 반환
    GET : 추천 페이지 렌더(기존 유지)
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            return JsonResponse({'success': False, 'error': '잘못된 요청 본문입니다.'}, status=400)

        query: str = data.get('query', '').strip()
        company_name: Optional[str] = data.get('company', None)
        client_filters: Optional[Dict[str, Any]] = data.get('filters', None)

        if not query:
            return JsonResponse({'success': False, 'error': '검색어를 입력해주세요.'}, status=400)

        results = retrieve_insurance_clauses(
            query=query,
            top_k=30,              # 클라에서 회사별 Top-1 묶고 싶으면 프런트에서 처리
            company=company_name,
            candidate_k=50,
            filters=client_filters,
            min_score=0.0
        )

        return JsonResponse({
            'success': True,
            'results': results,
            'searched_company': company_name,
            'total_results': len(results)
        })

    # GET: 페이지 렌더
    processor = EnhancedPDFProcessor()
    company_stats = processor.get_company_statistics()
    context = {
        'company_stats': company_stats,
        'insurance_companies': processor.insurance_companies
    }
    return render(request, 'insurance_app/recommendation.html', context)

@csrf_exempt
@require_http_methods(["POST"])
def insurance_clause_search(request: HttpRequest) -> JsonResponse:
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'success': False, 'error': '잘못된 요청 본문입니다.'}, status=400)

    query: str = data.get("query", "").strip()
    company: Optional[str] = data.get("company", None)
    client_filters: Optional[Dict[str, Any]] = data.get('filters', None)

    if not query:
        return JsonResponse({'success': False, 'error': '검색어를 입력해주세요.'}, status=400)

    results = retrieve_insurance_clauses(
        query=query,
        top_k=30,
        company=company,
        candidate_k=50,
        filters=client_filters,
        min_score=0.0
    )
    return JsonResponse({"success": True, "results": results})

@csrf_exempt
@require_http_methods(["POST"])
def insurance_clause_qa(request: HttpRequest) -> JsonResponse:
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'success': False, 'error': '잘못된 요청 본문입니다.'}, status=400)

    question: str = data.get("question", "").strip()
    company: Optional[str] = data.get("company", None)
    client_filters: Optional[Dict[str, Any]] = data.get('filters', None)

    if not question:
        return JsonResponse({'success': False, 'error': '질문을 입력해주세요.'}, status=400)

    matches = retrieve_insurance_clauses(
        query=question,
        top_k=20,
        company=company,
        candidate_k=40,
        filters=client_filters,
        min_score=0.0
    )

    # 간단 컨텍스트 (상위 5개)
    top_for_llm = matches[:5]
    llm_context = "\n".join([
        f"[{m.get('company','')}] {m.get('file','')} p.{m.get('page','')}\n{(m.get('text','') or '')[:300]}..."
        for m in top_for_llm
    ])
    prompt = f"""
질문: {question}

다음은 관련성이 높은 약관 발췌입니다:

{llm_context}

위 근거를 바탕으로, 질문에 정확하고 간결하게 답변해 주세요.
불확실하거나 예외/조건이 있으면 명확히 적어 주세요.
"""

    return JsonResponse({
        "success": True,
        "llm_prompt": prompt.strip(),
        "top_matches": matches
    })

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
