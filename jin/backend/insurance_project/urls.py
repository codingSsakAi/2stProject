"""
Insurance Project URL 설정
메인 프로젝트 URL 패턴을 정의합니다.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from insurance.views import main_page

urlpatterns = [
    # 메인 페이지
    path("", main_page, name="main_page"),
    # 관리자 페이지
    path("admin/", admin.site.urls),
    # Insurance 앱 URL
    path("insurance/", include("insurance.urls")),
]

# 개발 환경에서 미디어 파일 서빙
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
