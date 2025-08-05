"""
Insurance 앱 뷰
RAG 시스템 및 보험 추천 시스템을 위한 뷰
"""

import logging
import json
from typing import Dict, Any, List
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from .services import RAGService
from .models import PolicyDocument, InsuranceCompany

# 로깅 설정
logger = logging.getLogger(__name__)


def main_page(request):
    """메인 페이지 - 보험 추천 시스템 홈"""
    try:
        context = {
            'title': '자동차 보험 추천 시스템',
            'description': 'AI 기반 맞춤형 자동차 보험 추천 서비스',
            'features': [
                {
                    'title': '🤖 AI 상담사',
                    'description': 'LangChain 기반 지능형 보험 상담',
                    'icon': 'chat-bubble',
                    'url': '/insurance/langchain-dashboard/'
                },
                {
                    'title': '🎯 ML 추천',
                    'description': '머신러닝 기반 맞춤형 보험 추천',
                    'icon': 'target',
                    'url': '/insurance/ml-dashboard/'
                },
                {
                    'title': '📊 RAG 시스템',
                    'description': '보험 약관 검색 및 분석',
                    'icon': 'search',
                    'url': '/insurance/rag-dashboard/'
                },
                {
                    'title': '📋 보험 비교',
                    'description': '다양한 보험 상품 비교 분석',
                    'icon': 'compare',
                    'url': '/insurance/compare/'
                }
            ]
        }
        
        return render(request, 'insurance/main_page.jinja.html', context)
        
    except Exception as e:
        logger.error(f"메인 페이지 로드 실패: {e}")
        return render(request, 'insurance/main_page.jinja.html', {
            'error': f'페이지 로드 중 오류가 발생했습니다: {str(e)}'
        })


def rag_dashboard(request):
    """RAG 대시보드"""
    try:
        rag_service = RAGService()
        stats = rag_service.get_index_stats()

        context = {"title": "RAG 시스템 대시보드", "stats": stats}

        return render(request, "insurance/rag_dashboard.html", context)

    except Exception as e:
        logger.error(f"RAG 대시보드 로드 실패: {e}")
        return HttpResponse(
            f"대시보드 로드 중 오류가 발생했습니다: {str(e)}", status=500
        )


def compare_insurance(request):
    """보험 비교 페이지"""
    try:
        context = {
            'title': '보험 상품 비교',
            'description': '다양한 자동차 보험 상품을 비교해보세요'
        }
        
        return render(request, 'insurance/compare.jinja.html', context)
        
    except Exception as e:
        logger.error(f"보험 비교 페이지 로드 실패: {e}")
        return render(request, 'insurance/compare.jinja.html', {
            'error': f'페이지 로드 중 오류가 발생했습니다: {str(e)}'
        })


def about_page(request):
    """소개 페이지"""
    try:
        context = {
            'title': '서비스 소개',
            'description': 'AI 기반 자동차 보험 추천 시스템에 대해 알아보세요'
        }
        
        return render(request, 'insurance/about.jinja.html', context)
        
    except Exception as e:
        logger.error(f"소개 페이지 로드 실패: {e}")
        return render(request, 'insurance/about.jinja.html', {
            'error': f'페이지 로드 중 오류가 발생했습니다: {str(e)}'
        })


@api_view(["POST"])
@permission_classes([AllowAny])
def search_documents_api(request):
    """문서 검색 API"""
    try:
        data = request.data
        query = data.get("query", "").strip()

        if not query:
            return Response(
                {"error": "검색어가 비어있습니다."}, status=status.HTTP_400_BAD_REQUEST
            )

        rag_service = RAGService()
        results = rag_service.search_documents(query, top_k=5)

        return Response({"success": True, "query": query, "results": results})

    except Exception as e:
        logger.error(f"문서 검색 실패: {e}")
        return Response(
            {"error": f"검색 중 오류가 발생했습니다: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def generate_response_api(request):
    """응답 생성 API"""
    try:
        data = request.data
        query = data.get("query", "").strip()

        if not query:
            return Response(
                {"error": "질문이 비어있습니다."}, status=status.HTTP_400_BAD_REQUEST
            )

        rag_service = RAGService()
        response = rag_service.generate_response(query)

        return Response({"success": True, "query": query, "response": response})

    except Exception as e:
        logger.error(f"응답 생성 실패: {e}")
        return Response(
            {"error": f"응답 생성 중 오류가 발생했습니다: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def chat_api(request):
    """채팅 API"""
    try:
        data = request.data
        message = data.get("message", "").strip()

        if not message:
            return Response(
                {"error": "메시지가 비어있습니다."}, status=status.HTTP_400_BAD_REQUEST
            )

        rag_service = RAGService()
        response = rag_service.chat(message)

        return Response({"success": True, "message": message, "response": response})

    except Exception as e:
        logger.error(f"채팅 실패: {e}")
        return Response(
            {"error": f"채팅 중 오류가 발생했습니다: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def get_index_stats_api(request):
    """인덱스 통계 API"""
    try:
        rag_service = RAGService()
        stats = rag_service.get_index_stats()

        return Response({"success": True, "stats": stats})

    except Exception as e:
        logger.error(f"통계 조회 실패: {e}")
        return Response(
            {"error": f"통계 조회 중 오류가 발생했습니다: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def upload_document_api(request):
    """문서 업로드 API"""
    try:
        if "file" not in request.FILES:
            return Response(
                {"error": "파일이 업로드되지 않았습니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        file = request.FILES["file"]

        # 파일 크기 검증
        if file.size > settings.MAX_UPLOAD_SIZE:
            return Response(
                {
                    "error": f"파일 크기가 너무 큽니다. 최대 {settings.MAX_UPLOAD_SIZE} bytes"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 파일 확장자 검증
        file_extension = file.name.split(".")[-1].lower()
        if file_extension not in settings.ALLOWED_FILE_TYPES:
            return Response(
                {
                    "error": f'지원하지 않는 파일 형식입니다. 지원 형식: {", ".join(settings.ALLOWED_FILE_TYPES)}'
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        rag_service = RAGService()
        result = rag_service.upload_document(file)

        return Response(
            {
                "success": True,
                "message": "문서가 성공적으로 업로드되었습니다.",
                "result": result,
            }
        )

    except Exception as e:
        logger.error(f"문서 업로드 실패: {e}")
        return Response(
            {"error": f"문서 업로드 중 오류가 발생했습니다: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def delete_document_api(request):
    """문서 삭제 API"""
    try:
        data = request.data
        document_id = data.get("document_id")

        if not document_id:
            return Response(
                {"error": "문서 ID가 필요합니다."}, status=status.HTTP_400_BAD_REQUEST
            )

        rag_service = RAGService()
        result = rag_service.delete_document(document_id)

        return Response(
            {
                "success": True,
                "message": "문서가 성공적으로 삭제되었습니다.",
                "result": result,
            }
        )

    except Exception as e:
        logger.error(f"문서 삭제 실패: {e}")
        return Response(
            {"error": f"문서 삭제 중 오류가 발생했습니다: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
