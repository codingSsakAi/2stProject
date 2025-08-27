from django.db import models
from django.contrib.postgres.fields import ArrayField  # SQLite면 TextField로 JSON직렬화하세요
from django.conf import settings

# Create your models here.

# class Agreement(models.Model):
#     incident_dt = models.CharField(max_length=32, blank=True)
#     location    = models.CharField(max_length=255, blank=True)
#     a_name      = models.CharField(max_length=64, blank=True)
#     b_name      = models.CharField(max_length=64, blank=True)
#     damages_raw = models.TextField(blank=True)  # JSON 문자열 저장(간단 방식)
#     created_at  = models.DateTimeField(auto_now_add=True)

class Agreement(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="agreements",
        null=True, blank=True,   # 기존 데이터 때문에 처음엔 허용
    )
    a_name = models.CharField(max_length=100)
    b_name = models.CharField(max_length=100)
    location = models.CharField(max_length=200, blank=True)
    incident_dt = models.DateTimeField(null=True, blank=True)
    damages_raw = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class AccidentRecord(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="accident_records")
    accident_date = models.DateTimeField()
    location = models.CharField(max_length=200, blank=True)
    a_plate = models.CharField(max_length=50, blank=True)
    b_plate = models.CharField(max_length=50, blank=True)
    payload = models.JSONField(default=dict, blank=True)  # 폼 스냅샷(마스킹된 값 사용)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-accident_date", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "accident_date", "a_plate", "b_plate"],
                name="uniq_owner_accidentdate_plates"
            )
        ]

    def __str__(self):
        return f"{self.pk} | {self.owner} | {self.accident_date:%Y-%m-%d %H:%M}"