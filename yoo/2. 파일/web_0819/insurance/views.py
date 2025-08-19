from django.shortcuts import render
from django.views.generic import TemplateView
# Create your views here.

class InsuranceListView(TemplateView):
    template_name = 'insurance/list.html'

class RecommendView(TemplateView):
    template_name = 'insurance/recommend.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': '보험 추천',
            'subtitle': 'AI가 분석한 맞춤형 자동차보험을 추천해드립니다',
            'step_items': [
                '차량정보 입력',
                '운전패턴 분석', 
                '보험 옵션 선택',
                '맞춤 추천 결과'
            ]
        })
        return context

class CustomInsuranceView(TemplateView):
    template_name = 'insurance/custom.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': '맞춤형 보험',
            'subtitle': '나의 라이프스타일에 맞는 보험을 설계해보세요',
            'categories': [
                {
                    'name': '경제형',
                    'description': '기본 보장으로 합리적인 보험료',
                    'features': ['대인배상', '대물배상', '자손배상']
                },
                {
                    'name': '표준형', 
                    'description': '균형잡힌 보장과 합리적 보험료',
                    'features': ['대인배상', '대물배상', '자손배상', '자기신체사고']
                },
                {
                    'name': '고급형',
                    'description': '풍부한 보장으로 안심 보험',
                    'features': ['대인배상', '대물배상', '자손배상', '자기신체사고', '자기차량손해']
                }
            ]
        })
        return context

class CompareView(TemplateView):
    template_name = 'insurance/compare.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': '보험 비교',
            'subtitle': '여러 보험사의 상품을 한눈에 비교해보세요',
            'external_link': True,
            'partner_sites': [
                {'name': '보험다모아', 'url': '#'},
                {'name': '굿초이스', 'url': '#'},
                {'name': '보험비교사이트', 'url': '#'}
            ]
        })
        return context

class CompaniesView(TemplateView):
    template_name = 'insurance/companies.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': '보험사 알아보기',
            'subtitle': '신뢰할 수 있는 보험사 정보를 확인하세요',
            'companies': [
                {
                    'name': 'DB손해보험',
                    'rating': '4.5',
                    'features': ['빠른 보상', '친절한 서비스', '합리적 보험료'],
                    'logo': 'db_logo.png'
                },
                {
                    'name': '삼성화재',
                    'rating': '4.3', 
                    'features': ['든든한 보장', '다양한 상품', '전국 서비스망'],
                    'logo': 'samsung_logo.png'
                },
                {
                    'name': '현대해상',
                    'rating': '4.2',
                    'features': ['디지털 서비스', '맞춤형 상품', '간편 청구'],
                    'logo': 'hyundai_logo.png'
                }
            ]
        })
        return context

class QuoteView(TemplateView):
    template_name = 'insurance/quote.html'