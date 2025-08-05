from django.urls import path
from . import views

urlpatterns = [
    path('car_knowhow/', views.car_knowhow_list, name='car_knowhow_list'),
    path('car_knowhow/<int:pk>/', views.car_knowhow_detail, name='car_knowhow_detail'),
]