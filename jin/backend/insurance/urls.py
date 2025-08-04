"""
Insurance 앱 URL 설정
RAG 시스템 API 엔드포인트를 정의합니다.
"""

from django.urls import path
from . import views

app_name = 'insurance'

urlpatterns = [
    # RAG 시스템 API
    path('api/search/', views.search_documents_api, name='search_documents_api'),
    path('api/generate/', views.generate_response_api, name='generate_response_api'),
    path('api/chat/', views.chat_api, name='chat_api'),
    path('api/stats/', views.get_index_stats_api, name='get_index_stats_api'),
    path('api/upload/', views.upload_document_api, name='upload_document_api'),
    path('api/delete/', views.delete_document_api, name='delete_document_api'),
    
    # RAG 대시보드
    path('rag-dashboard/', views.rag_dashboard, name='rag_dashboard'),
] 