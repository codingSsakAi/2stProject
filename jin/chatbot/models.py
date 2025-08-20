from django.db import models
from django.contrib.auth.models import User
import os
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class InsuranceCompany(models.Model):
    """보험사 정보 모델"""

    name = models.CharField("보험사명", max_length=100, unique=True)
    code = models.CharField("기관코드", max_length=10, unique=True)
    is_active = models.BooleanField("활성화", default=True)
    created_at = models.DateTimeField("생성일시", auto_now_add=True)
    updated_at = models.DateTimeField("수정일시", auto_now=True)

    class Meta:
        verbose_name = "보험사"
        verbose_name_plural = "보험사 목록"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"


class InsuranceDocument(models.Model):
    """보험 약관 문서 모델"""

    title = models.CharField("제목", max_length=200)
    insurance_company = models.ForeignKey(
        InsuranceCompany,
        on_delete=models.CASCADE,
        verbose_name="보험사",
        related_name="documents",
    )

    def get_pdf_upload_path(instance, filename):
        """PDF 파일 업로드 경로 생성"""
        import os
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        company_name = instance.insurance_company.name
        name, ext = os.path.splitext(filename)
        return f"documents/pdf/{company_name}/{name}_{timestamp}{ext}"

    def get_txt_upload_path(instance, filename):
        """텍스트 파일 업로드 경로 생성"""
        import os
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        company_name = instance.insurance_company.name
        name, ext = os.path.splitext(filename)
        return f"documents/txt/{company_name}/{name}_{timestamp}{ext}"

    pdf_file = models.FileField(
        "PDF 파일", upload_to=get_pdf_upload_path, blank=True, null=True
    )
    txt_file = models.FileField(
        "텍스트 파일", upload_to=get_txt_upload_path, blank=True, null=True
    )
    uploaded_by = models.ForeignKey(
        User, on_delete=models.CASCADE, verbose_name="업로드자"
    )
    uploaded_at = models.DateTimeField("업로드일시", auto_now_add=True)
    processed_at = models.DateTimeField("처리일시", blank=True, null=True)
    status = models.CharField(
        "상태",
        max_length=20,
        choices=[("uploaded", "업로드됨"), ("completed", "완료"), ("error", "오류")],
        default="uploaded",
    )
    error_message = models.TextField("오류 메시지", blank=True)

    # 핵심 문서 메타데이터
    document_version = models.CharField(
        "문서버전", max_length=50, blank=True, null=True
    )
    effective_date = models.DateField("시행일자", blank=True, null=True)
    insurance_type = models.CharField("보험종류", max_length=100, blank=True, null=True)

    class Meta:
        verbose_name = "보험 약관 문서"
        verbose_name_plural = "보험 약관 문서 목록"
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.insurance_company.name} - {self.title}"

    def get_pdf_filename(self):
        """PDF 파일명 반환"""
        if self.pdf_file:
            return os.path.basename(self.pdf_file.name)
        return None

    def get_txt_filename(self):
        """텍스트 파일명 반환"""
        if self.txt_file:
            return os.path.basename(self.txt_file.name)
        return None


class DocumentChunk(models.Model):
    """문서 청크 모델"""

    document = models.ForeignKey(
        InsuranceDocument,
        on_delete=models.CASCADE,
        verbose_name="문서",
        related_name="chunks",
    )
    chunk_text = models.TextField("청크 텍스트")
    chunk_index = models.PositiveIntegerField("청크 인덱스")

    # 핵심 메타데이터 필드들
    title = models.CharField("제목", max_length=500, blank=True, null=True)
    category = models.CharField("카테고리", max_length=100, blank=True, null=True)
    article_number = models.PositiveIntegerField("조문번호", blank=True, null=True)
    keywords = models.JSONField("키워드", default=list, blank=True)
    summary = models.TextField("요약", blank=True, null=True)

    # 품질 관리 메타데이터
    extraction_method = models.CharField(
        "추출방법", max_length=50, default="rule_based"
    )
    confidence_score = models.FloatField("신뢰도", default=0.0)
    review_status = models.CharField("검토상태", max_length=20, default="pending")

    created_at = models.DateTimeField("생성일시", auto_now_add=True)
    updated_at = models.DateTimeField("수정일시", auto_now=True)

    class Meta:
        verbose_name = "문서 청크"
        verbose_name_plural = "문서 청크 목록"
        ordering = ["document", "chunk_index"]

    def __str__(self):
        return f"{self.document.title} - 청크 {self.chunk_index}"


