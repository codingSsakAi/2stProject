from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    GENDER_CHOICES = [
        ('M', '남성'),
        ('F', '여성'),
        ('O', '기타'),
    ]
    
    birth_date = models.DateField(null=True, blank=True, verbose_name='생년월일')
    gender = models.CharField(
        max_length=1, 
        choices=GENDER_CHOICES, 
        null=True, 
        blank=True, 
        verbose_name='성별'
    )
    has_license = models.BooleanField(
        default=False, 
        verbose_name='운전면허 보유 여부'
    )

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

