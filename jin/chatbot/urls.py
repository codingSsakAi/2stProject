from django.urls import path
from . import views

app_name = 'chatbot'

urlpatterns = [
    # 메인 페이지 (채팅 페이지로 리다이렉트)
    path('', views.chat_view, name='index'),
    
    # 문서 관리 URL 패턴들
    path('documents/', views.document_list_view, name='document_list'),
    path('documents/upload/', views.document_upload_view, name='document_upload'),
    path('documents/<int:document_id>/', views.document_detail_view, name='document_detail'),
    path('documents/<int:document_id>/delete/', views.document_delete_view, name='document_delete'),
    path('documents/<int:document_id>/process/', views.document_process_view, name='document_process'),
    
    # 채팅 관련 URL 패턴들
    path('chat/', views.chat_view, name='chat'),
    path('chat/session/<int:session_id>/', views.chat_session_view, name='chat_session'),
    path('chat/session/<int:session_id>/delete/', views.chat_delete_view, name='chat_delete'),
    
    # 실시간 채팅을 위한 AJAX API
    path('api/chat/send/', views.api_send_message, name='api_send_message'),
    
    # 보험 추천 관련 API
    path('api/insurance/profile/', views.api_insurance_profile, name='api_insurance_profile'),
    path('api/insurance/profile/get/', views.api_get_insurance_profile, name='api_get_insurance_profile'),
    
    # 기타 URL 패턴들
    path('embedding_stats/', views.embedding_stats_view, name='embedding_stats'),
    path('documents/search/', views.search_documents_view, name='search_documents'),
]
