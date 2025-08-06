from django.db import models

# Create your models here.

from django.db import models

class CarInsuranceKnowledge(models.Model):
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=50, default="자동차보험")
    summary = models.TextField()  # 한줄 요약
    content = models.TextField()  # 상세 설명
    image = models.ImageField(upload_to='car_knowhow/', null=True, blank=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

