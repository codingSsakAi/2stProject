from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator


class UserProfile(models.Model):
    """사용자 프로필 모델 - 보험 추천에 필요한 추가 정보 저장"""

    # 사용자 기본 정보
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    birth_date = models.DateField("생년월일", null=True, blank=True)

    # 성별 선택
    GENDER_CHOICES = [
        ("M", "남성"),
        ("F", "여성"),
    ]
    gender = models.CharField("성별", max_length=1, choices=GENDER_CHOICES)

    # 거주 지역
    RESIDENCE_CHOICES = [
        ("서울", "서울"),
        ("부산", "부산"),
        ("대구", "대구"),
        ("인천", "인천"),
        ("광주", "광주"),
        ("대전", "대전"),
        ("울산", "울산"),
        ("세종", "세종"),
        ("기타", "기타"),
    ]
    residence_area = models.CharField(
        "거주 지역", max_length=10, choices=RESIDENCE_CHOICES, blank=True
    )

    # 운전 경력 (년)
    driving_experience = models.PositiveIntegerField(
        "운전 경력(년)", default=0, validators=[MaxValueValidator(50)]
    )

    # 자동차 관련 정보
    CAR_TYPE_CHOICES = [
        ("경차", "경차"),
        ("소형", "소형"),
        ("준중형", "준중형"),
        ("중형", "중형"),
        ("대형", "대형"),
        ("SUV", "SUV"),
    ]
    car_type = models.CharField(
        "차종", max_length=10, choices=CAR_TYPE_CHOICES, blank=True
    )

    # 주행거리 (연간)
    annual_mileage = models.PositiveIntegerField(
        "연간 주행거리(km)",
        validators=[MinValueValidator(1000), MaxValueValidator(100000)],
        blank=True,
        null=True,
    )

    # 사고 경력
    accident_history = models.PositiveIntegerField(
        "사고 경력 횟수", default=0, validators=[MaxValueValidator(10)]
    )

    # 보장 수준
    COVERAGE_LEVEL_CHOICES = [
        ("기본", "기본"),
        ("표준", "표준"),
        ("고급", "고급"),
        ("프리미엄", "프리미엄"),
    ]
    coverage_level = models.CharField(
        "보장 수준", max_length=10, choices=COVERAGE_LEVEL_CHOICES, default="표준"
    )

    # 추가 특약 관심 여부
    additional_coverage_interest = models.BooleanField("추가 특약 관심", default=False)

    # 생성/수정 시간
    created_at = models.DateTimeField("생성일시", auto_now_add=True)
    updated_at = models.DateTimeField("수정일시", auto_now=True)

    class Meta:
        verbose_name = "사용자 프로필"
        verbose_name_plural = "사용자 프로필"

    def __str__(self):
        return f"{self.user.username}의 프로필"

    def get_age(self):
        """현재 나이 계산"""
        from datetime import date

        if not self.birth_date:
            return None
            
        today = date.today()
        return (
            today.year
            - self.birth_date.year
            - ((today.month, today.day) < (self.birth_date.month, self.birth_date.day))
        )

    def get_age_group(self):
        """연령대 그룹 반환"""
        age = self.get_age()
        if age is None:
            return "정보 없음"
        elif age < 20:
            return "10대"
        elif age < 30:
            return "20대"
        elif age < 40:
            return "30대"
        elif age < 50:
            return "40대"
        elif age < 60:
            return "50대"
        else:
            return "60대 이상"


class InsuranceRecommendation(models.Model):
    """보험 추천 내역 모델"""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="recommendations"
    )

    # 채팅 세션 연결
    chat_session = models.ForeignKey(
        'chatbot.ChatSession',
        on_delete=models.CASCADE,
        verbose_name="채팅 세션",
        related_name="recommendations",
        null=True,
        blank=True
    )

    # 추천 세션 ID (기존 호환성 유지)
    session_id = models.CharField("세션 ID", max_length=100, unique=True, default="")

    # 추천 모드
    RECOMMENDATION_MODE_CHOICES = [
        ("quick", "빠른 추천"),
        ("standard", "표준 추천"),
        ("detailed", "상세 추천"),
        ("chatbot", "챗봇 추천"),
    ]
    recommendation_mode = models.CharField(
        "추천 모드", max_length=10, choices=RECOMMENDATION_MODE_CHOICES
    )

    # 사용자 프로필 스냅샷 (추천 시점의 정보)
    user_profile_snapshot = models.JSONField("사용자 프로필 스냅샷", default=dict)

    # 추천된 보험 정보 (JSON 형태로 여러 보험사 정보 저장)
    recommendations_data = models.JSONField("추천 데이터", default=list)

    # 추천 이유
    recommendation_reason = models.TextField("추천 이유", blank=True)

    # 사용자 선택 여부
    is_selected = models.BooleanField("선택 여부", default=False)
    selected_company = models.CharField("선택한 보험사", max_length=100, blank=True)

    # 추천 품질 평가
    user_rating = models.PositiveIntegerField(
        "사용자 평가",
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    user_feedback = models.TextField("사용자 피드백", blank=True)

    # 생성 시간
    created_at = models.DateTimeField("생성일시", auto_now_add=True)

    class Meta:
        verbose_name = "보험 추천 내역"
        verbose_name_plural = "보험 추천 내역"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.recommendation_mode} 추천"


