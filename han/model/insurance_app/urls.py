from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

urlpatterns = [
    path('', views.home, name='home'),

    path('signup/', views.signup, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', LogoutView.as_view(next_page='home'), name='logout'),

    # 보험료 추천(페이지/POST)
    path('recommend/', views.recommend_insurance, name='recommend_insurance'),

    # 약관 검색: GET=페이지 렌더, POST=검색 API(통합 엔드포인트)
    path('insurance-recommendation/', views.insurance_recommendation, name='insurance_recommendation'),

    # 부가 API
    path('clause-summary/<int:clause_id>/', views.clause_summary, name='clause_summary'),
    path('company-detail/<str:company_name>/', views.get_company_detail, name='company_detail'),
    path('market-analysis/', views.get_market_analysis, name='market_analysis'),
]
