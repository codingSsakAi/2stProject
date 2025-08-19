from django.shortcuts import render
from django.views.generic import TemplateView, DetailView
# Create your views here.


class NewsListView(TemplateView):
    template_name = 'news/list.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': '뉴스센터',
            'subtitle': '최신 보험업계 및 자동차보험 뉴스',
            'featured_news': [
                {
                    'id': 1,
                    'title': '2024년 자동차보험료 평균 3.5% 인상 예정',
                    'summary': '금융당국이 자동차보험료 인상을 승인하면서 내년부터 보험료 부담이 늘어날 전망입니다.',
                    'category': '업계뉴스',
                    'date': '2024-12-19',
                    'image': 'news1.jpg',
                    'views': 1250
                },
                {
                    'id': 2,
                    'title': '전기차 보험료 할인 혜택 20%까지 확대',
                    'summary': '친환경차 보급 활성화를 위해 전기차 보험료 할인 혜택이 대폭 확대됩니다.',
                    'category': '자동차보험뉴스',
                    'date': '2024-12-18',
                    'image': 'news2.jpg',
                    'views': 890
                }
            ],
            'latest_industry_news': [
                {
                    'title': '보험업계 디지털 전환 가속화',
                    'date': '2024-12-17',
                    'category': '업계동향'
                },
                {
                    'title': 'AI 기반 보험심사 도입 확산',
                    'date': '2024-12-16', 
                    'category': '기술혁신'
                },
                {
                    'title': '금융위, 보험소비자 보호 강화 방안 발표',
                    'date': '2024-12-15',
                    'category': '정책뉴스'
                }
            ],
            'latest_auto_news': [
                {
                    'title': '겨울철 자동차 사고 급증, 보험 청구 늘어',
                    'date': '2024-12-17',
                    'category': '사고통계'
                },
                {
                    'title': '하이브리드차 보험료 할인 혜택 신설',
                    'date': '2024-12-16',
                    'category': '상품소식'
                },
                {
                    'title': '무인자동차 상용화 대비 보험상품 개발',
                    'date': '2024-12-15',
                    'category': '미래기술'
                }
            ]
        })
        return context

class IndustryNewsView(TemplateView):
    template_name = 'news/industry.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': '업계뉴스',
            'subtitle': '보험업계의 최신 동향과 정책 소식'
        })
        return context

class AutoInsuranceNewsView(TemplateView):
    template_name = 'news/auto_insurance.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': '자동차보험뉴스',
            'subtitle': '자동차보험 관련 최신 정보와 상품 소식'
        })
        return context

class NewsDetailView(TemplateView):
    template_name = 'news/detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        news_id = kwargs.get('pk')
        # 실제로는 모델에서 데이터를 가져와야 함
        context.update({
            'news': {
                'id': news_id,
                'title': '샘플 뉴스 제목',
                'content': '뉴스 상세 내용...',
                'date': '2024-12-19',
                'category': '업계뉴스'
            }
        })
        return context