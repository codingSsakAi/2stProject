from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.conf import settings

import os
import json

from .models import CustomUser
from .forms import CustomUserCreationForm
from .pdf_processor import EnhancedPDFProcessor
from .pinecone_search import retrieve_insurance_clauses
from .insurance_mock_server import InsuranceService
from openai import OpenAI


def home(request):
    return render(request, 'insurance_app/home.html')


def signup(request):
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


def login_view(request):
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
def recommend_insurance(request):
    if request.method == 'POST':
        try:
            # FormData에서 값 추출 (user model의 필드 직접 접근, 없는 건 default)
            user_profile = {
                'birth_date': str(getattr(request.user, 'birth_date', '1990-01-01')),
                'gender': getattr(request.user, 'gender', 'M'),
                'residence_area': request.POST.get('region', '서울'),
                'driving_experience': int(request.POST.get('driving_experience', 5)),
                'accident_history': int(request.POST.get('accident_history', 0)),
                'annual_mileage': int(request.POST.get('annual_mileage', 12000)),
                'car_info': {'type': request.POST.get('car_type', '준중형')},
                'coverage_level': request.POST.get('coverage_level', '표준')
            }
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


@require_http_methods(["GET"])
def get_company_detail(request, company_name):
    # 실제 구현 시 Pinecone 메타 또는 DB에서 상세 추출 가능
    try:
        return JsonResponse({"company_name": company_name, "detail": f"{company_name} 보험사 상세 정보"})
    except Exception as e:
        return JsonResponse({'error': f'보험사 정보 조회 중 오류: {str(e)}'}, status=500)


@require_http_methods(["GET"])
def get_market_analysis(request):
    # 메타데이터 기반 보험 시장 분석 반환 (예시)
    return JsonResponse({"market_summary": "자동차보험 시장 동향 및 보험사별 경쟁력 분석 예시"})


@require_http_methods(["GET"])
def clause_summary(request, clause_id):
    # Pinecone에서 clause_id로 벡터/메타 추출해 요약 반환 가능(예시)
    return JsonResponse({'success': True, 'clause_id': clause_id, 'summary': f'약관 {clause_id}번에 대한 요약입니다.'})


@require_http_methods(["GET", "POST"])
def insurance_recommendation(request):
    """
    GET  : recommendation.html 렌더(회사 통계 등)
    POST : 약관 검색 API (통합 엔드포인트)
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            query = data.get('query', '').strip()
            company_name = data.get('company')
            if not query:
                return JsonResponse({'success': False, 'error': '검색어를 입력해주세요.'}, status=400)

            results = retrieve_insurance_clauses(query, top_k=5, company=company_name)
            return JsonResponse({
                'success': True,
                'results': results,
                'searched_company': company_name,
                'total_results': len(results)
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    # GET
    processor = EnhancedPDFProcessor()
    company_stats = processor.get_company_statistics()
    context = {
        'company_stats': company_stats,
        'insurance_companies': processor.insurance_companies
    }
    return render(request, 'insurance_app/recommendation.html', context)
