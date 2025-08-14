from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),

    # 계정/페이지
    path('signup/', views.signup, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('mypage/', views.mypage, name='mypage'),
    path('recommend/', views.recommend_insurance, name='recommend_insurance'),

    # 검색/추천 및 보조 API
    path('insurance-recommendation/', views.insurance_recommendation, name='insurance_recommendation'),
    # path('company-detail/<str:company_name>/', views.get_company_detail, name='company_detail'),
    # path('market-analysis/', views.get_market_analysis, name='market_analysis'),
    # path('clause-summary/<int:clause_id>/', views.clause_summary, name='clause_summary'),

    # # 기존 API 유지
    # path('api/search/', views.insurance_clause_search, name='insurance_clause_search'),
    # path('api/qa/', views.insurance_clause_qa, name='insurance_clause_qa'),
]
