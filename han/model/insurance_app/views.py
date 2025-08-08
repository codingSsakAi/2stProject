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
from .insurance_mock_server import InsuranceService
from .pinecone_search_fault import retrieve_fault_ratio
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import os

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
        import json
        from openai import OpenAI
        
        data = json.loads(request.body)
        query = data.get('query', '')
        
        if not query:
            return JsonResponse({'success': False, 'error': '검색어를 입력해주세요.'})
        
        try:
            # Pinecone에서 상위 10개 결과 검색
            results = retrieve_fault_ratio(query, top_k=10)
            
            if not results:
                return JsonResponse({'success': False, 'error': '관련 근거를 찾지 못했습니다.'})

            # 상위 3개 결과만 선택 (이미 유사도 순으로 정렬됨)
            top_3_results = results[:3]
            
            # 상위 3개 결과를 컨텍스트로 구성
            context_str = ""
            for i, match in enumerate(top_3_results):
                context_str += f"""
{i+1}번째 근거 (유사도: {match['score']:.4f})
파일: {match['file']}
페이지: {match['page']}
내용: {match['text']}

"""
            
            # OpenAI GPT-4o-mini를 사용하여 AI 요약 생성
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            
            prompt = f"""
다음은 자동차 사고 과실비율과 관련된 검색 결과입니다.

사용자 질문: "{query}"

검색된 근거 자료:
{context_str}

위 검색 결과를 바탕으로 다음 요구사항에 맞게 답변해 주세요:
1. 사용자의 질문에 대한 명확하고 이해하기 쉬운 답변을 제공
2. 각 근거 자료의 유사도 점수와 출처 정보는 무슨 법 몇조에 해당 되는지와 해당 내용은 뭔지 설명
3. 과실비율에 대한 구체적인 정보가 있다면 명시
4. 추가 주의사항이나 예외사항이 있다면 언급
5. 해당 되는 법과 몇 조인지 근거 자료 제일 처음에 문단에 명시
6. 근거 자료의 내용에는 해당 되는 내용과 해당 내용의 과실 비율이 왜 그렇게 나왔는지 설명
7. 근저 자료에 표가 있으면 표는 표 구조를 유지한체 보여주고, 표 내용은 정보를 출력

답변 형식:
## 과실비율 분석 결과

**질문에 대한 답변:**
[여기에 명확한 답변]

**근거 자료:**
[각 근거별로 유사도와 함께 정리]

**주의사항:**
[추가 고려사항이나 제한사항]
"""
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "당신은 자동차 보험 과실비율 전문가입니다. 제공된 자료를 바탕으로 정확하고 이해하기 쉬운 답변을 제공해주세요."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,
                temperature=0.3
            )
            
            ai_summary = response.choices[0].message.content
            
            return JsonResponse({
                'success': True,
                'query': query,
                'ai_summary': ai_summary,
                'top_matches': [
                    {
                        'score': f"{match['score']:.4f}",
                        'similarity_percentage': f"{match['score'] * 100:.1f}%",
                        'file': match['file'],
                        'page': match['page'],
                        'text': match['text'][:300] + "..." if len(match['text']) > 300 else match['text'],
                        'full_text': match['text']
                    } for match in top_3_results
                ],
                'total_searched': len(results)
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False, 
                'error': f'검색 중 오류가 발생했습니다: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'error': 'POST 요청만 지원합니다.'})

def weekly_articles(request):
    # JSON 경로는 앱 내부를 기준으로
    json_path = os.path.join(os.path.dirname(__file__), 'weekly_articles.json')
    try:
        with open(json_path, encoding='utf-8') as f:
            articles = json.load(f)
    except Exception:
        articles = []

    return render(request, 'insurance_app/weekly.html', {'articles': articles})

def weekly_articles_partial(request):
    json_path = os.path.join(os.path.dirname(__file__), 'weekly_articles.json')
    try:
        with open(json_path, encoding='utf-8') as f:
            articles = json.load(f)
    except Exception:
        articles = []
    return render(request, 'insurance_app/weekly_partial.html', {'articles': articles})