import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg
from django.utils import timezone
from datetime import datetime, timedelta
import json

from .models import (
    InsuranceDocument,
    DocumentChunk,
    InsuranceCompany,
    ChatSession,
    ChatHistory,
)
from .forms import DocumentUploadForm
from .utils import PDFProcessor
from .services import DocumentEmbeddingService
from .enhanced_search import EnhancedSearchService
from .search_metrics import SearchPerformanceMonitor
from .metadata_service import MetadataService
from .decorators import admin_required
from .services import DocumentService, EmbeddingService

logger = logging.getLogger(__name__)


@admin_required
def enhanced_document_list_view(request):
    """향상된 문서 목록 뷰 (메타데이터 표시, 필터링, 검색)"""
    try:
        # 필터링 파라미터
        category_filter = request.GET.get("category")
        company_filter = request.GET.get("company")
        status_filter = request.GET.get("status")
        search_query = request.GET.get("search")
        date_from = request.GET.get("date_from")
        date_to = request.GET.get("date_to")

        # 기본 쿼리셋
        documents = InsuranceDocument.objects.select_related("insurance_company").all()

        # 필터링 적용
        if category_filter:
            documents = documents.filter(chunks__category=category_filter).distinct()

        if company_filter:
            documents = documents.filter(
                insurance_company__name__icontains=company_filter
            )

        if status_filter:
            documents = documents.filter(status=status_filter)

        if search_query:
            documents = documents.filter(
                Q(title__icontains=search_query)
                | Q(insurance_company__name__icontains=search_query)
                | Q(chunks__title__icontains=search_query)
            ).distinct()

        if date_from:
            documents = documents.filter(uploaded_at__gte=date_from)

        if date_to:
            documents = documents.filter(uploaded_at__lte=date_to)

        # 정렬
        sort_by = request.GET.get("sort", "-uploaded_at")
        documents = documents.order_by(sort_by)

        # 페이징
        paginator = Paginator(documents, 20)
        page_number = request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)

        # 통계 정보
        total_documents = documents.count()
        total_chunks = DocumentChunk.objects.count()
        avg_confidence = (
            DocumentChunk.objects.aggregate(avg_confidence=Avg("confidence_score"))[
                "avg_confidence"
            ]
            or 0
        )

        # 카테고리별 통계
        category_stats = (
            DocumentChunk.objects.values("category")
            .annotate(count=Count("id"), avg_confidence=Avg("confidence_score"))
            .order_by("-count")
        )

        # 보험사별 통계
        company_stats = (
            documents.values("insurance_company__name")
            .annotate(count=Count("id"), total_chunks=Count("chunks"))
            .order_by("-count")
        )

        # 필터 옵션
        categories = DocumentChunk.objects.values_list("category", flat=True).distinct()
        companies = InsuranceCompany.objects.all()
        statuses = InsuranceDocument.objects.values_list("status", flat=True).distinct()

        context = {
            "title": "향상된 문서 관리",
            "page_obj": page_obj,
            "total_documents": total_documents,
            "total_chunks": total_chunks,
            "avg_confidence": round(avg_confidence, 3),
            "category_stats": category_stats,
            "company_stats": company_stats,
            "categories": categories,
            "companies": companies,
            "statuses": statuses,
            "filters": {
                "category": category_filter,
                "company": company_filter,
                "status": status_filter,
                "search": search_query,
                "date_from": date_from,
                "date_to": date_to,
                "sort": sort_by,
            },
        }

        return render(request, "chatbot/enhanced_document_list.jinja.html", context)

    except Exception as e:
        logger.error(f"향상된 문서 목록 뷰 오류: {e}")
        messages.error(
            request, f"문서 목록을 불러오는 중 오류가 발생했습니다: {str(e)}"
        )
        return redirect("chatbot:document_list")


