# insurance_app/urls.py
from django.urls import path
from . import views

app_name = "insurance_app"  # ★ 추가

urlpatterns = [
    path('', views.home, name='home'),
    path('signup/', views.signup, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('mypage/', views.mypage, name='mypage'),

    # 추천 페이지 / API
    path('recommend/', views.recommend_insurance, name='recommend_insurance'),

    # 챗봇 RAG 페이지 + API
    path('insurance-recommendation/', views.insurance_recommendation, name='insurance_recommendation'),

    # 용어 사전
    path('glossary/', views.glossary, name='glossary'),
    path('api/glossary', views.glossary_api, name='glossary_api'),
]
