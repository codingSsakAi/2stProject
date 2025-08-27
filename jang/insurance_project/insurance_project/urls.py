from django.contrib import admin
from django.urls import include, path, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve as static_serve

# 기존 insurance_app 뷰 바로 연결(비네임스페이스)
from insurance_app import views as app_views

urlpatterns = [
    # 메인
    path("", app_views.home, name="home"),
    path("signup/", app_views.signup, name="signup"),
    path("login/", app_views.login_view, name="login"),
    path("logout/", app_views.logout_view, name="logout"),
    path("mypage/", app_views.mypage, name="mypage"),
    path("recommend/", app_views.recommend_insurance, name="recommend_insurance"),
    path("insurance-recommendation/", app_views.insurance_recommendation, name="insurance_recommendation"),
    path("glossary/", app_views.glossary, name="glossary"),
    path("api/glossary", app_views.glossary_api, name="glossary_api"),

    # 네임스페이스 버전 유지
    path("", include(("insurance_app.urls", "insurance_app"), namespace="insurance_app")),

    # 사고/협의서
    path("accident/", include(("accident_project.urls", "accident_project"), namespace="accident_project")),

    path("admin/", admin.site.urls),
]

# 개발 편의: 업로드/미디어
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# 문서(PDF) 서빙
urlpatterns += [
    re_path(
        r"^documents/(?P<path>.*)$",
        static_serve,
        {"document_root": settings.DOCUMENTS_ROOT},
        name="documents_serve",
    ),
]

# ★ 정적 포털 자산 404 방지(하이픈 경로 직접 매핑)
# /static/insurance_portal/** 를 0826-5/insurance-portal/static 에서 강제 서빙
_portal_static_root = settings.BASE_DIR / "0826-5" / "insurance-portal" / "static"
if _portal_static_root.exists() and settings.DEBUG:
    urlpatterns += [
        re_path(
            r"^static/insurance_portal/(?P<path>.*)$",
            static_serve,
            {"document_root": _portal_static_root / "insurance_portal"},
        ),
    ]
_portal_static_root = settings.BASE_DIR / "0826-5" / "insurance_portal" / "static" / "insurance_portal"
if _portal_static_root.exists() and settings.DEBUG:
    urlpatterns += [
        re_path(
            r"^static/insurance_portal/(?P<path>.*)$",
            static_serve,
            {"document_root": _portal_static_root},
        ),
    ]