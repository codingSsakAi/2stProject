from django.db import models
from django.contrib.postgres.fields import ArrayField  # SQLite면 TextField로 JSON직렬화하세요

class Agreement(models.Model):
    incident_dt = models.CharField(max_length=32, blank=True)
    location    = models.CharField(max_length=255, blank=True)
    a_name      = models.CharField(max_length=64, blank=True)
    b_name      = models.CharField(max_length=64, blank=True)
    damages_raw = models.TextField(blank=True)  # JSON 문자열 저장(간단 방식)
    created_at  = models.DateTimeField(auto_now_add=True)
