from django.urls import path
from django.views.generic import TemplateView
from .views import generate_report

urlpatterns = [
    path('', generate_report, name='generate_report'),
    path('print.html', TemplateView.as_view(template_name='report_form/print.html'), name='print_page'),
]