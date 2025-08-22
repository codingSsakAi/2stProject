# insurance_project/urls.py
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve as static_serve
from pathlib import Path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('insurance_app.urls')),
]

# 개발환경에서만 미디어 제공
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# 약관 PDF 전용 정적 서빙 (/documents/회사/회사.pdf)
BASE_DIR = Path(__file__).resolve().parent.parent
DOCS_ROOT = BASE_DIR / 'insurance_app' / 'documents'
urlpatterns += [
    re_path(r'^documents/(?P<path>.*)$', static_serve, {'document_root': str(DOCS_ROOT)}),
]
