from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import UserProfile, MLRecommendation


class UserProfileInline(admin.StackedInline):
    """User 모델에 UserProfile을 인라인으로 추가"""

    model = UserProfile
    can_delete = False
    verbose_name_plural = "프로필"
    fk_name = "user"


class CustomUserAdmin(UserAdmin):
    """커스텀 User 관리자"""

    inlines = (UserProfileInline,)
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "get_profile_info",
    )
    list_filter = ("is_staff", "is_superuser", "is_active", "groups")
    search_fields = ("username", "first_name", "last_name", "email")

    def get_profile_info(self, obj):
        """프로필 정보 표시"""
        if hasattr(obj, "profile"):
            return f"차량: {obj.profile.car_number or '없음'}, 경력: {obj.profile.driving_experience}년"
        return "프로필 없음"

    get_profile_info.short_description = "프로필 정보"


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """UserProfile 관리자"""

    list_display = (
        "user",
        "car_number",
        "driving_experience",
        "gender",
        "age",
        "residence_area",
        "satisfaction_score",
    )
    list_filter = (
        "gender",
        "driving_experience",
        "residence_area",
        "satisfaction_score",
    )
    search_fields = ("user__username", "user__email", "car_number", "residence_area")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            "사용자 정보",
            {"fields": ("user", "gender", "age", "occupation", "residence_area")},
        ),
        (
            "운전 정보",
            {
                "fields": (
                    "car_number",
                    "driving_experience",
                    "annual_mileage",
                    "accident_history",
                    "car_info",
                )
            },
        ),
        (
            "보험 정보",
            {"fields": ("selected_insurance", "satisfaction_score", "selection_date")},
        ),
        (
            "시스템 정보",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(MLRecommendation)
class MLRecommendationAdmin(admin.ModelAdmin):
    """MLRecommendation 관리자"""

    list_display = (
        "user",
        "recommendation_date",
        "get_recommended_products_count",
        "get_similar_users_count",
        "user_feedback",
        "is_viewed",
        "is_selected",
    )
    list_filter = ("recommendation_date", "user_feedback", "is_viewed", "is_selected")
    search_fields = ("user__username", "user__email")
    readonly_fields = ("recommendation_date",)
    fieldsets = (
        ("기본 정보", {"fields": ("user", "recommendation_date", "user_feedback")}),
        (
            "추천 정보",
            {"fields": ("recommended_products", "ml_scores", "similar_users")},
        ),
        ("상태 정보", {"fields": ("is_viewed", "is_selected")}),
    )

    def get_recommended_products_count(self, obj):
        """추천 상품 개수 표시"""
        return obj.get_recommended_products_count()

    get_recommended_products_count.short_description = "추천 상품 수"

    def get_similar_users_count(self, obj):
        """유사 사용자 개수 표시"""
        return obj.get_similar_users_count()

    get_similar_users_count.short_description = "유사 사용자 수"


# 기존 User 관리자를 커스텀 관리자로 교체
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