class ChatSession(models.Model):
    """채팅 세션 모델"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="사용자")
    title = models.CharField("세션 제목", max_length=200, default="새로운 채팅")
    created_at = models.DateTimeField("생성일시", auto_now_add=True)
    updated_at = models.DateTimeField("수정일시", auto_now=True)
    is_active = models.BooleanField("활성", default=True)

    class Meta:
        verbose_name = "채팅 세션"
        verbose_name_plural = "채팅 세션 목록"
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.user.username} - {self.title}"


class ChatHistory(models.Model):
    """채팅 기록 모델"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="사용자")
    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        verbose_name="채팅 세션",
        related_name="chat_history",
    )
    message = models.TextField("메시지 내용")
    is_user = models.BooleanField("사용자 메시지 여부", default=True)
    metadata = models.JSONField("메타데이터", default=dict, blank=True)
    created_at = models.DateTimeField("생성일시", auto_now_add=True)

    class Meta:
        verbose_name = "채팅 기록"
        verbose_name_plural = "채팅 기록 목록"
        ordering = ["created_at"]

    def __str__(self):
        message_type = "사용자" if self.is_user else "챗봇"
        return f"{self.session.title} - {message_type}: {self.message[:50]}..."


class InsuranceMockData(models.Model):
    """보험 Mock 데이터 모델"""

    insurance_company = models.ForeignKey(
        InsuranceCompany,
        on_delete=models.CASCADE,
        verbose_name="보험사",
        related_name="mock_data",
    )
    insurance_name = models.CharField("보험명", max_length=200)
    base_premium = models.PositiveIntegerField("기본 보험료")

    # 연령별 할증율 (20대 기준)
    age_20s_rate = models.FloatField("20대 할증율", default=1.0)
    age_30s_rate = models.FloatField("30대 할증율", default=1.1)
    age_40s_rate = models.FloatField("40대 할증율", default=1.2)
    age_50s_rate = models.FloatField("50대 할증율", default=1.3)
    age_60s_rate = models.FloatField("60대 할증율", default=1.5)

    # 성별 할증율
    male_rate = models.FloatField("남성 할증율", default=1.0)
    female_rate = models.FloatField("여성 할증율", default=0.9)

    # 차량 크기별 할증율
    small_car_rate = models.FloatField("소형차 할증율", default=0.8)
    medium_car_rate = models.FloatField("중형차 할증율", default=1.0)
    large_car_rate = models.FloatField("대형차 할증율", default=1.3)
    suv_rate = models.FloatField("SUV 할증율", default=1.2)

    # 주행거리별 할증율
    low_mileage_rate = models.FloatField("저주행 할증율", default=0.9)
    high_mileage_rate = models.FloatField("고주행 할증율", default=1.2)

    # 사고경력별 할증율
    no_accident_rate = models.FloatField("무사고 할증율", default=0.8)
    accident_rate = models.FloatField("사고 할증율", default=1.5)

    created_at = models.DateTimeField("생성일시", auto_now_add=True)
    updated_at = models.DateTimeField("수정일시", auto_now=True)

    class Meta:
        verbose_name = "보험 Mock 데이터"
        verbose_name_plural = "보험 Mock 데이터 목록"
        ordering = ["insurance_company", "insurance_name"]

    def __str__(self):
        return f"{self.insurance_company.name} - {self.insurance_name}"

    def calculate_premium(self, user_profile):
        """사용자 프로필 기반 보험료 계산"""
        premium = self.base_premium

        # 연령별 할증
        age = user_profile.get_age()
        if age < 30:
            premium *= self.age_20s_rate
        elif age < 40:
            premium *= self.age_30s_rate
        elif age < 50:
            premium *= self.age_40s_rate
        elif age < 60:
            premium *= self.age_50s_rate
        else:
            premium *= self.age_60s_rate

        # 성별 할증
        if user_profile.gender == "M":
            premium *= self.male_rate
        else:
            premium *= self.female_rate

        # 차량 크기별 할증
        if user_profile.car_size == "small":
            premium *= self.small_car_rate
        elif user_profile.car_size == "medium":
            premium *= self.medium_car_rate
        elif user_profile.car_size == "large":
            premium *= self.large_car_rate
        elif user_profile.car_size == "suv":
            premium *= self.suv_rate

        # 주행거리별 할증
        if user_profile.annual_mileage:
            if user_profile.annual_mileage < 10000:
                premium *= self.low_mileage_rate
            elif user_profile.annual_mileage > 20000:
                premium *= self.high_mileage_rate

        # 사고경력별 할증
        if user_profile.accident_history == 0:
            premium *= self.no_accident_rate
        else:
            premium *= self.accident_rate

        return int(premium)


