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

from django.contrib.auth.decorators import user_passes_test
import os
from pathlib import Path
from django.conf import settings
import PyPDF2
from docx import Document
from werkzeug.utils import secure_filename

# 로깅 설정
logger = logging.getLogger(__name__)


def main_page(request):
    """메인 페이지 - AI 챗봇 중심 보험 추천 시스템 홈"""
    try:
        context = {
            "title": "AI 챗봇 자동차 보험 추천",
            "description": "개인화된 AI 챗봇으로 최적의 자동차 보험을 찾아보세요",
        }

        return render(request, "insurance/main_page.jinja.html", context)

    except Exception as e:
        logger.error(f"메인 페이지 로드 실패: {e}")
        return render(
            request,
            "insurance/main_page.jinja.html",
            {"error": f"페이지 로드 중 오류가 발생했습니다: {str(e)}"},
        )


def rag_dashboard(request):
    """RAG 대시보드"""
    try:
        rag_service = RAGService()
        stats = rag_service.get_index_stats()

        context = {"title": "RAG 시스템 대시보드", "stats": stats}

        return render(request, "insurance/rag_dashboard.jinja.html", context)

    except Exception as e:
        logger.error(f"RAG 대시보드 로드 실패: {e}")
        return HttpResponse(
            f"대시보드 로드 중 오류가 발생했습니다: {str(e)}", status=500
        )


def compare_insurance(request):
    """보험 비교 페이지"""
    try:
        context = {
            "title": "보험 상품 비교",
            "description": "다양한 자동차 보험 상품을 비교해보세요",
        }

        return render(request, "insurance/compare.jinja.html", context)

    except Exception as e:
        logger.error(f"보험 비교 페이지 로드 실패: {e}")
        return render(
            request,
            "insurance/compare.jinja.html",
            {"error": f"페이지 로드 중 오류가 발생했습니다: {str(e)}"},
        )


def about_page(request):
    """소개 페이지"""
    try:
        context = {
            "title": "서비스 소개",
            "description": "AI 기반 자동차 보험 추천 시스템에 대해 알아보세요",
        }

        return render(request, "insurance/about.jinja.html", context)

    except Exception as e:
        logger.error(f"소개 페이지 로드 실패: {e}")
        return render(
            request,
            "insurance/about.jinja.html",
            {"error": f"페이지 로드 중 오류가 발생했습니다: {str(e)}"},
        )


def personalized_chat(request):
    """개인화된 AI 챗봇 페이지"""
    try:
        context = {
            "title": "개인화된 AI 챗봇",
            "description": "당신의 프로필을 기반으로 맞춤형 보험 상담을 제공합니다",
        }

        return render(request, "insurance/personalized_chat.jinja.html", context)

    except Exception as e:
        logger.error(f"개인화 챗봇 페이지 로드 실패: {e}")
        return render(
            request,
            "insurance/personalized_chat.jinja.html",
            {"error": f"페이지 로드 중 오류가 발생했습니다: {str(e)}"},
        )


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


def admin_required(view_func):
    """관리자 권한 확인 데코레이터"""
    return user_passes_test(lambda u: u.is_staff)(view_func)


@admin_required
def admin_upload_document(request):
    """관리자 문서 업로드 페이지"""
    if request.method == "POST":
        try:
            company = request.POST.get("company")
            document_file = request.FILES.get("document")
            title = request.POST.get("title")
            document_type = request.POST.get("document_type")
            description = request.POST.get("description", "")
            tags = request.POST.get("tags", "")

            if not all([company, document_file, title, document_type]):
                return JsonResponse(
                    {"success": False, "error": "필수 정보가 누락되었습니다."}
                )

            # 파일 저장 및 처리
            result = process_document_upload(
                company, document_file, title, document_type, description, tags
            )

            return JsonResponse(result)

        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    # GET 요청: 업로드 페이지 표시
    insurance_companies = [
        "삼성화재",
        "현대해상",
        "KB손해보험",
        "메리츠화재",
        "DB손해보험",
        "롯데손해보험",
        "하나손해보험",
        "흥국화재",
        "AXA손해보험",
        "MG손해보험",
        "캐롯손해보험",
        "한화손해보험",
    ]

    context = {"insurance_companies": insurance_companies, "title": "문서 업로드"}

    return render(request, "insurance/admin_upload.jinja.html", context)


def process_document_upload(company, file, title, document_type, description, tags):
    """문서 업로드 처리"""
    try:
        # 1. PDF 폴더에 파일 저장
        pdf_dir = Path(settings.BASE_DIR) / "policy_documents" / "pdf" / company
        pdf_dir.mkdir(parents=True, exist_ok=True)

        filename = secure_filename(file.name)
        pdf_path = pdf_dir / filename

        with open(pdf_path, "wb") as f:
            for chunk in file.chunks():
                f.write(chunk)

        # 2. PDF → DOCX 변환
        docx_dir = Path(settings.BASE_DIR) / "policy_documents" / "docx" / company
        docx_dir.mkdir(parents=True, exist_ok=True)

        docx_filename = filename.replace(".pdf", ".docx")
        docx_path = docx_dir / docx_filename

        # PDF → DOCX 변환
        convert_pdf_to_docx(pdf_path, docx_path)

        # 3. 데이터베이스에 문서 정보 저장
        document = PolicyDocument.objects.create(
            title=title,
            company=InsuranceCompany.objects.get(name=company),
            document_type=document_type,
            description=description,
            tags=tags,
            file_path=str(docx_path),
            status="approved",
        )

        # 4. Pinecone에 업로드
        rag_service = RAGService()
        upload_result = rag_service.upload_document_with_metadata(
            docx_path, company, document_type, title, tags
        )

        return {
            "success": True,
            "message": f"문서 업로드 완료: {title}",
            "document_id": document.id,
            "pinecone_result": upload_result,
        }

    except Exception as e:
        logger.error(f"문서 업로드 실패: {e}")
        return {"success": False, "error": str(e)}


def convert_pdf_to_docx(pdf_path, docx_path):
    """PDF를 DOCX로 변환"""
    try:
        # PDF 텍스트 추출
        pdf_reader = PyPDF2.PdfReader(pdf_path)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"

        # DOCX 생성
        doc = Document()
        doc.add_paragraph(text)
        doc.save(docx_path)

        logger.info(f"PDF → DOCX 변환 완료: {pdf_path} → {docx_path}")

    except Exception as e:
        logger.error(f"PDF → DOCX 변환 실패: {e}")
        raise e

@admin_required
def admin_document_list(request):
    """관리자 문서 목록 페이지"""
    documents = PolicyDocument.objects.all().order_by('-upload_date')
    context = {
        'documents': documents,
        'title': '문서 관리'
    }
    return render(request, 'insurance/admin_documents.jinja.html', context)

@admin_required
def admin_pinecone_management(request):
    """관리자 Pinecone 관리 페이지"""
    rag_service = RAGService()
    stats = rag_service.get_company_document_stats()
    
    context = {
        'stats': stats,
        'title': 'Pinecone 관리'
    }
    return render(request, 'insurance/admin_pinecone.jinja.html', context)
