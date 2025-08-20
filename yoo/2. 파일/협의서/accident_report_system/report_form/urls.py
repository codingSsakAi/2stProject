from django.urls import path
from .views import generate_report

urlpatterns = [
    path('', generate_report, name='generate_report'),
]
