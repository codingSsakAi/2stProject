from django.db import models
from django.contrib.auth.models import User
import os


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
    created_at = models.DateTimeField("생성일시", auto_now_add=True)

    class Meta:
        verbose_name = "문서 청크"
        verbose_name_plural = "문서 청크 목록"
        ordering = ["document", "chunk_index"]
        unique_together = ["document", "chunk_index"]

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
        related_name="chat_history"
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
