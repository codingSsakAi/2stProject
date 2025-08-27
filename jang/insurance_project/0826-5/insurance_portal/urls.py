# insurance_portal/urls.py
# 목적: 포털 앱 전용 라우팅 정의 (주: 기존 insurance_app은 수정하지 않음)

from django.urls import path
from .views import chatbot, weekly
from .views import fault_answer_view

urlpatterns = [
    # 사고 과실 챗봇 API
    path("api/chatbot/ask/", chatbot.ask, name="portal_chatbot_ask"),     
    # 과실비율 챗봇 관련 API
    path('api/fault/answer/', fault_answer_view.fault_answer, name='fault_answer'),
    path('api/fault/navigation/', fault_answer_view.navigation_data, name='navigation_data'),
    
    # 기존 호환성을 위한 엔드포인트
    path('api/fault/ask/', fault_answer_view.ask, name='fault_ask'),

    # 보험 상식(weekly) 페이지 및 부분 렌더
    path("weekly/", weekly.page, name="portal_weekly"),
    
]