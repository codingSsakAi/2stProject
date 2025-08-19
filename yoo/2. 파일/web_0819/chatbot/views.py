from django.shortcuts import render
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.views import View
import json
# Create your views here.

class ChatbotView(TemplateView):
    template_name = 'chatbot/index.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': '보험 상담 챗봇',
            'subtitle': '궁금한 것이 있으시면 언제든 물어보세요!',
            'quick_questions': [
                '자동차보험료 계산하기',
                '사고 신고 방법',
                '보험금 청구 절차',
                '과실비율 문의',
                '보험 상품 추천'
            ]
        })
        return context

class ChatAPIView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            user_message = data.get('message', '')
            
            # 간단한 규칙 기반 챗봇 응답
            response = self.get_bot_response(user_message)
            
            return JsonResponse({
                'success': True,
                'response': response
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    def get_bot_response(self, message):
        """간단한 규칙 기반 챗봇 응답"""
        message = message.lower()
        
        if '보험료' in message or '계산' in message:
            return {
                'text': '자동차보험료 계산을 도와드리겠습니다. 차량연식, 운전경력, 지역 등의 정보가 필요합니다. 맞춤 견적을 원하시면 보험 추천 페이지를 이용해주세요.',
                'buttons': [
                    {'text': '보험료 계산하기', 'url': '/insurance/recommend/'},
                    {'text': '맞춤 보험 찾기', 'url': '/insurance/custom/'}
                ]
            }
        elif '사고' in message and '신고' in message:
            return {
                'text': '사고 신고는 다음 순서로 진행해주세요:\n1. 인명구조 최우선\n2. 2차 사고 방지\n3. 증거수집\n4. 보험사 신고\n자세한 가이드를 확인해보세요.',
                'buttons': [
                    {'text': '사고처리 가이드', 'url': '/guide/accident/'},
                    {'text': '과실비율 확인', 'url': '/guide/fault-ratio/'}
                ]
            }
        elif '보험금' in message and '청구' in message:
            return {
                'text': '보험금 청구 절차는 다음과 같습니다:\n1. 사고신고\n2. 현장조사\n3. 손해사정\n4. 보상금 지급\n필요한 서류와 자세한 절차를 안내해드리겠습니다.',
                'buttons': [
                    {'text': '보상 절차 보기', 'url': '/guide/compensation/'},
                    {'text': '필요 서류 확인', 'url': '/guide/compensation/'}
                ]
            }
        elif '과실' in message or '비율' in message:
            return {
                'text': '과실비율은 사고 유형에 따라 달라집니다. 추돌사고, 교차로사고 등 상황별로 과실비율을 미리 확인해보세요.',
                'buttons': [
                    {'text': '과실비율 확인', 'url': '/guide/fault-ratio/'},
                    {'text': '사고처리 가이드', 'url': '/guide/accident/'}
                ]
            }
        elif '추천' in message or '상품' in message:
            return {
                'text': 'AI가 고객님의 조건에 맞는 최적의 보험상품을 추천해드립니다. 차량정보와 운전패턴을 분석하여 맞춤형 보험을 제안합니다.',
                'buttons': [
                    {'text': '보험 추천받기', 'url': '/insurance/recommend/'},
                    {'text': '보험사 비교', 'url': '/insurance/companies/'}
                ]
            }
        elif '안녕' in message or '안녕하세요' in message:
            return {
                'text': '안녕하세요! 자동차보험 상담 챗봇입니다. 궁금한 것이 있으시면 언제든 물어보세요. 아래 버튼을 클릭하시거나 직접 질문해주세요.',
                'buttons': [
                    {'text': '보험료 계산', 'action': 'message', 'value': '보험료 계산하고 싶어요'},
                    {'text': '사고 신고', 'action': 'message', 'value': '사고 신고 방법 알려주세요'},
                    {'text': '보험 추천', 'action': 'message', 'value': '보험 상품 추천해주세요'}
                ]
            }
        else:
            return {
                'text': '죄송합니다. 정확히 이해하지 못했습니다. 다음과 같은 주제로 도움을 드릴 수 있습니다:\n• 자동차보험료 계산\n• 사고 신고 방법\n• 보험금 청구 절차\n• 과실비율 문의\n• 보험 상품 추천',
                'buttons': [
                    {'text': '자주 묻는 질문', 'url': '/guide/knowledge/'},
                    {'text': '고객센터 연결', 'action': 'phone', 'value': '1588-0000'}
                ]
            }