from django.shortcuts import render
from django.views.generic import TemplateView
# Create your views here.

class GuideListView(TemplateView):
    template_name = 'guide/list.html'

class FaultRatioView(TemplateView):
    template_name = 'guide/fault_ratio.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': '과실비율 알아보기',
            'subtitle': '사고 유형별 과실비율을 미리 확인해보세요',
            'accident_types': [
                {
                    'category': '추돌사고',
                    'cases': [
                        {'situation': '신호대기 중 뒤에서 추돌', 'fault_ratio': '후행차 100%'},
                        {'situation': '급정거로 인한 추돌', 'fault_ratio': '전행차 30% : 후행차 70%'},
                        {'situation': '끼어들기 중 추돌', 'fault_ratio': '끼어든 차 80% : 직진차 20%'}
                    ]
                },
                {
                    'category': '교차로사고',
                    'cases': [
                        {'situation': '신호위반 vs 직진', 'fault_ratio': '신호위반차 100%'},
                        {'situation': '좌회전 vs 직진', 'fault_ratio': '좌회전차 80% : 직진차 20%'},
                        {'situation': '우회전 vs 직진', 'fault_ratio': '우회전차 20% : 직진차 80%'}
                    ]
                }
            ]
        })
        return context

class CompensationView(TemplateView):
    template_name = 'guide/compensation.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': '자동차 보상 상식',
            'subtitle': '보상절차와 필요서류를 미리 알아두세요',
            'compensation_steps': [
                {
                    'step': 1,
                    'title': '사고신고',
                    'description': '보험사 및 경찰서에 신고',
                    'documents': ['사고경위서', '운전면허증', '차량등록증']
                },
                {
                    'step': 2,
                    'title': '현장조사',
                    'description': '보험사 직원이 현장 확인',
                    'documents': ['사고사진', '블랙박스 영상', '목격자 진술']
                },
                {
                    'step': 3,
                    'title': '손해사정',
                    'description': '수리비 및 과실비율 결정',
                    'documents': ['수리견적서', '의료비 영수증']
                },
                {
                    'step': 4,
                    'title': '보상금 지급',
                    'description': '확정된 보상금 지급',
                    'documents': ['통장사본', '신분증']
                }
            ]
        })
        return context

class AccidentGuideView(TemplateView):
    template_name = 'guide/accident.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': '사고처리 가이드',
            'subtitle': '사고 발생 시 신속하고 정확한 대처방법',
            'emergency_steps': [
                {
                    'priority': '최우선',
                    'action': '인명구조',
                    'details': ['부상자 확인', '119 신고', '안전한 곳으로 이동']
                },
                {
                    'priority': '1단계',
                    'action': '2차 사고 방지',
                    'details': ['비상등 점멸', '삼각대 설치', '갓길로 차량 이동']
                },
                {
                    'priority': '2단계', 
                    'action': '증거수집',
                    'details': ['사고현장 촬영', '상대방 연락처 확인', '목격자 확보']
                },
                {
                    'priority': '3단계',
                    'action': '보험사 신고',
                    'details': ['보험사 콜센터 연락', '사고경위 설명', '현장조사 요청']
                }
            ]
        })
        return context

class KnowledgeView(TemplateView):
    template_name = 'guide/knowledge.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': '자동차 보험상식',
            'subtitle': '알아두면 유용한 자동차보험 정보',
            'knowledge_categories': [
                {
                    'category': '보험료 절약 팁',
                    'tips': [
                        '무사고 할인 혜택 최대 활용',
                        '마일리지 연동 보험 가입',
                        '불필요한 특약 정리',
                        '보험료 연납 할인 활용'
                    ]
                },
                {
                    'category': '청구 시 주의사항',
                    'tips': [
                        '허위신고 시 계약해지 위험',
                        '음주운전 시 보험금 부지급',
                        '무면허 운전 시 보장 제외',
                        '신고 의무 위반 시 불이익'
                    ]
                }
            ]
        })
        return context