class ChatHistory(models.Model):
    """채팅 내역 모델"""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="chat_history"
    )

    # 메시지 타입
    MESSAGE_TYPE_CHOICES = [
        ("user", "사용자"),
        ("bot", "봇"),
    ]
    message_type = models.CharField(
        "메시지 타입", max_length=10, choices=MESSAGE_TYPE_CHOICES
    )

    # 메시지 내용
    content = models.TextField("메시지 내용")

    # 채팅 세션 ID
    session_id = models.CharField("세션 ID", max_length=100)

    # 생성 시간
    created_at = models.DateTimeField("생성일시", auto_now_add=True)

    class Meta:
        verbose_name = "채팅 내역"
        verbose_name_plural = "채팅 내역"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.message_type} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class RecommendationStatistics(models.Model):
    """보험 추천 통계 모델 - 배치 처리로 일일 업데이트"""

    # 통계 날짜
    date = models.DateField("통계 날짜", unique=True)
    
    # 연령대별 통계
    age_group_stats = models.JSONField("연령대별 통계", default=dict)
    
    # 성별 통계
    gender_stats = models.JSONField("성별 통계", default=dict)
    
    # 차종별 통계
    car_type_stats = models.JSONField("차종별 통계", default=dict)
    
    # 보험사별 선호도 통계
    company_preference_stats = models.JSONField("보험사별 선호도", default=dict)
    
    # 보장 수준별 통계
    coverage_level_stats = models.JSONField("보장 수준별 통계", default=dict)
    
    # 지역별 통계
    region_stats = models.JSONField("지역별 통계", default=dict)
    
    # 일일 추천 총 수
    total_recommendations = models.PositiveIntegerField("일일 추천 총 수", default=0)
    
    # 일일 선택된 추천 수
    total_selections = models.PositiveIntegerField("일일 선택된 추천 수", default=0)
    
    # 평균 보험료
    average_premium = models.DecimalField("평균 보험료", max_digits=10, decimal_places=2, null=True, blank=True)
    
    # 생성/수정 시간
    created_at = models.DateTimeField("생성일시", auto_now_add=True)
    updated_at = models.DateTimeField("수정일시", auto_now=True)

    class Meta:
        verbose_name = "추천 통계"
        verbose_name_plural = "추천 통계"
        ordering = ["-date"]

    def __str__(self):
        return f"{self.date} 추천 통계"


class UserBehaviorLog(models.Model):
    """사용자 행동 로그 모델 - 상세 분석용"""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="behavior_logs"
    )
    
    # 행동 타입
    BEHAVIOR_TYPE_CHOICES = [
        ("login", "로그인"),
        ("chat_start", "채팅 시작"),
        ("chat_message", "채팅 메시지"),
        ("recommendation_request", "추천 요청"),
        ("recommendation_view", "추천 조회"),
        ("recommendation_select", "추천 선택"),
        ("profile_update", "프로필 수정"),
        ("page_view", "페이지 조회"),
    ]
    behavior_type = models.CharField("행동 타입", max_length=30, choices=BEHAVIOR_TYPE_CHOICES)
    
    # 행동 상세 정보
    behavior_data = models.JSONField("행동 데이터", default=dict)
    
    # 세션 ID
    session_id = models.CharField("세션 ID", max_length=100, blank=True)
    
    # 생성 시간
    created_at = models.DateTimeField("생성일시", auto_now_add=True)

    class Meta:
        verbose_name = "사용자 행동 로그"
        verbose_name_plural = "사용자 행동 로그"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.behavior_type} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
