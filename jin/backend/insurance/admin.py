from django.contrib import admin
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils.html import format_html
from django.urls import reverse
from django.shortcuts import redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import fitz
from docx import Document
import os
import json
from .models import (
    InsuranceCompany,
    PolicyDocument,
    InsuranceQuote,
    ChatSession,
    ChatMessage,
)
# from .services import rag_service  # 임시로 주석 처리


@admin.register(InsuranceCompany)
class InsuranceCompanyAdmin(admin.ModelAdmin):
    """보험사 관리자"""

    list_display = ("name", "code", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("name", "code")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("name",)


@admin.register(PolicyDocument)
class PolicyDocumentAdmin(admin.ModelAdmin):
    """보험 약관 문서 관리자"""

    list_display = (
        "company",
        "document_type",
        "version",
        "get_file_name",
        "get_file_size_mb",
        "page_count",
        "is_active",
        "upload_date",
    )
    list_filter = ("company", "document_type", "is_active", "upload_date")
    search_fields = ("company__name", "file_path")
    readonly_fields = ("upload_date", "file_size", "page_count", "pinecone_index_id")
    actions = ["convert_pdf_to_docx", "upload_to_pinecone", "search_documents", "get_index_stats"]

    fieldsets = (
        ("기본 정보", {"fields": ("company", "document_type", "version", "is_active")}),
        (
            "파일 정보",
            {"fields": ("file_path", "file_size", "page_count", "upload_date")},
        ),
        ("Pinecone 연동", {"fields": ("pinecone_index_id",), "classes": ("collapse",)}),
    )

    def get_file_name(self, obj):
        """파일명 표시"""
        return obj.get_file_name()

    get_file_name.short_description = "파일명"

    def get_file_size_mb(self, obj):
        """파일 크기 표시"""
        return f"{obj.get_file_size_mb()} MB"

    get_file_size_mb.short_description = "파일 크기"

    def convert_pdf_to_docx(self, request, queryset):
        """PDF를 DOCX로 변환"""
        converted_count = 0
        for document in queryset:
            if document.document_type == "PDF":
                try:
                    # PDF 파일 경로
                    pdf_path = document.file_path
                    if not os.path.exists(pdf_path):
                        messages.error(
                            request, f"PDF 파일을 찾을 수 없습니다: {pdf_path}"
                        )
                        continue

                    # DOCX 파일 경로 생성
                    docx_path = pdf_path.replace(".pdf", ".docx")

                    # PDF 텍스트 추출 및 DOCX 생성
                    doc = fitz.open(pdf_path)
                    document_docx = Document()

                    for page in doc:
                        text = page.get_text()
                        document_docx.add_paragraph(text)

                    # DOCX 파일 저장
                    document_docx.save(docx_path)
                    doc.close()

                    # 새로운 PolicyDocument 생성
                    new_document = PolicyDocument.objects.create(
                        company=document.company,
                        document_type="DOCX",
                        file_path=docx_path,
                        version=document.version,
                        file_size=os.path.getsize(docx_path),
                        page_count=document.page_count,
                    )

                    converted_count += 1
                    messages.success(
                        request,
                        f"변환 완료: {document.get_file_name()} -> {new_document.get_file_name()}",
                    )

                except Exception as e:
                    messages.error(
                        request, f"변환 실패: {document.get_file_name()} - {str(e)}"
                    )

        if converted_count > 0:
            messages.success(
                request, f"{converted_count}개 파일이 성공적으로 변환되었습니다."
            )
        else:
            messages.warning(request, "변환할 PDF 파일이 없습니다.")

    convert_pdf_to_docx.short_description = "선택된 PDF를 DOCX로 변환"

    def update_pinecone_index(self, request, queryset):
        """Pinecone 인덱스 업데이트"""
        updated_count = 0
        for document in queryset:
            try:
                # Pinecone 인덱스 업데이트 로직 (추후 구현)
                document.pinecone_index_id = (
                    f"index_{document.company.code}_{document.version}"
                )
                document.save()
                updated_count += 1
                messages.success(
                    request, f"인덱스 업데이트 완료: {document.get_file_name()}"
                )
            except Exception as e:
                messages.error(
                    request,
                    f"인덱스 업데이트 실패: {document.get_file_name()} - {str(e)}",
                )

        if updated_count > 0:
            messages.success(
                request, f"{updated_count}개 문서의 인덱스가 업데이트되었습니다."
            )

    def upload_to_pinecone(self, request, queryset):
        """선택된 문서를 Pinecone에 업로드"""
        messages.info(request, "Pinecone 업로드 기능은 현재 비활성화되어 있습니다.")
    
    upload_to_pinecone.short_description = "Pinecone에 문서 업로드"
    
    def search_documents(self, request, queryset):
        """문서 검색 테스트"""
        # 검색 기능은 별도 뷰로 구현
        messages.info(request, "검색 기능은 별도 페이지에서 사용할 수 있습니다.")
    
    search_documents.short_description = "문서 검색 테스트"
    
    def get_index_stats(self, request, queryset):
        """인덱스 통계 정보"""
        messages.info(request, "인덱스 통계 기능은 현재 비활성화되어 있습니다.")
    
    get_index_stats.short_description = "인덱스 통계 조회"


@admin.register(InsuranceQuote)
class InsuranceQuoteAdmin(admin.ModelAdmin):
    """보험 견적 관리자"""

    list_display = (
        "user",
        "company",
        "annual_premium",
        "monthly_premium",
        "coverage_level",
        "customer_satisfaction",
        "calculation_date",
    )
    list_filter = ("company", "coverage_level", "calculation_date")
    search_fields = ("user__username", "company__name")
    readonly_fields = ("calculation_date",)
    fieldsets = (
        ("기본 정보", {"fields": ("user", "company", "calculation_date")}),
        (
            "보험료 정보",
            {"fields": ("annual_premium", "monthly_premium", "coverage_level")},
        ),
        (
            "상세 정보",
            {
                "fields": (
                    "coverage_details",
                    "special_discount",
                    "discount_rate",
                    "penalty_rate",
                    "deductible",
                )
            },
        ),
        (
            "추가 정보",
            {
                "fields": (
                    "payment_options",
                    "additional_benefits",
                    "customer_satisfaction",
                    "claim_service_rating",
                )
            },
        ),
    )


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    """채팅 세션 관리자"""

    list_display = (
        "user",
        "session_id",
        "is_active",
        "created_at",
        "get_message_count",
    )
    list_filter = ("is_active", "created_at")
    search_fields = ("user__username", "session_id")
    readonly_fields = ("session_id", "created_at", "updated_at")

    def get_message_count(self, obj):
        """메시지 개수 표시"""
        return obj.messages.count()

    get_message_count.short_description = "메시지 수"


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    """채팅 메시지 관리자"""

    list_display = ("session", "message_type", "get_content_preview", "timestamp")
    list_filter = ("message_type", "timestamp")
    search_fields = ("session__user__username", "content")
    readonly_fields = ("timestamp",)

    def get_content_preview(self, obj):
        """메시지 내용 미리보기"""
        content = obj.content[:50]
        return f"{content}..." if len(obj.content) > 50 else content

    get_content_preview.short_description = "메시지 내용"
