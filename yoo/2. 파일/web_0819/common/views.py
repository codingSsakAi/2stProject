from django.shortcuts import render
from django.views.generic import TemplateView
# Create your views here.


class TermsView(TemplateView):
    template_name = 'common/terms.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': '보험 용어사전',
            'subtitle': '어려운 보험용어를 쉽게 설명해드립니다',
            'term_categories': [
                {
                    'category': '기본 용어',
                    'terms': [
                        {
                            'term': '대인배상',
                            'definition': '타인의 생명이나 신체에 피해를 입혔을 때 보상하는 보험',
                            'example': '교통사고로 상대방이 다쳤을 때 치료비, 위자료 등을 보상'
                        },
                        {
                            'term': '대물배상',
                            'definition': '타인의 재물에 피해를 입혔을 때 보상하는 보험',
                            'example': '사고로 상대방 차량이나 시설물을 파손했을 때 수리비 보상'
                        },
                        {
                            'term': '자기신체사고',
                            'definition': '운전자 본인이 다쳤을 때 보상받는 보험',
                            'example': '사고로 본인이 부상당했을 때 치료비, 휴업손해 등을 보상'
                        }
                    ]
                },
                {
                    'category': '특약 용어',
                    'terms': [
                        {
                            'term': '무보험차상해',
                            'definition': '무보험차량과의 사고 시 피해를 보상하는 특약',
                            'example': '상대방이 보험에 가입하지 않은 경우 내 보험으로 보상'
                        },
                        {
                            'term': '자기차량손해',
                            'definition': '내 차량의 파손이나 도난 시 보상하는 특약',
                            'example': '사고, 도난, 화재 등으로 내 차가 손상됐을 때 수리비 보상'
                        },
                        {
                            'term': '블랙박스특약',
                            'definition': '블랙박스 장착 시 보험료 할인 및 사고 시 혜택을 주는 특약',
                            'example': '블랙박스 영상 제공 시 과실비율 우대 또는 보험료 할인'
                        }
                    ]
                },
                {
                    'category': '청구 관련 용어',
                    'terms': [
                        {
                            'term': '과실비율',
                            'definition': '사고에 대한 책임의 정도를 백분율로 나타낸 것',
                            'example': 'A차량 70%, B차량 30% - A차량이 더 큰 책임'
                        },
                        {
                            'term': '손해사정',
                            'definition': '사고로 인한 손해의 원인과 규모를 조사하여 보상액을 결정하는 과정',
                            'example': '사고 후 보험사에서 수리비와 과실비율을 조사하는 과정'
                        },
                        {
                            'term': '면책금',
                            'definition': '보험금 지급 시 보험가입자가 부담해야 하는 금액',
                            'example': '수리비 100만원, 면책금 20만원 → 보험사는 80만원만 지급'
                        }
                    ]
                }
            ]
        })
        return context