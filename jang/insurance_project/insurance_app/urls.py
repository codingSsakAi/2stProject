from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path('', views.home, name='home'),
    path('signup/', views.signup, name='signup'),
    path('login/', views.login_view, name='login'),
    path('recommend/', views.recommend_insurance, name='recommend_insurance'),
    path('clause-summary/<int:clause_id>/', views.clause_summary, name='clause_summary'),
    path('insurance-recommendation/', views.insurance_recommendation, name='insurance_recommendation'),
    path('company-detail/<str:company_name>/', views.get_company_detail, name='company_detail'),  # 추가
    path('market-analysis/', views.get_market_analysis, name='market_analysis'),  # 추가
    path('api/search/', views.insurance_clause_search, name='insurance_clause_search'),
    path('api/qa/', views.insurance_clause_qa, name='insurance_clause_qa'),
    path('logout/', LogoutView.as_view(next_page='home'), name='logout'),
]