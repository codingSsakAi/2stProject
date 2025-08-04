from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
import json


class UserProfile(models.Model):
    """사용자 프로필 모델 (ML 학습 데이터)"""

    GENDER_CHOICES = [
        ("M", "남성"),
        ("F", "여성"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    car_number = models.CharField(
        max_length=20, blank=True, null=True, verbose_name="자동차 번호"
    )
    driving_experience = models.IntegerField(default=0, verbose_name="운전 경력 (년)")
    gender = models.CharField(
        max_length=1, choices=GENDER_CHOICES, blank=True, null=True, verbose_name="성별"
    )
    age = models.IntegerField(blank=True, null=True, verbose_name="나이")
    occupation = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="직업"
    )
    residence_area = models.CharField(
        max_length=50, blank=True, null=True, verbose_name="거주지역"
    )
    annual_mileage = models.IntegerField(default=12000, verbose_name="연간 주행거리")
    accident_history = models.IntegerField(default=0, verbose_name="사고 이력")
    car_info = models.JSONField(default=dict, verbose_name="차량 정보")
    selected_insurance = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="선택한 보험상품"
    )
    satisfaction_score = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        blank=True,
        null=True,
        verbose_name="만족도 점수",
    )
    selection_date = models.DateTimeField(
        blank=True, null=True, verbose_name="보험 선택일"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")

    class Meta:
        verbose_name = "사용자 프로필"
        verbose_name_plural = "사용자 프로필"

    def __str__(self):
        return f"{self.user.username}의 프로필"

    def get_car_info_display(self):
        """차량 정보를 읽기 쉬운 형태로 반환"""
        if isinstance(self.car_info, str):
            return json.loads(self.car_info)
        return self.car_info


class MLRecommendation(models.Model):
    """ML 추천 이력 모델"""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="recommendations",
        verbose_name="사용자",
    )
    recommended_products = models.JSONField(
        default=list, verbose_name="추천 상품 리스트"
    )
    ml_scores = models.JSONField(default=dict, verbose_name="ML 추천 점수")
    similar_users = models.JSONField(default=list, verbose_name="유사 사용자 리스트")
    recommendation_date = models.DateTimeField(
        auto_now_add=True, verbose_name="추천 생성일"
    )
    user_feedback = models.CharField(
        max_length=20, blank=True, null=True, verbose_name="사용자 피드백"
    )
    is_viewed = models.BooleanField(default=False, verbose_name="조회 여부")
    is_selected = models.BooleanField(default=False, verbose_name="선택 여부")

    class Meta:
        verbose_name = "ML 추천 이력"
        verbose_name_plural = "ML 추천 이력"
        ordering = ["-recommendation_date"]

    def __str__(self):
        return f"{self.user.username}의 추천 ({self.recommendation_date.strftime('%Y-%m-%d %H:%M')})"

    def get_recommended_products_count(self):
        """추천 상품 개수 반환"""
        if isinstance(self.recommended_products, list):
            return len(self.recommended_products)
        return 0

    def get_similar_users_count(self):
        """유사 사용자 개수 반환"""
        if isinstance(self.similar_users, list):
            return len(self.similar_users)
        return 0
