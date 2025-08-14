from django import forms
from .models import InsuranceDocument, InsuranceCompany


class DocumentUploadForm(forms.ModelForm):
    """문서 업로드 폼"""

    class Meta:
        model = InsuranceDocument
        fields = ["title", "insurance_company", "pdf_file"]
        widgets = {
            "title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "문서 제목을 입력하세요"}
            ),
            "insurance_company": forms.Select(attrs={"class": "form-select"}),
            "pdf_file": forms.FileInput(
                attrs={"class": "form-control", "accept": ".pdf"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 활성화된 보험사만 표시
        self.fields["insurance_company"].queryset = InsuranceCompany.objects.filter(
            is_active=True
        )
        self.fields["insurance_company"].empty_label = "보험사를 선택하세요"