@admin_required
def enhanced_document_detail_view(request, document_id):
    """향상된 문서 상세 뷰 (메타데이터 편집, 재처리)"""
    try:
        document = get_object_or_404(InsuranceDocument, id=document_id)

        # 청크 정보 (메타데이터 포함)
        chunks = document.chunks.all().order_by("chunk_index")

        # 메타데이터 통계
        metadata_service = MetadataService()
        chunk_data = []
        for chunk in chunks:
            chunk_data.append(
                {
                    "id": chunk.id,
                    "title": chunk.title,
                    "category": chunk.category,
                    "article_number": chunk.article_number,
                    "keywords": chunk.keywords,
                    "summary": chunk.summary,
                    "confidence_score": chunk.confidence_score,
                    "review_status": chunk.review_status,
                }
            )

        metadata_stats = metadata_service.get_metadata_statistics(chunk_data)

        # 재처리 가능 여부 확인
        can_reprocess = document.status in ["completed", "error"]

        context = {
            "title": f"문서 상세 - {document.title}",
            "document": document,
            "chunks": chunks,
            "metadata_stats": metadata_stats,
            "can_reprocess": can_reprocess,
        }

        return render(request, "chatbot/enhanced_document_detail.jinja.html", context)

    except Exception as e:
        logger.error(f"향상된 문서 상세 뷰 오류: {e}")
        messages.error(
            request, f"문서 상세 정보를 불러오는 중 오류가 발생했습니다: {str(e)}"
        )
        return redirect("chatbot:document_list")


@admin_required
def enhanced_document_search_view(request):
    """향상된 문서 검색 뷰 (고급 검색, 하이라이팅)"""
    try:
        query = request.GET.get("q", "")
        category_filter = request.GET.get("category")
        company_filter = request.GET.get("company")
        article_number = request.GET.get("article_number")

        search_results = []
        search_stats = {}

        if query:
            # 향상된 검색 서비스 초기화
            embedding_service = EmbeddingService()
            document_service = DocumentService(embedding_service)
            enhanced_search = EnhancedSearchService(document_service, embedding_service)

            # 검색 수행
            search_results = enhanced_search.enhanced_search(
                query=query,
                category_filter=category_filter,
                insurance_company=company_filter,
                article_number=article_number,
                use_metadata=True,
            )

            # 검색 통계
            search_stats = enhanced_search.get_search_statistics(search_results)

        # 필터 옵션
        categories = DocumentChunk.objects.values_list("category", flat=True).distinct()
        companies = InsuranceCompany.objects.all()

        context = {
            "title": "향상된 문서 검색",
            "query": query,
            "search_results": search_results,
            "search_stats": search_stats,
            "categories": categories,
            "companies": companies,
            "filters": {
                "category": category_filter,
                "company": company_filter,
                "article_number": article_number,
            },
        }

        return render(request, "chatbot/enhanced_document_search.jinja.html", context)

    except Exception as e:
        logger.error(f"향상된 문서 검색 뷰 오류: {e}")
        messages.error(request, f"문서 검색 중 오류가 발생했습니다: {str(e)}")
        return render(
            request,
            "chatbot/enhanced_document_search.jinja.html",
            {"title": "향상된 문서 검색"},
        )


