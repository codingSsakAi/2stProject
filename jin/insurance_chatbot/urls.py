"""
URL configuration for insurance_chatbot project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.shortcuts import render
import logging

# 로거 설정
logger = logging.getLogger(__name__)

def home_view(request):
    """메인 페이지 뷰 - user.is_authenticated 값 로깅"""
    logger.info(f"=== 사용자 인증 상태 확인 ===")
    logger.info(f"user: {request.user}")
    logger.info(f"user.is_authenticated: {request.user.is_authenticated}")
    logger.info(f"user.is_anonymous: {request.user.is_anonymous}")
    logger.info(f"user.id: {request.user.id if request.user.is_authenticated else 'None'}")
    logger.info(f"================================")
    
    return render(request, 'home.jinja.html')

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("chatbot/", include("chatbot.urls")),
    path("", home_view, name="home"),
]

# 개발 환경에서 미디어 파일 서빙
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
