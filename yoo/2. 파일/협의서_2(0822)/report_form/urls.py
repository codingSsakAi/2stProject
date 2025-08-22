from django.urls import path
from django.views.generic import TemplateView
# from .views import generate_report
from . import views


app_name = 'report_form' # namespace 선언

urlpatterns = [
    path("agreement/form/", views.form_view, name="agreement_form"),
    path("agreement/print/", views.print_view, name="agreement_print"),
    path('agreement/download/pdf/', views.download_pdf, name='download_pdf'),
    path('agreement/download/image/', views.download_image, name='download_image'),
    # path("print/", views.agreement_print, name="agreement_print"),
    # path('generate/', views.generate_report, name='generate_report'),
]