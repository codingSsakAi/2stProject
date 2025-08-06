from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from .models import CustomUser
from .forms import CustomUserCreationForm
from .pdf_processor import EnhancedPDFProcessor
from .pinecone_search import retrieve_insurance_clauses   # Pinecone 연동 함수
import json
from django.views.decorators.http import require_http_methods
from .pinecone_search import retrieve_insurance_clauses
from .pinecone_search_fault import retrieve_fault_ratio


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
    """보험 추천 폼 페이지 (실제 추천은 별도 API)"""
    if request.method == 'POST':
        # 보험 추천 API가 아니라, 보험 추천 폼일 경우만 사용
        pass
    context = {
        'user': request.user,
        'car_types': ['경차', '소형', '준중형', '중형', '대형', 'SUV'],
        'regions': ['서울', '부산', '대구', '인천', '광주', '대전', '울산', '기타'],
        'coverage_levels': ['기본', '표준', '고급', '프리미엄']
    }
    return render(request, 'insurance_app/recommend.html', context)

@csrf_exempt
def get_company_detail(request, company_name):
    # 실제 구현 시 Pinecone 메타 또는 DB에서 상세 추출 가능
    try:
        # 임시 예시
        return JsonResponse({"company_name": company_name, "detail": f"{company_name} 보험사 상세 정보"})
    except Exception as e:
        return JsonResponse({
            'error': f'보험사 정보 조회 중 오류: {str(e)}'
        }, status=500)

def get_market_analysis(request):
    # 마찬가지로 메타데이터 기반 보험 시장 분석 반환
    return JsonResponse({
        "market_summary": "자동차보험 시장 동향 및 보험사별 경쟁력 분석 예시"
    })

def clause_summary(request, clause_id):
    # Pinecone에서 clause_id로 벡터/메타 추출해 요약 반환 가능
    return JsonResponse({
        'success': True,
        'clause_id': clause_id,
        'summary': f'약관 {clause_id}번에 대한 요약입니다.'
    })

@csrf_exempt
def insurance_recommendation(request):
    """AI 기반 보험 약관 검색 (Pinecone 검색 사용)"""
    if request.method == 'POST':
        data = json.loads(request.body)
        query = data.get('query', '')
        company_name = data.get('company', None)
        
        if query:
            # Pinecone 실전 검색 함수로 직접 검색
            results = retrieve_insurance_clauses(query, top_k=5, company=company_name)
            # Pinecone 검색 결과를 그대로 반환
            return JsonResponse({
                'success': True,
                'results': results,
                'searched_company': company_name,
                'total_results': len(results)
            })
        else:
            return JsonResponse({
                'success': False,
                'error': '검색어를 입력해주세요.'
            })

    # GET 요청시 보험사 목록과 문서 통계 제공
    processor = EnhancedPDFProcessor()
    company_stats = processor.get_company_statistics()
    context = {
        'company_stats': company_stats,
        'insurance_companies': processor.insurance_companies
    }
    return render(request, 'insurance_app/recommendation.html', context)

@csrf_exempt
@require_http_methods(["POST"])
def insurance_clause_search(request):
    import json
    data = json.loads(request.body)
    query = data.get("query", "")
    company = data.get("company", None)
    from .pinecone_search import retrieve_insurance_clauses
    results = retrieve_insurance_clauses(query, top_k=5, company=company)
    return JsonResponse({"success": True, "results": results})

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from django.http import JsonResponse
from .pinecone_search import retrieve_insurance_clauses

@csrf_exempt
@require_http_methods(["POST"])
def insurance_clause_qa(request):
    """
    POST: { "question": "음주운전 보상 되나요?", "company": "DB손해보험" }
    → Pinecone 검색 후 LLM 컨텍스트 자동 생성 예시 (실제 LLM 연동은 아래에서 커스텀)
    """
    data = json.loads(request.body)
    question = data.get("question", "")
    company = data.get("company", None)
    top_matches = retrieve_insurance_clauses(question, top_k=3, company=company)

    # LLM 컨텍스트 예시 생성 (여기에 LLM 호출/응답도 바로 추가 가능)
    llm_context = "\n".join([
        f"[{m['company']}] {m['file']} p.{m['page']}\n{m['chunk'][:200]}..."
        for m in top_matches
    ])
    prompt = f"""
다음은 '{company or '전체'}' 보험사 약관 중 사용자의 질문과 유사한 조항입니다.

질문: {question}

--- 근거 조항 ---
{llm_context}

위 내용을 바탕으로 정확하고 쉽게 설명해 주세요. 실제 약관 내용이 불확실하거나 조건이 있다면 명시해 주세요.
"""

    return JsonResponse({
        "success": True,
        "llm_prompt": prompt,
        "top_matches": top_matches
    })

@csrf_exempt
def fault_ratio_search(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        query = data.get('query', '')
        if query:
            results = retrieve_fault_ratio(query, top_k=5)
            return JsonResponse({'success': True, 'results': results})
        else:
            return JsonResponse({'success': False, 'error': '검색어를 입력해주세요.'})
    return JsonResponse({'success': False, 'error': 'POST 요청만 지원합니다.'})
