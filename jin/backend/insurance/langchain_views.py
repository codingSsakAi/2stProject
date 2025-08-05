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
    """LangChain 서비스 상태 조회"""
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
    """맞춤형 보험 추천 생성"""
    try:
        data = request.data
        user_info = data.get('user_info', '').strip()
        
        if not user_info:
            return Response(
                {'error': '사용자 정보가 비어있습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        langchain_service = LangChainService()
        
        # 추천 생성
        recommendation = langchain_service._generate_insurance_recommendation(user_info)
        
        return Response({
            'success': True,
            'recommendation': recommendation,
            'user_info': user_info
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
        top_k = data.get('top_k', 5)
        
        if not query:
            return Response(
                {'error': '검색어가 비어있습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        langchain_service = LangChainService()
        
        # 문서 검색
        search_result = langchain_service._search_insurance_documents(query)
        
        return Response({
            'success': True,
            'search_result': search_result,
            'query': query,
            'top_k': top_k
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
    """보험 회사 정보 조회"""
    try:
        data = request.data
        company_name = data.get('company_name', '').strip()
        
        if not company_name:
            return Response(
                {'error': '회사명이 비어있습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        langchain_service = LangChainService()
        
        # 회사 정보 조회
        company_info = langchain_service._get_insurance_company_info(company_name)
        
        return Response({
            'success': True,
            'company_info': company_info,
            'company_name': company_name
        })

    except Exception as e:
        logger.error(f"보험 회사 정보 조회 실패: {e}")
        return Response(
            {'error': f'회사 정보 조회 중 오류가 발생했습니다: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def compare_insurance_products(request):
    """보험 상품 비교 분석"""
    try:
        data = request.data
        product_names = data.get('product_names', '').strip()
        
        if not product_names:
            return Response(
                {'error': '상품명이 비어있습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        langchain_service = LangChainService()
        
        # 상품 비교 분석
        comparison_result = langchain_service._compare_insurance_products(product_names)
        
        return Response({
            'success': True,
            'comparison_result': comparison_result,
            'product_names': product_names
        })

    except Exception as e:
        logger.error(f"보험 상품 비교 분석 실패: {e}")
        return Response(
            {'error': f'상품 비교 분석 중 오류가 발생했습니다: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def test_langchain_tools(request):
    """LangChain 도구 테스트"""
    try:
        data = request.data
        tool_name = data.get('tool_name', '').strip()
        tool_input = data.get('tool_input', '').strip()
        
        if not tool_name or not tool_input:
            return Response(
                {'error': '도구명과 입력값이 필요합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        langchain_service = LangChainService()
        
        # 도구 실행
        tool_functions = {
            '보험_문서_검색': langchain_service._search_insurance_documents,
            '보험_회사_정보_조회': langchain_service._get_insurance_company_info,
            '보험_추천_생성': langchain_service._generate_insurance_recommendation,
            '보험_비교_분석': langchain_service._compare_insurance_products
        }
        
        if tool_name not in tool_functions:
            return Response(
                {'error': f'알 수 없는 도구명: {tool_name}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        result = tool_functions[tool_name](tool_input)
        
        return Response({
            'success': True,
            'tool_name': tool_name,
            'tool_input': tool_input,
            'result': result
        })

    except Exception as e:
        logger.error(f"LangChain 도구 테스트 실패: {e}")
        return Response(
            {'error': f'도구 테스트 중 오류가 발생했습니다: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        ) 