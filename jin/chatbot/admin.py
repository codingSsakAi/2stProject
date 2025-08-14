from django.contrib import admin
from .models import (
    InsuranceCompany,
    InsuranceDocument,
    DocumentChunk,
    ChatSession,
    ChatHistory,
    InsuranceMockData,
)


@admin.register(InsuranceCompany)
class InsuranceCompanyAdmin(admin.ModelAdmin):
    """보험사 관리"""

    list_display = ("name", "code", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("name", "code")
    ordering = ("name",)

    fieldsets = (
        ("보험사 정보", {"fields": ("name", "code", "is_active")}),
        (
            "시간 정보",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(InsuranceDocument)
class InsuranceDocumentAdmin(admin.ModelAdmin):
    """보험 약관 문서 관리"""

    list_display = (
        "title",
        "insurance_company",
        "status",
        "uploaded_by",
        "uploaded_at",
        "processed_at",
    )
    list_filter = ("status", "insurance_company", "uploaded_at", "processed_at")
    search_fields = ("title", "insurance_company__name", "uploaded_by__username")
    readonly_fields = ("uploaded_at", "processed_at")

    fieldsets = (
        ("문서 정보", {"fields": ("title", "insurance_company", "status")}),
        ("파일 정보", {"fields": ("pdf_file", "txt_file")}),
        ("처리 정보", {"fields": ("uploaded_by", "uploaded_at", "processed_at")}),
        ("오류 정보", {"fields": ("error_message",), "classes": ("collapse",)}),
    )


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    """문서 청크 관리"""

    list_display = ("document", "chunk_index", "chunk_preview", "created_at")
    list_filter = ("document__insurance_company", "created_at")
    search_fields = ("document__title", "chunk_text")
    readonly_fields = ("created_at",)

    def chunk_preview(self, obj):
        """청크 텍스트 미리보기"""
        return (
            obj.chunk_text[:100] + "..."
            if len(obj.chunk_text) > 100
            else obj.chunk_text
        )

    chunk_preview.short_description = "청크 내용"

    fieldsets = (
        ("문서 정보", {"fields": ("document", "chunk_index")}),
        ("청크 내용", {"fields": ("chunk_text",)}),
        ("시간 정보", {"fields": ("created_at",), "classes": ("collapse",)}),
    )


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    """채팅 세션 관리"""

    list_display = ("user", "title", "is_active", "created_at", "updated_at")
    list_filter = ("is_active", "created_at", "updated_at")
    search_fields = ("user__username", "title")
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("사용자 정보", {"fields": ("user", "title")}),
        ("세션 정보", {"fields": ("is_active",)}),
        ("시간 정보", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(ChatHistory)
class ChatHistoryAdmin(admin.ModelAdmin):
    """채팅 기록 관리"""

    list_display = ("user", "session", "message_preview", "is_user", "created_at")
    list_filter = ("is_user", "session", "created_at")
    search_fields = ("user__username", "session__title", "message")
    readonly_fields = ("created_at",)

    def message_preview(self, obj):
        """메시지 미리보기"""
        return obj.message[:100] + "..." if len(obj.message) > 100 else obj.message

    message_preview.short_description = "메시지 내용"

    fieldsets = (
        ("사용자 정보", {"fields": ("user", "session")}),
        ("메시지 정보", {"fields": ("message", "is_user", "metadata")}),
        ("시간 정보", {"fields": ("created_at",), "classes": ("collapse",)}),
    )


@admin.register(InsuranceMockData)
class InsuranceMockDataAdmin(admin.ModelAdmin):
    """보험 Mock 데이터 관리"""

    list_display = ("insurance_company", "insurance_name", "base_premium", "created_at")
    list_filter = ("insurance_company", "created_at")
    search_fields = ("insurance_company__name", "insurance_name")
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (
            "보험 정보",
            {"fields": ("insurance_company", "insurance_name", "base_premium")},
        ),
        (
            "연령별 할증율",
            {
                "fields": (
                    "age_20s_rate",
                    "age_30s_rate",
                    "age_40s_rate",
                    "age_50s_rate",
                    "age_60s_rate",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "성별 할증율",
            {"fields": ("male_rate", "female_rate"), "classes": ("collapse",)},
        ),
        (
            "차량 크기별 할증율",
            {
                "fields": (
                    "small_car_rate",
                    "medium_car_rate",
                    "large_car_rate",
                    "suv_rate",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "주행거리별 할증율",
            {
                "fields": ("low_mileage_rate", "high_mileage_rate"),
                "classes": ("collapse",),
            },
        ),
        (
            "사고경력별 할증율",
            {"fields": ("no_accident_rate", "accident_rate"), "classes": ("collapse",)},
        ),
        (
            "시간 정보",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )
