# insurance_portal/urls.py
# 목적: 포털 앱 전용 라우팅 정의 (주: 기존 insurance_app은 수정하지 않음)

from django.urls import path
from .views import chatbot, weekly

urlpatterns = [
    # 사고 과실 챗봇 API
    path("api/chatbot/ask/", chatbot.ask, name="portal_chatbot_ask"),

    # 보험 상식(weekly) 페이지 및 부분 렌더
    path("weekly/", weekly.page, name="portal_weekly"),
    path("weekly/partial/", weekly.partial, name="portal_weekly_partial"),
]
