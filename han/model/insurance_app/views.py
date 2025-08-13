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
from .pinecone_search_fault import retrieve_fault_ratio
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


@require_http_methods(["POST"])
def chatbot_ask(request):
    """
    대화형 과실비율 상담:
    입력: { "messages": [{"role":"user"|"assistant","content":"..."}] }
    """
    try:
        data = json.loads(request.body)
        messages = data.get("messages", [])
        if not messages:
            return JsonResponse({"success": False, "error": "messages가 비어있습니다."}, status=400)

        # 마지막 사용자 메시지
        last_user_msg = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                last_user_msg = m.get("content", "").strip()
                break
        if not last_user_msg:
            return JsonResponse({"success": False, "error": "user 메시지가 없습니다."}, status=400)

        # 1) Pinecone 검색
        results = retrieve_fault_ratio(last_user_msg, top_k=10)  # 상위 10
        top3 = results[:3]
        context_str = ""
        for i, r in enumerate(top3, 1):
            context_str += (
                f"[{i}] score={r['score']:.4f} file={r.get('file','')} page={r.get('page','')}\n"
                f"{(r.get('text') or r.get('chunk') or '')[:450]}\n\n"
            )

        # 2) LLM 호출 준비
        if not settings.OPENAI_API_KEY:
            return JsonResponse({"success": False, "error": "OpenAI API Key 미설정"}, status=500)
        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        history_text = ""
        for m in messages[-10:]:  # 최근 10턴만 압축
            role = m.get("role", "user")
            content = m.get("content", "")
            history_text += f"{role.upper()}: {content}\n"

        scenario_guide = """
사고 시나리오 예:
- 정차 중 후방추돌: 정차 사유(신호/정체/주차 등), 급정차 여부, 감속 정도, 정차 지속시간
- 우회전 보행자 사고: 우회전 신호 유무/상태, 보행자 신호, 일시정지 여부, 속도, 주/야간
- 차선변경/끼어들기: 방향지시등, 안전거리, 상대차의 위치, 속도 차이, 서행/급차선변경 여부
- 교차로 직진/좌우회전 충돌: 신호 현시, 선진입 여부, 속도, 시야, 우선순위
"""
        top1 = results[0]["score"] if results else 0.0
        heuristic_hint = "low_score" if top1 < 0.70 else "ok_score"

        system_prompt = (
            "너는 자동차 사고 과실비율 상담 챗봇이다. "
            "대화 내역과 검색된 근거를 바탕으로 사용자가 원하는 답으로 안내한다. "
            "반드시 JSON만 반환한다."
        )

        user_prompt = f"""
[대화 내역]
{history_text}

[현재 사용자 질문]
{last_user_msg}

[검색 상위3 근거]
{context_str}

[시나리오 가이드]
{scenario_guide}

요구사항:
1) 질문이 모호하면 need_more=true 로 설정하고, 사용자가 즉시 답할 수 있는 추가질문 1~2개를 'clarifying_questions'에 한국어로 제시.
    - 질문은 짧고 구체적으로. 선택지 유도 OK(예: "급정차였나요, 서서히 정차였나요?")
2) 질문이 충분히 구체적이면 need_more=false 로 설정하고 'final_answer'에 과실비율 판단 논리를 근거와 함께 자세히 제시.
3) 매 턴 'representative_answer'에는 2~3문장으로 간단 요약을 제공.
4) 'examples'에는 유사 사례/판단 포인트 1~3개를 짧게 bullet형 문장으로 제공.
5) JSON 키만 사용하고 그 외 텍스트 금지.
6) 휴리스틱 힌트: {heuristic_hint}

반환 JSON 스키마:
{{
    "need_more": true|false,
    "clarifying_questions": ["...", "..."],
    "representative_answer": "...",
    "examples": ["...", "..."],
    "final_answer": "..."   // need_more=true이면 빈 문자열
}}
"""
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=900,
        )
        content = resp.choices[0].message.content.strip()

        # JSON 파싱
        try:
            llm_json = json.loads(content)
        except Exception:
            llm_json = {
                "need_more": True,
                "clarifying_questions": ["사고 상황을 조금 더 구체적으로 알려주세요."],
                "representative_answer": "현재 질문만으로는 판단이 어려워 추가 정보가 필요합니다.",
                "examples": [],
                "final_answer": ""
            }

        # 3) 상위 3개 간단 요약(유사도/출처/요약문)
        top_matches_payload = []
        for r in top3:
            text = (r.get("text") or r.get("chunk") or "").replace("\n", " ")
            snippet = text[:200] + ("..." if len(text) > 200 else "")
            top_matches_payload.append({
                "score": f"{r['score'] * 100:.1f}%",
                "file": r.get("file", ""),
                "page": r.get("page", ""),
                "snippet": snippet
            })

        return JsonResponse({
            "success": True,
            "need_more": bool(llm_json.get("need_more", True)),
            "clarifying_questions": llm_json.get("clarifying_questions", [])[:2],
            "representative_answer": llm_json.get("representative_answer", ""),
            "examples": llm_json.get("examples", [])[:3],
            "final_answer": llm_json.get("final_answer", ""),
            "top_matches": top_matches_payload
        })

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


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
