# insurance_portal/urls.py
# 기능별 뷰를 모듈로 분리해 가져옵니다.
from django.urls import path
from .views import chatbot, weekly, guide, claim_knowledge

urlpatterns = [
    # [과실 챗봇] UI 페이지 (기존 recommendation 화면)
    # - 템플릿: insurance_portal/recommendation.html
    # - 내부에서 _chatbot.html 등 조각을 include
    path(
        "portal/", 
        chatbot.recommendation_view, 
        name="portal_home"
        ),

    # [과실 챗봇] 질의응답 API
    # - 프런트에서 fetch로 호출
    # - Pinecone 검색 + LLM 생성 후 최종 링크를 답변 끝에만 추가
    path(
        "api/fault-chatbot/",
        chatbot.fault_chatbot_api,
        name="fault_chatbot_api",
    ),

    # [보험상식] 모달/페이지 진입
    # - 템플릿 조각: insurance_portal/_weekly.html
    # - recommendation.html에서 include로 사용 가능
    path(
        "weekly/",
        weekly.weekly_modal_view,
        name="weekly",
    ),

    # [보험상식] 목록 데이터 API
    # - 데이터 소스: insurance_portal/data/weekly_articles.json
    path(
        "api/weekly/list/",
        weekly.weekly_list_api,
        name="weekly_list_api",
    ),

    # [사고 처리 가이드] 모달/페이지 진입
    # - 템플릿 조각: insurance_portal/_guide.html
    path(
        "guide/",
        guide.modal_view,
        name="guide",
    ),

    # [사고 처리 가이드] 단계 목록 API
    # - 데이터 소스가 있다면 utils.loaders로 로드
    path(
        "api/guide/steps/",
        guide.steps_api,
        name="guide_steps_api",
    ),

    # [보상상식] 모달/페이지 진입
    # - 템플릿 조각: insurance_portal/_claim_knowledge.html
    path(
        "claim-knowledge/",
        claim_knowledge.modal_view,
        name="claim_knowledge",
    ),

    # [보상상식] 목록 데이터 API
    # - 데이터 소스: insurance_portal/data/merged_cases.json 등
    path(
        "api/claim-knowledge/list/",
        claim_knowledge.list_api,
        name="claim_knowledge_list_api",
    ),
]
