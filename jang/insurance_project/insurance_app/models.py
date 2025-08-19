# insurance_app/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser

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


class Clause(models.Model):
    insurer = models.CharField(max_length=50)
    title = models.CharField(max_length=100)
    clause_number = models.CharField(max_length=20)
    page = models.IntegerField()
    text = models.TextField()
    pdf_link = models.URLField()


class InsuranceQuote(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    insurer_name = models.CharField(max_length=50)
    premium = models.IntegerField()
    coverage_summary = models.TextField()
    special_terms = models.TextField()
    score = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    conditions = models.JSONField(default=dict)


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
