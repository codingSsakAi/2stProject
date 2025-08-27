# insurance_app/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.apps import apps


class CustomUser(AbstractUser):
    GENDER_CHOICES = [
        ('M', '남성'),
        ('F', '여성'),
        ('O', '기타'),
    ]
    birth_date = models.DateField(null=True, blank=True, verbose_name='생년월일')
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, null=True, blank=True, verbose_name='성별')
    has_license = models.BooleanField(default=False, verbose_name='운전면허 보유 여부')

    def __str__(self):
        return self.username

    # ─────────────────────────────────────────
    # 통합 헬퍼: 사고 협의서(Agreement) 연동
    # - accident_project.Agreement.owner(FK → AUTH_USER_MODEL) 기준으로 본인 레코드만 반환
    # - owner 필드가 없거나 앱이 로드되지 않은 경우 안전하게 빈 쿼리셋 반환
    # ─────────────────────────────────────────
    @property
    def agreements_qs(self):
        """
        사용자의 협의서 QuerySet을 반환.
        accident_project가 없거나 owner 필드가 없으면 빈 QuerySet.
        """
        try:
            Agreement = apps.get_model('accident_project', 'Agreement')
        except Exception:
            return models.QuerySet(model=None)  # 안전한 빈 형태

        if Agreement is None:
            return Agreement.objects.none()

        # owner 필드가 있을 때만 필터
        if hasattr(Agreement, 'owner'):
            return Agreement.objects.filter(owner_id=self.id)

        # 혹시 과거 user FK가 있었다면 백업 시도(없으면 빈 쿼리셋)
        if hasattr(Agreement, 'user'):
            return Agreement.objects.filter(user_id=self.id)

        return Agreement.objects.none()

    def agreements_count(self) -> int:
        try:
            return self.agreements_qs.count()
        except Exception:
            return 0


class Clause(models.Model):
    insurer = models.CharField(max_length=50)
    title = models.CharField(max_length=100)
    clause_number = models.CharField(max_length=20)
    page = models.IntegerField()
    text = models.TextField()
    pdf_link = models.URLField()

    def __str__(self):
        return f"[{self.insurer}] {self.title} #{self.clause_number} p.{self.page}"


class InsuranceQuote(models.Model):
    # 기존: user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    # 개선: AUTH_USER_MODEL로 참조(유연성↑, 기존 데이터 유지)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    insurer_name = models.CharField(max_length=50)
    premium = models.IntegerField()
    coverage_summary = models.TextField()
    special_terms = models.TextField()
    score = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    conditions = models.JSONField(default=dict)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} · {self.insurer_name} · {self.premium}원 · score={self.score}"


# ─────────────────────────────────────────────
# 약관 용어 사전
# ─────────────────────────────────────────────
class GlossaryTerm(models.Model):
    slug = models.SlugField(max_length=120, unique=True)  # URL용 키
    term = models.CharField(max_length=120)               # 표제어
    short_def = models.CharField(max_length=300)          # 짧은 정의
    long_def = models.TextField(blank=True)               # 긴 정의
    category = models.CharField(max_length=60, db_index=True)  # 분류(보장/면책/금액/절차 등)
    aliases = models.JSONField(default=list, blank=True)  # 동의어/약어
    related = models.JSONField(default=list, blank=True)  # 연관 용어(슬러그 목록)
    meta = models.JSONField(default=dict, blank=True)     # 기타 메타(관련 담보 등)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["term"]), models.Index(fields=["category"])]
        ordering = ["term"]

    def __str__(self):
        return self.term
