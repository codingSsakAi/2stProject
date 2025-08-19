# home/views.py
from django.shortcuts import render

def index(request):
    """메인 페이지"""
    context = {
        'title': '자동차보험 알아보기',
        'subtitle': '최적의 자동차보험을 찾아드립니다',
        # 나중에 추가할 데이터들
        'main_slides': [],
        'main_cards': [],
        'latest_news': []
    }
    return render(request, 'home/index.html', context)