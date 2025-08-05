"""
LangChain + LLM API 뷰
보험 추천 시스템을 위한 LangChain 기반 API 엔드포인트
"""

import logging
from typing import Dict, Any, List
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
import json

from .langchain_service import LangChainService

# 로깅 설정
logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([AllowAny])
def chat_with_agent(request):
    """LangChain 에이전트와 대화"""
    try:
        data = request.data
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return Response(
                {'error': '메시지가 비어있습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # LangChain 서비스 초기화
        langchain_service = LangChainService()
        
        # 에이전트와 대화
        response = langchain_service.chat_with_agent(user_message)
        
        return Response({
            'success': True,
            'response': response,
            'user_message': user_message
        })

    except Exception as e:
        logger.error(f"에이전트 대화 실패: {e}")
        return Response(
            {'error': f'대화 중 오류가 발생했습니다: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_conversation_history(request):
    """대화 기록 조회"""
    try:
        langchain_service = LangChainService()
        history = langchain_service.get_conversation_history()
        
        return Response({
            'success': True,
            'history': history
        })

    except Exception as e:
        logger.error(f"대화 기록 조회 실패: {e}")
        return Response(
            {'error': f'대화 기록 조회 중 오류가 발생했습니다: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def clear_conversation_memory(request):
    """대화 메모리 초기화"""
    try:
        langchain_service = LangChainService()
        langchain_service.clear_memory()
        
        return Response({
            'success': True,
            'message': '대화 메모리가 초기화되었습니다.'
        })

    except Exception as e:
        logger.error(f"대화 메모리 초기화 실패: {e}")
        return Response(
            {'error': f'메모리 초기화 중 오류가 발생했습니다: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_service_status(request):
    """서비스 상태 조회"""
    try:
        langchain_service = LangChainService()
        status_info = langchain_service.get_service_status()
        
        return Response({
            'success': True,
            'status': status_info
        })

    except Exception as e:
        logger.error(f"서비스 상태 조회 실패: {e}")
        return Response(
            {'error': f'서비스 상태 조회 중 오류가 발생했습니다: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def generate_insurance_recommendation(request):
    """보험 추천 생성"""
    try:
        data = request.data
        user_profile = data.get('user_profile', {})
        
        if not user_profile:
            return Response(
                {'error': '사용자 프로필이 필요합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        langchain_service = LangChainService()
        recommendation = langchain_service.generate_insurance_recommendation(user_profile)
        
        return Response({
            'success': True,
            'recommendation': recommendation
        })

    except Exception as e:
        logger.error(f"보험 추천 생성 실패: {e}")
        return Response(
            {'error': f'추천 생성 중 오류가 발생했습니다: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def search_insurance_documents(request):
    """보험 문서 검색"""
    try:
        data = request.data
        query = data.get('query', '').strip()
        
        if not query:
            return Response(
                {'error': '검색어가 필요합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        langchain_service = LangChainService()
        results = langchain_service.search_insurance_documents(query)
        
        return Response({
            'success': True,
            'results': results
        })

    except Exception as e:
        logger.error(f"보험 문서 검색 실패: {e}")
        return Response(
            {'error': f'문서 검색 중 오류가 발생했습니다: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def get_insurance_company_info(request):
    """보험사 정보 조회"""
    try:
        data = request.data
        company_name = data.get('company_name', '').strip()
        
        if not company_name:
            return Response(
                {'error': '보험사명이 필요합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        langchain_service = LangChainService()
        company_info = langchain_service.get_insurance_company_info(company_name)
        
        return Response({
            'success': True,
            'company_info': company_info
        })

    except Exception as e:
        logger.error(f"보험사 정보 조회 실패: {e}")
        return Response(
            {'error': f'보험사 정보 조회 중 오류가 발생했습니다: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def compare_insurance_products(request):
    """보험 상품 비교"""
    try:
        data = request.data
        products = data.get('products', [])
        user_profile = data.get('user_profile', {})
        
        if not products:
            return Response(
                {'error': '비교할 상품이 필요합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        langchain_service = LangChainService()
        comparison = langchain_service.compare_insurance_products(products, user_profile)
        
        return Response({
            'success': True,
            'comparison': comparison
        })

    except Exception as e:
        logger.error(f"보험 상품 비교 실패: {e}")
        return Response(
            {'error': f'상품 비교 중 오류가 발생했습니다: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def test_langchain_tools(request):
    """LangChain 도구 테스트"""
    try:
        data = request.data
        tool_name = data.get('tool_name', '')
        
        langchain_service = LangChainService()
        test_result = langchain_service.test_tool(tool_name)
        
        return Response({
            'success': True,
            'test_result': test_result
        })

    except Exception as e:
        logger.error(f"LangChain 도구 테스트 실패: {e}")
        return Response(
            {'error': f'도구 테스트 중 오류가 발생했습니다: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def generate_personalized_recommendation(request):
    """개인화된 보험 추천 생성"""
    try:
        data = request.data
        user_profile = data.get('user_profile', {})
        user_preferences = data.get('user_preferences', {})
        chat_history = data.get('chat_history', [])
        
        if not user_profile:
            return Response(
                {'error': '사용자 프로필이 필요합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        langchain_service = LangChainService()
        
        # 개인화된 추천 생성
        personalized_recommendation = langchain_service.generate_personalized_recommendation(
            user_profile=user_profile,
            user_preferences=user_preferences,
            chat_history=chat_history
        )
        
        return Response({
            'success': True,
            'personalized_recommendation': personalized_recommendation
        })

    except Exception as e:
        logger.error(f"개인화 추천 생성 실패: {e}")
        return Response(
            {'error': f'개인화 추천 생성 중 오류가 발생했습니다: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def analyze_user_risk_profile(request):
    """사용자 위험도 프로필 분석"""
    try:
        data = request.data
        user_profile = data.get('user_profile', {})
        
        if not user_profile:
            return Response(
                {'error': '사용자 프로필이 필요합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        langchain_service = LangChainService()
        
        # 위험도 분석
        risk_analysis = langchain_service.analyze_user_risk_profile(user_profile)
        
        return Response({
            'success': True,
            'risk_analysis': risk_analysis
        })

    except Exception as e:
        logger.error(f"위험도 분석 실패: {e}")
        return Response(
            {'error': f'위험도 분석 중 오류가 발생했습니다: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def get_smart_insurance_suggestions(request):
    """스마트 보험 제안"""
    try:
        data = request.data
        user_profile = data.get('user_profile', {})
        current_situation = data.get('current_situation', '')
        
        if not user_profile:
            return Response(
                {'error': '사용자 프로필이 필요합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        langchain_service = LangChainService()
        
        # 스마트 제안 생성
        smart_suggestions = langchain_service.get_smart_insurance_suggestions(
            user_profile=user_profile,
            current_situation=current_situation
        )
        
        return Response({
            'success': True,
            'smart_suggestions': smart_suggestions
        })

    except Exception as e:
        logger.error(f"스마트 제안 생성 실패: {e}")
        return Response(
            {'error': f'스마트 제안 생성 중 오류가 발생했습니다: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def update_user_preferences(request):
    """사용자 선호도 업데이트"""
    try:
        data = request.data
        user_id = data.get('user_id')
        preferences = data.get('preferences', {})
        
        if not user_id:
            return Response(
                {'error': '사용자 ID가 필요합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        langchain_service = LangChainService()
        
        # 선호도 업데이트
        update_result = langchain_service.update_user_preferences(user_id, preferences)
        
        return Response({
            'success': True,
            'update_result': update_result
        })

    except Exception as e:
        logger.error(f"사용자 선호도 업데이트 실패: {e}")
        return Response(
            {'error': f'선호도 업데이트 중 오류가 발생했습니다: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        ) 