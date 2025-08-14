from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import UserProfile, InsuranceRecommendation, ChatHistory


class UserProfileInline(admin.StackedInline):
    """사용자 프로필을 User 모델에 인라인으로 표시"""

    model = UserProfile
    can_delete = False
    verbose_name_plural = "사용자 프로필"


class CustomUserAdmin(UserAdmin):
    """사용자 관리자 페이지 커스터마이징"""

    inlines = (UserProfileInline,)
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "get_profile_info",
    )

    def get_profile_info(self, obj):
        """프로필 정보 표시"""
        if hasattr(obj, "profile"):
            return f"{obj.profile.get_age_group()}, {obj.profile.get_gender_display()}"
        return "프로필 없음"

    get_profile_info.short_description = "프로필 정보"


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """사용자 프로필 관리"""

    list_display = (
        "user",
        "birth_date",
        "gender",
        "residence_area",
        "car_type",
        "annual_mileage",
        "accident_history",
        "created_at",
    )
    list_filter = (
        "gender",
        "residence_area",
        "car_type",
        "coverage_level",
        "accident_history",
        "additional_coverage_interest",
        "created_at",
    )
    search_fields = ("user__username", "user__first_name", "user__last_name")
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("사용자 정보", {"fields": ("user", "birth_date", "gender", "residence_area")}),
        ("운전 정보", {"fields": ("driving_experience", "accident_history")}),
        ("자동차 정보", {"fields": ("car_type", "annual_mileage")}),
        ("보험 정보", {"fields": ("coverage_level", "additional_coverage_interest")}),
        (
            "시간 정보",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(InsuranceRecommendation)
class InsuranceRecommendationAdmin(admin.ModelAdmin):
    """보험 추천 내역 관리"""

    list_display = (
        "user",
        "session_id",
        "recommendation_mode",
        "is_selected",
        "selected_company",
        "user_rating",
        "created_at",
    )
    list_filter = ("recommendation_mode", "is_selected", "user_rating", "created_at")
    search_fields = ("user__username", "session_id", "selected_company")
    readonly_fields = ("created_at", "session_id")

    fieldsets = (
        ("기본 정보", {"fields": ("user", "session_id", "recommendation_mode")}),
        (
            "추천 데이터",
            {
                "fields": (
                    "user_profile_snapshot",
                    "recommendations_data",
                    "recommendation_reason",
                )
            },
        ),
        ("사용자 선택", {"fields": ("is_selected", "selected_company")}),
        ("사용자 평가", {"fields": ("user_rating", "user_feedback")}),
        ("시간 정보", {"fields": ("created_at",), "classes": ("collapse",)}),
    )


@admin.register(ChatHistory)
class ChatHistoryAdmin(admin.ModelAdmin):
    """채팅 내역 관리"""

    list_display = (
        "user",
        "message_type",
        "session_id",
        "content_preview",
        "created_at",
    )
    list_filter = ("message_type", "created_at")
    search_fields = ("user__username", "content", "session_id")
    readonly_fields = ("created_at",)

    def content_preview(self, obj):
        """메시지 내용 미리보기"""
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content

    content_preview.short_description = "메시지 내용"

    fieldsets = (
        ("기본 정보", {"fields": ("user", "message_type", "session_id")}),
        ("메시지 내용", {"fields": ("content",)}),
        ("시간 정보", {"fields": ("created_at",), "classes": ("collapse",)}),
    )


# 기존 User 모델을 커스텀 관리자로 교체
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
