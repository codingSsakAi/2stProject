from django.db import models
from django.core.validators import FileExtensionValidator
from django.contrib.auth.models import User
import os


class InsuranceCompany(models.Model):
    """보험사 모델"""

    STATUS_CHOICES = [
        ("active", "활성"),
        ("inactive", "비활성"),
        ("pending", "대기"),
    ]

    name = models.CharField(max_length=100, unique=True, verbose_name="보험사명")
    code = models.CharField(max_length=20, unique=True, verbose_name="보험사 코드")
    description = models.TextField(blank=True, verbose_name="설명")
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="active", verbose_name="상태"
    )
    phone = models.CharField(max_length=20, blank=True, verbose_name="전화번호")
    email = models.EmailField(blank=True, verbose_name="이메일")
    website = models.URLField(blank=True, verbose_name="웹사이트")
    address = models.TextField(blank=True, verbose_name="주소")
    city = models.CharField(max_length=50, blank=True, verbose_name="도시")
    state = models.CharField(max_length=50, blank=True, verbose_name="주/도")
    zip_code = models.CharField(max_length=20, blank=True, verbose_name="우편번호")
    is_active = models.BooleanField(default=True, verbose_name="활성화 여부")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")

    class Meta:
        verbose_name = "보험사"
        verbose_name_plural = "보험사"
        ordering = ["name"]

    def __str__(self):
        return self.name


class PolicyDocument(models.Model):
    """보험 약관 문서 모델"""

    DOCUMENT_TYPE_CHOICES = [
        ("PDF", "PDF"),
        ("DOCX", "DOCX"),
    ]

    STATUS_CHOICES = [
        ("pending", "대기"),
        ("approved", "승인"),
        ("rejected", "거부"),
    ]

    title = models.CharField(max_length=200, blank=True, null=True, verbose_name="제목")
    description = models.TextField(blank=True, verbose_name="설명")
    company = models.ForeignKey(
        InsuranceCompany,
        on_delete=models.CASCADE,
        related_name="documents",
        verbose_name="보험사",
    )
    document_type = models.CharField(
        max_length=10,
        choices=DOCUMENT_TYPE_CHOICES,
        default="PDF",
        verbose_name="문서 유형",
    )
    file = models.FileField(
        upload_to="documents/",
        validators=[FileExtensionValidator(allowed_extensions=["pdf", "docx"])],
        blank=True,
        null=True,
        verbose_name="파일",
    )
    file_path = models.CharField(max_length=500, blank=True, verbose_name="파일 경로")
    file_size = models.BigIntegerField(
        blank=True, null=True, verbose_name="파일 크기 (bytes)"
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending", verbose_name="상태"
    )
    tags = models.JSONField(default=list, verbose_name="태그")
    keywords = models.JSONField(default=list, verbose_name="키워드")
    upload_date = models.DateTimeField(auto_now_add=True, verbose_name="업로드 날짜")
    version = models.CharField(max_length=20, default="1.0", verbose_name="버전 정보")
    is_active = models.BooleanField(default=True, verbose_name="활성화 여부")
    pinecone_index_id = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Pinecone 인덱스 ID"
    )
    page_count = models.IntegerField(blank=True, null=True, verbose_name="페이지 수")

    class Meta:
        verbose_name = "보험 약관 문서"
        verbose_name_plural = "보험 약관 문서"
        ordering = ["-upload_date"]
        unique_together = ["company", "version"]

    def __str__(self):
        return f"{self.company.name} - {self.title} (v{self.version})"

    def get_file_name(self):
        """파일명 반환"""
        return os.path.basename(self.file_path) if self.file_path else self.file.name

    def get_file_size_mb(self):
        """파일 크기를 MB 단위로 반환"""
        if self.file_size:
            return round(self.file_size / (1024 * 1024), 2)
        return 0


# UserProfile은 users 앱에서 관리하므로 제거


