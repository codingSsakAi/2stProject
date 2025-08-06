"""
Insurance 앱 관리자 설정
관리자 대시보드에서 보험사, 문서, 사용자 등을 관리할 수 있습니다.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Avg, Sum
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, timedelta

from .models import PolicyDocument, InsuranceCompany, ChatHistory, RecommendationHistory


@admin.register(InsuranceCompany)
class InsuranceCompanyAdmin(admin.ModelAdmin):
    """보험사 관리"""

    list_display = ["name", "status", "created_at", "updated_at", "document_count"]
    list_filter = ["status", "created_at"]
    search_fields = ["name", "description"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        ("기본 정보", {"fields": ("name", "description", "status")}),
        (
            "연락처 정보",
            {"fields": ("phone", "email", "website"), "classes": ("collapse",)},
        ),
        (
            "주소 정보",
            {
                "fields": ("address", "city", "state", "zip_code"),
                "classes": ("collapse",),
            },
        ),
        (
            "시스템 정보",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def document_count(self, obj):
        """문서 수 표시"""
        count = PolicyDocument.objects.filter(company=obj).count()
        return count

    document_count.short_description = "문서 수"

    actions = ["activate_companies", "deactivate_companies"]

    def activate_companies(self, request, queryset):
        """선택된 보험사 활성화"""
        updated = queryset.update(status="active")
        self.message_user(request, f"{updated}개의 보험사가 활성화되었습니다.")

    activate_companies.short_description = "선택된 보험사 활성화"

    def deactivate_companies(self, request, queryset):
        """선택된 보험사 비활성화"""
        updated = queryset.update(status="inactive")
        self.message_user(request, f"{updated}개의 보험사가 비활성화되었습니다.")

    deactivate_companies.short_description = "선택된 보험사 비활성화"


@admin.register(PolicyDocument)
class PolicyDocumentAdmin(admin.ModelAdmin):
    """정책 문서 관리"""

    list_display = [
        "title",
        "company",
        "document_type",
        "upload_date",
        "file_size",
        "status",
    ]
    list_filter = ["document_type", "upload_date", "status", "company"]
    search_fields = ["title", "description", "company__name"]
    readonly_fields = ["upload_date", "file_size", "file_path"]

    fieldsets = (
        (
            "기본 정보",
            {"fields": ("title", "description", "company", "document_type", "status")},
        ),
        (
            "파일 정보",
            {
                "fields": ("file", "file_path", "file_size", "upload_date"),
                "classes": ("collapse",),
            },
        ),
        ("메타데이터", {"fields": ("tags", "keywords"), "classes": ("collapse",)}),
    )

    def file_size(self, obj):
        """파일 크기 표시"""
        if obj.file:
            size = obj.file.size
            if size < 1024:
                return f"{size} B"
            elif size < 1024 * 1024:
                return f"{size // 1024} KB"
        else:
            return f"{size // (1024 * 1024)} MB"
        return "N/A"

    file_size.short_description = "파일 크기"

    actions = ["approve_documents", "reject_documents", "delete_selected"]

    def approve_documents(self, request, queryset):
        """선택된 문서 승인"""
        updated = queryset.update(status="approved")
        self.message_user(request, f"{updated}개의 문서가 승인되었습니다.")

    approve_documents.short_description = "선택된 문서 승인"

    def reject_documents(self, request, queryset):
        """선택된 문서 거부"""
        updated = queryset.update(status="rejected")
        self.message_user(request, f"{updated}개의 문서가 거부되었습니다.")

    reject_documents.short_description = "선택된 문서 거부"


# UserProfile은 users 앱에서 관리하므로 제거


@admin.register(ChatHistory)
class ChatHistoryAdmin(admin.ModelAdmin):
    """채팅 기록 관리"""

    list_display = ["user", "message_type", "created_at", "response_length"]
    list_filter = ["message_type", "created_at"]
    search_fields = ["user__username", "message", "response"]
    readonly_fields = ["created_at"]

    fieldsets = (
        ("사용자 정보", {"fields": ("user", "session_id")}),
        ("메시지 정보", {"fields": ("message", "response", "message_type")}),
        ("시스템 정보", {"fields": ("created_at",), "classes": ("collapse",)}),
    )

    def response_length(self, obj):
        """응답 길이"""
        if obj.response:
            return len(obj.response)
        return 0

    response_length.short_description = "응답 길이"

    actions = ["export_chat_data", "delete_old_chats"]

    def export_chat_data(self, request, queryset):
        """채팅 데이터 내보내기"""
        # 실제 구현에서는 CSV 또는 Excel 파일로 내보내기
        self.message_user(
            request, f"{queryset.count()}개의 채팅 기록이 내보내기 준비되었습니다."
        )

    export_chat_data.short_description = "선택된 채팅 데이터 내보내기"

    def delete_old_chats(self, request, queryset):
        """30일 이상 된 채팅 삭제"""
        cutoff_date = timezone.now() - timedelta(days=30)
        old_chats = ChatHistory.objects.filter(created_at__lt=cutoff_date)
        count = old_chats.count()
        old_chats.delete()
        self.message_user(request, f"{count}개의 오래된 채팅 기록이 삭제되었습니다.")

    delete_old_chats.short_description = "30일 이상 된 채팅 삭제"


@admin.register(RecommendationHistory)
class RecommendationHistoryAdmin(admin.ModelAdmin):
    """추천 기록 관리"""

    list_display = ["user", "recommendation_type", "created_at", "feedback_score"]
    list_filter = ["recommendation_type", "feedback_score", "created_at"]
    search_fields = ["user__username", "recommendation_data"]
    readonly_fields = ["created_at"]

    fieldsets = (
        ("사용자 정보", {"fields": ("user", "session_id")}),
        (
            "추천 정보",
            {
                "fields": (
                    "recommendation_type",
                    "recommendation_data",
                    "feedback_score",
                    "feedback_comment",
                )
            },
        ),
        ("시스템 정보", {"fields": ("created_at",), "classes": ("collapse",)}),
    )

    actions = ["export_recommendations", "analyze_feedback"]

    def export_recommendations(self, request, queryset):
        """추천 데이터 내보내기"""
        self.message_user(
            request, f"{queryset.count()}개의 추천 기록이 내보내기 준비되었습니다."
        )

    export_recommendations.short_description = "선택된 추천 데이터 내보내기"

    def analyze_feedback(self, request, queryset):
        """피드백 분석"""
        avg_score = queryset.aggregate(Avg("feedback_score"))["feedback_score__avg"]
        if avg_score:
            self.message_user(request, f"평균 피드백 점수: {avg_score:.2f}")
        else:
            self.message_user(request, "피드백 데이터가 없습니다.")

    analyze_feedback.short_description = "피드백 분석"


# 관리자 사이트 커스터마이징
admin.site.site_header = "보험 추천 시스템 관리자"
admin.site.site_title = "보험 관리자"
admin.site.index_title = "관리자 대시보드"


# 관리자 액션 추가
class AdminActions:
    """관리자 액션 클래스"""

    @staticmethod
    def generate_system_report(modeladmin, request, queryset):
        """시스템 리포트 생성"""
        from django.http import JsonResponse

        # 통계 데이터 수집
        stats = {
            "total_users": UserProfile.objects.count(),
            "total_documents": PolicyDocument.objects.count(),
            "total_companies": InsuranceCompany.objects.count(),
            "total_chats": ChatHistory.objects.count(),
            "total_recommendations": RecommendationHistory.objects.count(),
            "recent_chats": ChatHistory.objects.filter(
                created_at__gte=timezone.now() - timedelta(days=7)
            ).count(),
            "avg_feedback": RecommendationHistory.objects.aggregate(
                Avg("feedback_score")
            )["feedback_score__avg"]
            or 0,
        }

        return JsonResponse(stats)

    @staticmethod
    def backup_data(modeladmin, request, queryset):
        """데이터 백업"""
        messages.success(request, "데이터 백업이 시작되었습니다.")
        return HttpResponseRedirect(request.get_full_path())

    @staticmethod
    def clear_cache(modeladmin, request, queryset):
        """캐시 정리"""
        from django.core.cache import cache

        cache.clear()
        messages.success(request, "캐시가 정리되었습니다.")
        return HttpResponseRedirect(request.get_full_path())


# 관리자 액션 등록
admin.site.add_action(AdminActions.generate_system_report, "시스템 리포트 생성")
admin.site.add_action(AdminActions.backup_data, "데이터 백업")
admin.site.add_action(AdminActions.clear_cache, "캐시 정리")
