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
import logging
import re

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

# Pinecone 관리 API 뷰 함수들
@admin_required
def update_company_index(request):
    """보험사별 인덱스 업데이트"""
    if request.method == 'POST':
        try:
            import json
            data = json.loads(request.body)
            company = data.get('company')
            
            if not company:
                return JsonResponse({'success': False, 'error': '보험사 정보가 누락되었습니다.'})
            
            rag_service = RAGService()
            
            # 해당 보험사의 승인된 문서들만 다시 업로드
            documents = PolicyDocument.objects.filter(
                company__name=company,
                status='approved'
            )
            
            success_count = 0
            for document in documents:
                if document.file_path:
                    try:
                        result = rag_service.upload_document_with_metadata(
                            document.file_path,
                            company,
                            document.document_type,
                            document.title,
                            document.tags
                        )
                        if result['success']:
                            success_count += 1
                    except Exception as e:
                        logger.error(f"문서 업로드 실패: {document.title} - {e}")
            
            return JsonResponse({
                'success': True,
                'message': f'{company} 인덱스 업데이트 완료: {success_count}개 문서',
                'updated_count': success_count
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'POST 요청만 지원합니다.'})

@admin_required
def delete_company_data(request):
    """보험사별 데이터 삭제"""
    if request.method == 'DELETE':
        try:
            import json
            data = json.loads(request.body)
            company = data.get('company')
            
            if not company:
                return JsonResponse({'success': False, 'error': '보험사 정보가 누락되었습니다.'})
            
            rag_service = RAGService()
            
            # Pinecone에서 해당 보험사 데이터 삭제
            if rag_service.pinecone_index:
                # 보험사별 필터로 벡터 삭제
                rag_service.pinecone_index.delete(filter={"company": company})
            
            return JsonResponse({
                'success': True,
                'message': f'{company} 데이터 삭제 완료'
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'DELETE 요청만 지원합니다.'})

@admin_required
def update_all_index(request):
    """전체 인덱스 업데이트"""
    if request.method == 'POST':
        try:
            rag_service = RAGService()
            
            # 기존 인덱스 초기화
            if rag_service.pinecone_index:
                rag_service.pinecone_index.delete(delete_all=True)
            
            # 승인된 모든 문서 다시 업로드
            documents = PolicyDocument.objects.filter(status='approved')
            
            success_count = 0
            for document in documents:
                if document.file_path:
                    try:
                        result = rag_service.upload_document_with_metadata(
                            document.file_path,
                            document.company.name,
                            document.document_type,
                            document.title,
                            document.tags
                        )
                        if result['success']:
                            success_count += 1
                    except Exception as e:
                        logger.error(f"문서 업로드 실패: {document.title} - {e}")
            
            return JsonResponse({
                'success': True,
                'message': f'전체 인덱스 업데이트 완료: {success_count}개 문서',
                'updated_count': success_count
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'POST 요청만 지원합니다.'})

@admin_required
def clear_all_index(request):
    """전체 인덱스 초기화"""
    if request.method == 'DELETE':
        try:
            rag_service = RAGService()
            
            if rag_service.pinecone_index:
                rag_service.pinecone_index.delete(delete_all=True)
            
            return JsonResponse({
                'success': True,
                'message': '전체 인덱스 초기화 완료'
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'DELETE 요청만 지원합니다.'})

@admin_required
def get_pinecone_stats(request):
    """Pinecone 통계 조회"""
    try:
        rag_service = RAGService()
        stats = rag_service.get_company_document_stats()
        
        return JsonResponse({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@admin_required
def delete_document_api(request, document_id):
    """문서 삭제 API"""
    if request.method == 'DELETE':
        try:
            document = PolicyDocument.objects.get(id=document_id)
            
            # Pinecone에서 해당 문서 벡터 삭제
            rag_service = RAGService()
            if rag_service.pinecone_index:
                rag_service.pinecone_index.delete(
                    filter={
                        "source": document.file_path.split("/")[-1],
                        "company": document.company.name
                    }
                )
            
            # 데이터베이스에서 문서 삭제
            document.delete()
            
            return JsonResponse({
                'success': True,
                'message': '문서 삭제 완료'
            })
            
        except PolicyDocument.DoesNotExist:
            return JsonResponse({'success': False, 'error': '문서를 찾을 수 없습니다.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'DELETE 요청만 지원합니다.'})

def secure_filename(filename):
    """안전한 파일명 생성 (Django 내장 함수 사용)"""
    # 파일명에서 특수문자 제거
    filename = re.sub(r'[^\w\s-]', '', filename)
    # 공백을 언더스코어로 변경
    filename = re.sub(r'[-\s]+', '_', filename)
    return filename

def search_documents_api(request):
    """문서 검색 API"""
    if request.method == 'GET':
        try:
            query = request.GET.get('query', '')
            company = request.GET.get('company', '')
            top_k = int(request.GET.get('top_k', 5))
            
            if not query:
                return JsonResponse({'success': False, 'error': '검색어가 필요합니다.'})
            
            rag_service = RAGService()
            
            if company:
                results = rag_service.search_documents_by_company(query, company, top_k)
            else:
                results = rag_service.search_documents(query, top_k)
            
            return JsonResponse({
                'success': True,
                'results': results,
                'query': query,
                'company': company,
                'count': len(results)
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'GET 요청만 지원합니다.'})