class PineconeUsage(models.Model):
    """Pinecone 사용량 추적 모델"""

    date = models.DateField(auto_now_add=True)
    read_units = models.IntegerField(default=0, help_text="읽기 단위 사용량")
    write_units = models.IntegerField(default=0, help_text="쓰기 단위 사용량")
    storage_gb = models.FloatField(default=0.0, help_text="저장소 사용량 (GB)")
    total_queries = models.IntegerField(default=0, help_text="총 쿼리 수")

    class Meta:
        db_table = "pinecone_usage"
        verbose_name = "Pinecone 사용량"
        verbose_name_plural = "Pinecone 사용량"

    def __str__(self):
        return f"{self.date} - RUs: {self.read_units}, WUs: {self.write_units}, Storage: {self.storage_gb:.2f}GB"

    @classmethod
    def get_today_usage(cls):
        """오늘 사용량 조회"""
        today = timezone.now().date()
        usage, created = cls.objects.get_or_create(
            date=today,
            defaults={
                "read_units": 0,
                "write_units": 0,
                "storage_gb": 0.0,
                "total_queries": 0,
            },
        )
        return usage

    @classmethod
    def add_read_units(cls, read_units: int):
        """읽기 단위 추가"""
        usage = cls.get_today_usage()
        usage.read_units += read_units
        usage.total_queries += 1
        usage.save()
        logger.info(
            f"Pinecone 사용량 업데이트: RUs +{read_units}, 총 RUs: {usage.read_units}"
        )

    @classmethod
    def add_write_units(cls, write_units: int):
        """쓰기 단위 추가"""
        usage = cls.get_today_usage()
        usage.write_units += write_units
        usage.save()
        logger.info(
            f"Pinecone 사용량 업데이트: WUs +{write_units}, 총 WUs: {usage.write_units}"
        )

    @classmethod
    def update_storage(cls, storage_gb: float):
        """저장소 사용량 업데이트"""
        usage = cls.get_today_usage()
        usage.storage_gb = storage_gb
        usage.save()
        logger.info(f"Pinecone 저장소 사용량 업데이트: {storage_gb:.2f}GB")


class ProcessingProgress(models.Model):
    """문서 처리 진행상황 추적 모델"""

    document = models.ForeignKey(
        InsuranceDocument,
        on_delete=models.CASCADE,
        verbose_name="문서",
        related_name="processing_progress",
    )

    # 처리 단계
    STAGE_CHOICES = [
        ("uploading", "업로드 중"),
        ("pdf_processing", "PDF 처리 중"),
        ("text_extraction", "텍스트 추출 중"),
        ("chunk_creation", "청크 생성 중"),
        ("metadata_generation", "메타데이터 생성 중"),
        ("embedding_processing", "Embedding 처리 중"),
        ("pinecone_upload", "Pinecone 업로드 중"),
        ("completed", "완료"),
        ("error", "오류"),
    ]

    current_stage = models.CharField(
        "현재 단계", max_length=30, choices=STAGE_CHOICES, default="uploading"
    )

    # 진행률 정보
    total_chunks = models.PositiveIntegerField("전체 청크 수", default=0)
    processed_chunks = models.PositiveIntegerField("처리된 청크 수", default=0)
    progress_percentage = models.FloatField("진행률 (%)", default=0.0)

    # 로그 메시지
    log_messages = models.JSONField("로그 메시지", default=list)

    # 시간 정보
    started_at = models.DateTimeField("시작 시간", auto_now_add=True)
    updated_at = models.DateTimeField("수정 시간", auto_now=True)
    completed_at = models.DateTimeField("완료 시간", null=True, blank=True)

    # 오류 정보
    error_message = models.TextField("오류 메시지", blank=True)

    class Meta:
        verbose_name = "처리 진행상황"
        verbose_name_plural = "처리 진행상황 목록"
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.document.title} - {self.current_stage}"

    def add_log_message(self, message: str):
        """로그 메시지 추가"""
        if not self.log_messages:
            self.log_messages = []

        timestamp = timezone.now().strftime("%H:%M:%S")
        self.log_messages.append({"timestamp": timestamp, "message": message})

        # 최대 100개 메시지만 유지
        if len(self.log_messages) > 100:
            self.log_messages = self.log_messages[-100:]

        self.save()

    def update_progress(self, stage: str, processed: int = None, total: int = None):
        """진행상황 업데이트"""
        self.current_stage = stage

        if processed is not None:
            self.processed_chunks = processed

        if total is not None:
            self.total_chunks = total

        if self.total_chunks > 0:
            self.progress_percentage = (self.processed_chunks / self.total_chunks) * 100

        self.save()

    def complete(self, success: bool = True, error_message: str = ""):
        """처리 완료"""
        if success:
            self.current_stage = "completed"
            self.progress_percentage = 100.0
            self.processed_chunks = self.total_chunks
        else:
            self.current_stage = "error"
            self.error_message = error_message

        self.completed_at = timezone.now()
        self.save()
