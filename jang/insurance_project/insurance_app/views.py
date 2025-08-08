from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from .models import CustomUser
from .forms import CustomUserCreationForm
from .pdf_processor import EnhancedPDFProcessor
from .pinecone_search import retrieve_insurance_clauses
import json
from django.views.decorators.http import require_http_methods
from .insurance_mock_server import InsuranceService
from .forms import UserProfileChangeForm, EmailPasswordChangeForm

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

@csrf_exempt
def get_company_detail(request, company_name):
    try:
        return JsonResponse({"company_name": company_name, "detail": f"{company_name} 보험사 상세 정보"})
    except Exception as e:
        return JsonResponse({
            'error': f'보험사 정보 조회 중 오류: {str(e)}'
        }, status=500)

def get_market_analysis(request):
    return JsonResponse({
        "market_summary": "자동차보험 시장 동향 및 보험사별 경쟁력 분석 예시"
    })

def clause_summary(request, clause_id):
    return JsonResponse({
        'success': True,
        'clause_id': clause_id,
        'summary': f'약관 {clause_id}번에 대한 요약입니다.'
    })

### --- [핵심 필터 함수] --- ###
def filter_results_by_keyword_and_company(results, keywords, max_per_company=1):
    """
    회사별로 keyword가 들어간 대표 청크(max_per_company개)만 반환
    """
    keyword_filtered = []
    for r in results:
        text = r.get("text", "") or r.get("chunk", "") or r.get("metadata", {}).get("text", "")
        if any(k in text for k in keywords):
            keyword_filtered.append(r)
    company_counts = {}
    final_results = []
    for r in keyword_filtered:
        company = r.get("company", "") or r.get("metadata", {}).get("company", "")
        if not company:
            continue
        if company not in company_counts:
            company_counts[company] = 0
        if company_counts[company] < max_per_company:
            final_results.append(r)
            company_counts[company] += 1
    return final_results
### ----------------------- ###

@csrf_exempt
def insurance_recommendation(request):
    """AI 기반 보험 약관 검색 (Pinecone 검색 사용)"""
    if request.method == 'POST':
        data = json.loads(request.body)
        query = data.get('query', '')
        company_name = data.get('company', None)

        if query:
            # 넉넉히 top_k 받아와서 후처리(중복/키워드)
            results = retrieve_insurance_clauses(query, top_k=30, company=company_name)
            keywords = ['면책', '보상하지 않는 손해', '지급하지 않는다', '보상하지', '제외', '면책사항']
            filtered_results = filter_results_by_keyword_and_company(results, keywords, max_per_company=1)
            return JsonResponse({
                'success': True,
                'results': filtered_results,
                'searched_company': company_name,
                'total_results': len(filtered_results)
            })
        else:
            return JsonResponse({
                'success': False,
                'error': '검색어를 입력해주세요.'
            })

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
    data = json.loads(request.body)
    query = data.get("query", "")
    company = data.get("company", None)
    results = retrieve_insurance_clauses(query, top_k=30, company=company)
    keywords = ['면책', '보상하지 않는 손해', '지급하지 않는다', '보상하지', '제외', '면책사항']
    filtered_results = filter_results_by_keyword_and_company(results, keywords, max_per_company=1)
    return JsonResponse({"success": True, "results": filtered_results})

@csrf_exempt
@require_http_methods(["POST"])
def insurance_clause_qa(request):
    data = json.loads(request.body)
    question = data.get("question", "")
    company = data.get("company", None)
    top_matches = retrieve_insurance_clauses(question, top_k=30, company=company)
    keywords = ['면책', '보상하지 않는 손해', '지급하지 않는다', '보상하지', '제외', '면책사항']
    filtered_matches = filter_results_by_keyword_and_company(top_matches, keywords, max_per_company=1)
    llm_context = "\n".join([
        f"[{m['company']}] {m['file']} p.{m['page']}\n{m.get('text', m.get('chunk', ''))[:200]}..."
        for m in filtered_matches
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
        "top_matches": filtered_matches
    })

def logout_view(request):
    if request.method == 'POST':
        storage = messages.get_messages(request)
        for message in storage:
            pass
        storage.used = True
        logout(request)
        return redirect('login')
    return redirect('home')

@login_required
def mypage(request):
    if request.method == "POST":
        form = EmailPasswordChangeForm(request.POST, user=request.user, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "회원정보가 수정되었습니다.")
            return redirect('mypage')
    else:
        form = EmailPasswordChangeForm(user=request.user, instance=request.user)
    return render(request, 'insurance_app/mypage.html', {'form': form})