@admin_required
def enhanced_embedding_stats_view(request):
    """향상된 Embedding 통계 뷰 (시각화, 성능 메트릭)"""
    try:
        # 기본 통계
        total_documents = InsuranceDocument.objects.count()
        total_chunks = DocumentChunk.objects.count()
        total_companies = InsuranceCompany.objects.count()

        # 메타데이터 통계
        metadata_service = MetadataService()
        chunk_data = []
        for chunk in DocumentChunk.objects.all():
            chunk_data.append(
                {
                    "category": chunk.category,
                    "confidence_score": chunk.confidence_score,
                    "review_status": chunk.review_status,
                    "extraction_method": chunk.extraction_method,
                }
            )

        metadata_stats = metadata_service.get_metadata_statistics(chunk_data)

        # 검색 성능 통계
        performance_monitor = SearchPerformanceMonitor()
        monitoring_data = performance_monitor.get_monitoring_data()

        # 시간별 통계 (최근 30일)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        daily_stats = []

        for i in range(30):
            date = thirty_days_ago + timedelta(days=i)
            next_date = date + timedelta(days=1)

            daily_docs = InsuranceDocument.objects.filter(
                uploaded_at__gte=date, uploaded_at__lt=next_date
            ).count()

            daily_chunks = DocumentChunk.objects.filter(
                created_at__gte=date, created_at__lt=next_date
            ).count()

            daily_stats.append(
                {
                    "date": date.strftime("%Y-%m-%d"),
                    "documents": daily_docs,
                    "chunks": daily_chunks,
                }
            )

        # 카테고리별 분포
        category_distribution = (
            DocumentChunk.objects.values("category")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        # 신뢰도 분포
        confidence_distribution = {
            "high": DocumentChunk.objects.filter(confidence_score__gte=0.8).count(),
            "medium": DocumentChunk.objects.filter(
                confidence_score__gte=0.6, confidence_score__lt=0.8
            ).count(),
            "low": DocumentChunk.objects.filter(confidence_score__lt=0.6).count(),
        }

        # 검토 상태 분포
        review_status_distribution = (
            DocumentChunk.objects.values("review_status")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        context = {
            "title": "향상된 Embedding 통계",
            "total_documents": total_documents,
            "total_chunks": total_chunks,
            "total_companies": total_companies,
            "metadata_stats": metadata_stats,
            "monitoring_data": monitoring_data,
            "daily_stats": daily_stats,
            "category_distribution": category_distribution,
            "confidence_distribution": confidence_distribution,
            "review_status_distribution": review_status_distribution,
        }

        return render(request, "chatbot/enhanced_embedding_stats.jinja.html", context)

    except Exception as e:
        logger.error(f"향상된 Embedding 통계 뷰 오류: {e}")
        messages.error(
            request, f"통계 정보를 불러오는 중 오류가 발생했습니다: {str(e)}"
        )
        return render(
            request,
            "chatbot/enhanced_embedding_stats.jinja.html",
            {"title": "향상된 Embedding 통계"},
        )


@admin_required
def enhanced_chat_management_view(request):
    """향상된 챗봇 상담 관리 뷰 (유사도, 소스, 카테고리 분석)"""
    try:
        # 필터링 파라미터
        user_filter = request.GET.get("user")
        date_from = request.GET.get("date_from")
        date_to = request.GET.get("date_to")
        category_filter = request.GET.get("category")

        # 채팅 세션 조회
        chat_sessions = ChatSession.objects.select_related("user").all()

        if user_filter:
            chat_sessions = chat_sessions.filter(user__username__icontains=user_filter)

        if date_from:
            chat_sessions = chat_sessions.filter(created_at__gte=date_from)

        if date_to:
            chat_sessions = chat_sessions.filter(created_at__lte=date_to)

        chat_sessions = chat_sessions.order_by("-created_at")

        # 페이징
        paginator = Paginator(chat_sessions, 20)
        page_number = request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)

        # 채팅 통계
        total_sessions = chat_sessions.count()
        total_messages = ChatHistory.objects.count()

        # 카테고리별 질문 분석
        category_questions = {}
        for session in chat_sessions:
            for message in session.messages.all():
                if message.role == "user":
                    # 메타데이터에서 카테고리 정보 추출
                    metadata = message.metadata or {}
                    categories = metadata.get("categories", [])
                    for category in categories:
                        if category not in category_questions:
                            category_questions[category] = 0
                        category_questions[category] += 1

        # 평균 유사도 점수
        avg_similarity = (
            ChatHistory.objects.filter(metadata__isnull=False).aggregate(
                avg_similarity=Avg("metadata__similarity_score")
            )["avg_similarity"]
            or 0
        )

        # 시간별 채팅 활동
        hourly_activity = []
        for hour in range(24):
            hour_start = timezone.now().replace(
                hour=hour, minute=0, second=0, microsecond=0
            )
            hour_end = hour_start + timedelta(hours=1)

            message_count = ChatHistory.objects.filter(
                created_at__gte=hour_start, created_at__lt=hour_end
            ).count()

            hourly_activity.append({"hour": hour, "count": message_count})

        context = {
            "title": "향상된 챗봇 상담 관리",
            "page_obj": page_obj,
            "total_sessions": total_sessions,
            "total_messages": total_messages,
            "category_questions": category_questions,
            "avg_similarity": round(avg_similarity, 3),
            "hourly_activity": hourly_activity,
            "filters": {
                "user": user_filter,
                "date_from": date_from,
                "date_to": date_to,
                "category": category_filter,
            },
        }

        return render(request, "chatbot/enhanced_chat_management.jinja.html", context)

    except Exception as e:
        logger.error(f"향상된 챗봇 상담 관리 뷰 오류: {e}")
        messages.error(
            request, f"채팅 관리 정보를 불러오는 중 오류가 발생했습니다: {str(e)}"
        )
        return render(
            request,
            "chatbot/enhanced_chat_management.jinja.html",
            {"title": "향상된 챗봇 상담 관리"},
        )


@admin_required
@csrf_exempt
@require_http_methods(["POST"])
def update_chunk_metadata_view(request, chunk_id):
    """청크 메타데이터 업데이트 API"""
    try:
        chunk = get_object_or_404(DocumentChunk, id=chunk_id)
        data = json.loads(request.body)

        # 메타데이터 업데이트
        if "title" in data:
            chunk.title = data["title"]
        if "category" in data:
            chunk.category = data["category"]
        if "article_number" in data:
            chunk.article_number = data["article_number"]
        if "keywords" in data:
            chunk.keywords = data["keywords"]
        if "summary" in data:
            chunk.summary = data["summary"]

        # 신뢰도 점수 재계산
        metadata_service = MetadataService()
        chunk_data = {
            "title": chunk.title,
            "category": chunk.category,
            "article_number": chunk.article_number,
            "keywords": chunk.keywords,
            "summary": chunk.summary,
        }

        validated_metadata = metadata_service._validate_and_postprocess(chunk_data)
        chunk.confidence_score = validated_metadata.get("confidence_score", 0.0)
        chunk.review_status = validated_metadata.get("review_status", "pending")

        chunk.save()

        return JsonResponse(
            {
                "success": True,
                "message": "메타데이터가 성공적으로 업데이트되었습니다.",
                "chunk": {
                    "id": chunk.id,
                    "title": chunk.title,
                    "category": chunk.category,
                    "article_number": chunk.article_number,
                    "keywords": chunk.keywords,
                    "summary": chunk.summary,
                    "confidence_score": chunk.confidence_score,
                    "review_status": chunk.review_status,
                },
            }
        )

    except Exception as e:
        logger.error(f"청크 메타데이터 업데이트 오류: {e}")
        return JsonResponse(
            {
                "success": False,
                "message": f"메타데이터 업데이트 중 오류가 발생했습니다: {str(e)}",
            },
            status=500,
        )


@admin_required
@csrf_exempt
@require_http_methods(["POST"])
def reprocess_document_metadata_view(request, document_id):
    """문서 메타데이터 재처리 API"""
    try:
        document = get_object_or_404(InsuranceDocument, id=document_id)

        # 메타데이터 서비스 초기화
        metadata_service = MetadataService()

        # 기존 청크들의 메타데이터 재처리
        chunks = document.chunks.all()
        processed_count = 0

        for chunk in chunks:
            try:
                # 메타데이터 재생성
                llm_metadata = metadata_service._generate_llm_metadata(chunk.chunk_text)

                # 기존 메타데이터와 통합
                combined_metadata = {
                    "title": llm_metadata.get("title", chunk.title),
                    "category": llm_metadata.get("category", chunk.category),
                    "article_number": chunk.article_number,  # 기존 값 유지
                    "keywords": llm_metadata.get("keywords", chunk.keywords),
                    "summary": llm_metadata.get("summary", chunk.summary),
                }

                # 검증 및 후처리
                final_metadata = metadata_service._validate_and_postprocess(
                    combined_metadata
                )

                # 청크 업데이트
                chunk.title = final_metadata.get("title", "")
                chunk.category = final_metadata.get("category", "기타")
                chunk.keywords = final_metadata.get("keywords", [])
                chunk.summary = final_metadata.get("summary", "")
                chunk.confidence_score = final_metadata.get("confidence_score", 0.0)
                chunk.review_status = final_metadata.get("review_status", "pending")
                chunk.extraction_method = "llm_reprocessed"
                chunk.updated_at = timezone.now()

                chunk.save()
                processed_count += 1

            except Exception as e:
                logger.error(f"청크 {chunk.id} 메타데이터 재처리 오류: {e}")
                continue

        return JsonResponse(
            {
                "success": True,
                "message": f"{processed_count}개 청크의 메타데이터가 재처리되었습니다.",
                "processed_count": processed_count,
                "total_count": chunks.count(),
            }
        )

    except Exception as e:
        logger.error(f"문서 메타데이터 재처리 오류: {e}")
        return JsonResponse(
            {
                "success": False,
                "message": f"메타데이터 재처리 중 오류가 발생했습니다: {str(e)}",
            },
            status=500,
        )


@admin_required
def export_metadata_view(request):
    """메타데이터 내보내기 뷰"""
    try:
        from django.http import HttpResponse
        import csv

        # 필터링 파라미터
        category_filter = request.GET.get("category")
        company_filter = request.GET.get("company")
        format_type = request.GET.get("format", "csv")

        # 쿼리셋 구성
        chunks = DocumentChunk.objects.select_related(
            "document", "document__insurance_company"
        ).all()

        if category_filter:
            chunks = chunks.filter(category=category_filter)

        if company_filter:
            chunks = chunks.filter(
                document__insurance_company__name__icontains=company_filter
            )

        if format_type == "csv":
            response = HttpResponse(content_type="text/csv; charset=utf-8")
            response["Content-Disposition"] = (
                'attachment; filename="metadata_export.csv"'
            )

            writer = csv.writer(response)
            writer.writerow(
                [
                    "문서ID",
                    "문서제목",
                    "보험사",
                    "청크ID",
                    "청크인덱스",
                    "제목",
                    "카테고리",
                    "조문번호",
                    "키워드",
                    "요약",
                    "신뢰도",
                    "검토상태",
                    "생성일시",
                ]
            )

            for chunk in chunks:
                writer.writerow(
                    [
                        chunk.document.id,
                        chunk.document.title,
                        chunk.document.insurance_company.name,
                        chunk.id,
                        chunk.chunk_index,
                        chunk.title or "",
                        chunk.category or "",
                        chunk.article_number or "",
                        ", ".join(chunk.keywords) if chunk.keywords else "",
                        chunk.summary or "",
                        chunk.confidence_score or 0.0,
                        chunk.review_status or "",
                        (
                            chunk.created_at.strftime("%Y-%m-%d %H:%M:%S")
                            if chunk.created_at
                            else ""
                        ),
                    ]
                )

            return response

        else:
            # JSON 형식
            data = []
            for chunk in chunks:
                data.append(
                    {
                        "document_id": chunk.document.id,
                        "document_title": chunk.document.title,
                        "insurance_company": chunk.document.insurance_company.name,
                        "chunk_id": chunk.id,
                        "chunk_index": chunk.chunk_index,
                        "title": chunk.title,
                        "category": chunk.category,
                        "article_number": chunk.article_number,
                        "keywords": chunk.keywords,
                        "summary": chunk.summary,
                        "confidence_score": chunk.confidence_score,
                        "review_status": chunk.review_status,
                        "created_at": (
                            chunk.created_at.isoformat() if chunk.created_at else None
                        ),
                    }
                )

            response = HttpResponse(
                json.dumps(data, ensure_ascii=False, indent=2),
                content_type="application/json; charset=utf-8",
            )
            response["Content-Disposition"] = (
                'attachment; filename="metadata_export.json"'
            )
            return response

    except Exception as e:
        logger.error(f"메타데이터 내보내기 오류: {e}")
        messages.error(request, f"메타데이터 내보내기 중 오류가 발생했습니다: {str(e)}")
        return redirect("chatbot:enhanced_document_list")
