# ibk_pension_project/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('home.urls')),
    # 다른 앱들은 일단 주석 처리 (나중에 하나씩 추가)
    # path('accounts/', include('accounts.urls')),
    # path('insurance/', include('insurance.urls')),
    # path('guide/', include('guide.urls')),
    # path('news/', include('news.urls')),
    # path('chatbot/', include('chatbot.urls')),
    # path('common/', include('common.urls')),
]

# 개발 환경에서 정적 파일 서빙
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)