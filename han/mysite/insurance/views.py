from django.shortcuts import render

# Create your views here.

from .models import CarInsuranceKnowledge
from django.shortcuts import render, get_object_or_404

def car_knowhow_list(request):
    items = CarInsuranceKnowledge.objects.order_by('order')
    return render(request, 'insurance/car_knowhow_list.html', {'items': items})

def car_knowhow_detail(request, pk):
    item = get_object_or_404(CarInsuranceKnowledge, pk=pk)
    return render(request, 'insurance/car_knowhow_detail.html', {'item': item})

