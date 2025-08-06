"""
Insurance 앱 URL 설정
RAG 시스템 및 보험 추천 시스템을 위한 URL 패턴
"""

from django.urls import path
from . import views

app_name = "insurance"

urlpatterns = [
    # 메인 페이지
    path("", views.main_page, name="main_page"),
    # 개인화 챗봇
    path("personalized-chat/", views.personalized_chat, name="personalized_chat"),
    # RAG 시스템 API
    path("api/rag/search/", views.search_documents_api, name="search_documents_api"),
    path("api/rag/chat/", views.chat_api, name="chat_api"),
    path("api/rag/stats/", views.get_index_stats_api, name="get_index_stats_api"),
    # 관리자 전용 URL 패턴
    path("admin/upload/", views.admin_upload_document, name="admin_upload_document"),
    path("admin/documents/", views.admin_document_list, name="admin_document_list"),
    path(
        "admin/pinecone/",
        views.admin_pinecone_management,
        name="admin_pinecone_management",
    ),
]