class ChatHistory(models.Model):
    """채팅 기록 모델"""

    MESSAGE_TYPE_CHOICES = [
        ("user", "사용자"),
        ("assistant", "어시스턴트"),
        ("system", "시스템"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="chat_history",
        verbose_name="사용자",
    )
    session_id = models.CharField(max_length=100, verbose_name="세션 ID")
    message = models.TextField(verbose_name="사용자 메시지")
    response = models.TextField(verbose_name="시스템 응답")
    message_type = models.CharField(
        max_length=10,
        choices=MESSAGE_TYPE_CHOICES,
        default="user",
        verbose_name="메시지 유형",
    )
    metadata = models.JSONField(default=dict, verbose_name="메타데이터")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")

    class Meta:
        verbose_name = "채팅 기록"
        verbose_name_plural = "채팅 기록"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class RecommendationHistory(models.Model):
    """추천 기록 모델"""

    RECOMMENDATION_TYPE_CHOICES = [
        ("personalized", "개인화"),
        ("collaborative", "협업 필터링"),
        ("content_based", "콘텐츠 기반"),
        ("hybrid", "하이브리드"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="recommendation_history",
        verbose_name="사용자",
    )
    session_id = models.CharField(max_length=100, verbose_name="세션 ID")
    recommendation_type = models.CharField(
        max_length=20, choices=RECOMMENDATION_TYPE_CHOICES, verbose_name="추천 유형"
    )
    recommendation_data = models.JSONField(default=dict, verbose_name="추천 데이터")
    feedback_score = models.FloatField(
        blank=True, null=True, verbose_name="피드백 점수"
    )
    feedback_comment = models.TextField(blank=True, verbose_name="피드백 코멘트")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")

    class Meta:
        verbose_name = "추천 기록"
        verbose_name_plural = "추천 기록"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.recommendation_type} ({self.created_at.strftime('%Y-%m-%d')})"


class InsuranceQuote(models.Model):
    """보험 견적 모델"""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="quotes", verbose_name="사용자"
    )
    company = models.ForeignKey(
        InsuranceCompany,
        on_delete=models.CASCADE,
        related_name="quotes",
        verbose_name="보험사",
    )
    annual_premium = models.IntegerField(verbose_name="연간 보험료")
    monthly_premium = models.IntegerField(verbose_name="월 보험료")
    coverage_level = models.CharField(
        max_length=20, default="표준", verbose_name="보장 수준"
    )
    coverage_details = models.JSONField(default=dict, verbose_name="보장 상세 내용")
    special_discount = models.CharField(
        max_length=200, blank=True, null=True, verbose_name="특별 할인"
    )
    discount_rate = models.CharField(
        max_length=20, blank=True, null=True, verbose_name="할인율"
    )
    penalty_rate = models.CharField(
        max_length=20, blank=True, null=True, verbose_name="할증율"
    )
    deductible = models.JSONField(default=dict, verbose_name="자기부담금")
    payment_options = models.JSONField(default=list, verbose_name="납입 옵션")
    additional_benefits = models.JSONField(default=list, verbose_name="추가 혜택")
    customer_satisfaction = models.FloatField(
        blank=True, null=True, verbose_name="고객만족도"
    )
    claim_service_rating = models.FloatField(
        blank=True, null=True, verbose_name="클레임 서비스 평점"
    )
    calculation_date = models.DateTimeField(auto_now_add=True, verbose_name="계산일")

    class Meta:
        verbose_name = "보험 견적"
        verbose_name_plural = "보험 견적"
        ordering = ["-calculation_date"]

    def __str__(self):
        return f"{self.user.username} - {self.company.name} ({self.calculation_date.strftime('%Y-%m-%d')})"


class ChatSession(models.Model):
    """채팅 세션 모델"""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="chat_sessions",
        verbose_name="사용자",
    )
    session_id = models.CharField(max_length=100, unique=True, verbose_name="세션 ID")
    is_active = models.BooleanField(default=True, verbose_name="활성화 여부")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")

    class Meta:
        verbose_name = "채팅 세션"
        verbose_name_plural = "채팅 세션"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.session_id}"


class ChatMessage(models.Model):
    """채팅 메시지 모델"""

    MESSAGE_TYPE_CHOICES = [
        ("USER", "사용자"),
        ("ASSISTANT", "어시스턴트"),
        ("SYSTEM", "시스템"),
    ]

    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name="세션",
    )
    message_type = models.CharField(
        max_length=10, choices=MESSAGE_TYPE_CHOICES, verbose_name="메시지 유형"
    )
    content = models.TextField(verbose_name="메시지 내용")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="타임스탬프")
    metadata = models.JSONField(default=dict, verbose_name="메타데이터")

    class Meta:
        verbose_name = "채팅 메시지"
        verbose_name_plural = "채팅 메시지"
        ordering = ["timestamp"]

    def __str__(self):
        return f"{self.session.user.username} - {self.message_type} ({self.timestamp.strftime('%H:%M')})"
