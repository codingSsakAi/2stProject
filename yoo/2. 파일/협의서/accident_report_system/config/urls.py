from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from report_form.views import generate_report

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('report_form.urls')),
    path("", generate_report, name="generate_report"),  # form POST/GET 모두 처리,
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
