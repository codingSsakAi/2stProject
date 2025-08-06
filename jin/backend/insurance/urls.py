"""
Insurance 앱 URL 설정
RAG 시스템 및 LangChain API 엔드포인트를 정의합니다.
"""

from django.urls import path
from . import views
from . import langchain_views
from . import langchain_dashboard
from . import ml_views
from . import ml_dashboard

app_name = "insurance"

urlpatterns = [
    # RAG 시스템 API
    path("api/rag/search/", views.search_documents_api, name="search_documents_api"),
    path(
        "api/rag/generate/", views.generate_response_api, name="generate_response_api"
    ),
    path("api/rag/chat/", views.chat_api, name="chat_api"),
    path("api/rag/stats/", views.get_index_stats_api, name="get_index_stats_api"),
    path("api/rag/upload/", views.upload_document_api, name="upload_document_api"),
    path("api/rag/delete/", views.delete_document_api, name="delete_document_api"),
    # LangChain + LLM API
    path("api/langchain/chat/", langchain_views.chat_with_agent, name="langchain_chat"),
    path(
        "api/langchain/history/",
        langchain_views.get_conversation_history,
        name="conversation_history",
    ),
    path(
        "api/langchain/clear-memory/",
        langchain_views.clear_conversation_memory,
        name="clear_memory",
    ),
    path(
        "api/langchain/status/",
        langchain_views.get_service_status,
        name="service_status",
    ),
    path(
        "api/langchain/recommendation/",
        langchain_views.generate_insurance_recommendation,
        name="insurance_recommendation",
    ),
    path(
        "api/langchain/search-documents/",
        langchain_views.search_insurance_documents,
        name="search_documents_langchain",
    ),
    path(
        "api/langchain/company-info/",
        langchain_views.get_insurance_company_info,
        name="company_info",
    ),
    path(
        "api/langchain/compare-products/",
        langchain_views.compare_insurance_products,
        name="compare_products",
    ),
    path(
        "api/langchain/test-tools/",
        langchain_views.test_langchain_tools,
        name="test_tools",
    ),
    # 개인화 추천 API
    path(
        "api/langchain/personalized-recommendation/",
        langchain_views.generate_personalized_recommendation,
        name="personalized_recommendation",
    ),
    path(
        "api/langchain/risk-analysis/",
        langchain_views.analyze_user_risk_profile,
        name="risk_analysis",
    ),
    path(
        "api/langchain/smart-suggestions/",
        langchain_views.get_smart_insurance_suggestions,
        name="smart_suggestions",
    ),
    path(
        "api/langchain/update-preferences/",
        langchain_views.update_user_preferences,
        name="update_preferences",
    ),
    # ML 추천 시스템 API
    path(
        "api/ml/generate/",
        ml_views.generate_ml_recommendations,
        name="generate_ml_recommendations",
    ),
    path(
        "api/ml/history/",
        ml_views.get_recommendation_history,
        name="get_recommendation_history",
    ),
    path(
        "api/ml/feedback/",
        ml_views.update_recommendation_feedback,
        name="update_recommendation_feedback",
    ),
    path(
        "api/ml/stats/",
        ml_views.get_recommendation_stats,
        name="get_recommendation_stats",
    ),
    path(
        "api/ml/collaborative/",
        ml_views.get_collaborative_recommendations,
        name="get_collaborative_recommendations",
    ),
    path(
        "api/ml/content-based/",
        ml_views.get_content_based_recommendations,
        name="get_content_based_recommendations",
    ),
    path(
        "api/ml/hybrid/",
        ml_views.get_hybrid_recommendations,
        name="get_hybrid_recommendations",
    ),
    path(
        "api/ml/sample-data/",
        ml_views.create_sample_user_data,
        name="create_sample_user_data",
    ),
    path("api/ml/profiles/", ml_views.get_user_profiles, name="get_user_profiles"),
    path("api/ml/test/", ml_views.test_ml_models, name="test_ml_models"),
    # 새로운 ML API 엔드포인트들
    path(
        "api/ml/performance/",
        ml_views.get_model_performance,
        name="get_model_performance",
    ),
    path(
        "api/ml/retrain/",
        ml_views.retrain_ml_models,
        name="retrain_ml_models",
    ),
    path(
        "api/ml/cluster-info/",
        ml_views.get_user_cluster_info,
        name="get_user_cluster_info",
    ),
    path(
        "api/ml/personalized/",
        ml_views.get_personalized_recommendations,
        name="get_personalized_recommendations",
    ),
    path(
        "api/ml/update-preference/",
        ml_views.update_user_preference,
        name="update_user_preference",
    ),
    path(
        "api/ml/analytics/",
        ml_views.get_recommendation_analytics,
        name="get_recommendation_analytics",
    ),
    # LangChain 대시보드
    path(
        "langchain-dashboard/",
        langchain_dashboard.langchain_dashboard,
        name="langchain_dashboard",
    ),
    path(
        "langchain-dashboard/chat/",
        langchain_dashboard.langchain_chat_ajax,
        name="langchain_chat_ajax",
    ),
    path(
        "langchain-dashboard/tool-test/",
        langchain_dashboard.langchain_tool_test_ajax,
        name="langchain_tool_test_ajax",
    ),
    path(
        "langchain-dashboard/memory/",
        langchain_dashboard.langchain_memory_ajax,
        name="langchain_memory_ajax",
    ),
    path(
        "langchain-dashboard/status/",
        langchain_dashboard.langchain_status_ajax,
        name="langchain_status_ajax",
    ),
    # ML 대시보드
    path("ml-dashboard/", ml_dashboard.ml_dashboard, name="ml_dashboard"),
    path(
        "ml-dashboard/ajax/", ml_dashboard.ml_dashboard_ajax, name="ml_dashboard_ajax"
    ),
    path(
        "ml-dashboard/stats/",
        ml_dashboard.ml_dashboard_stats_ajax,
        name="ml_dashboard_stats_ajax",
    ),
    # RAG 대시보드
    path("rag-dashboard/", views.rag_dashboard, name="rag_dashboard"),
    # 프론트엔드 페이지들
    path("", views.main_page, name="main_page"),
    path("compare/", views.compare_insurance, name="compare_insurance"),
    path("about/", views.about_page, name="about_page"),
    path("personalized-chat/", views.personalized_chat, name="personalized_chat"),

    # 관리자 전용 URL 패턴
    path('admin/upload/', views.admin_upload_document, name='admin_upload_document'),
    path('admin/multiple-upload/', views.admin_multiple_upload_document, name='admin_multiple_upload_document'),
    path('admin/documents/', views.admin_document_list, name='admin_document_list'),
    path('admin/pinecone/', views.admin_pinecone_management, name='admin_pinecone_management'),

    # Pinecone 관리 API
    path('api/pinecone/update-company/', views.update_company_index, name='update_company_index'),
    path('api/pinecone/delete-company/', views.delete_company_data, name='delete_company_data'),
    path('api/pinecone/update-all/', views.update_all_index, name='update_all_index'),
    path('api/pinecone/clear-all/', views.clear_all_index, name='clear_all_index'),
    path('api/pinecone/stats/', views.get_pinecone_stats, name='get_pinecone_stats'),

    # 문서 관리 API
    path('api/documents/<int:document_id>/delete/', views.delete_document_api, name='delete_document_api'),
    path('api/documents/search/', views.search_documents_api, name='search_documents_api'),
]
