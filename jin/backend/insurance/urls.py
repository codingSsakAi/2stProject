"""
Insurance 앱 URL 설정
RAG 시스템 및 LangChain API 엔드포인트를 정의합니다.
"""

from django.urls import path
from . import views
from . import langchain_views
from . import langchain_dashboard

app_name = 'insurance'

urlpatterns = [
    # RAG 시스템 API
    path('api/search/', views.search_documents_api, name='search_documents_api'),
    path('api/generate/', views.generate_response_api, name='generate_response_api'),
    path('api/chat/', views.chat_api, name='chat_api'),
    path('api/stats/', views.get_index_stats_api, name='get_index_stats_api'),
    path('api/upload/', views.upload_document_api, name='upload_document_api'),
    path('api/delete/', views.delete_document_api, name='delete_document_api'),
    
    # LangChain + LLM API
    path('api/langchain/chat/', langchain_views.chat_with_agent, name='langchain_chat'),
    path('api/langchain/history/', langchain_views.get_conversation_history, name='conversation_history'),
    path('api/langchain/clear-memory/', langchain_views.clear_conversation_memory, name='clear_memory'),
    path('api/langchain/status/', langchain_views.get_service_status, name='service_status'),
    path('api/langchain/recommendation/', langchain_views.generate_insurance_recommendation, name='insurance_recommendation'),
    path('api/langchain/search-documents/', langchain_views.search_insurance_documents, name='search_documents_langchain'),
    path('api/langchain/company-info/', langchain_views.get_insurance_company_info, name='company_info'),
    path('api/langchain/compare-products/', langchain_views.compare_insurance_products, name='compare_products'),
    path('api/langchain/test-tools/', langchain_views.test_langchain_tools, name='test_tools'),
    
    # LangChain 대시보드
    path('langchain-dashboard/', langchain_dashboard.langchain_dashboard, name='langchain_dashboard'),
    path('langchain-dashboard/chat/', langchain_dashboard.langchain_chat_ajax, name='langchain_chat_ajax'),
    path('langchain-dashboard/tool-test/', langchain_dashboard.langchain_tool_test_ajax, name='langchain_tool_test_ajax'),
    path('langchain-dashboard/memory/', langchain_dashboard.langchain_memory_ajax, name='langchain_memory_ajax'),
    path('langchain-dashboard/status/', langchain_dashboard.langchain_status_ajax, name='langchain_status_ajax'),
    
    # RAG 대시보드
    path('rag-dashboard/', views.rag_dashboard, name='rag_dashboard'),
] 