# accident_project/forms.py
from django import forms
from .models import Agreement
import json

# 폼에 노출하고 싶은 우선순위 필드(모델에 없으면 자동 제외)
PREFERRED_FIELDS = [
    "title", "accident_date", "accident_type", "summary",
    "location", "status", "damages_raw",
]

# 모델에 실제로 존재하는 필드만 사용
MODEL_FIELDS = [f.name for f in Agreement._meta.get_fields() if getattr(f, "attname", None)]
FIELDS = [f for f in PREFERRED_FIELDS if f in MODEL_FIELDS]

if not FIELDS:
    # 최소 한 개는 있어야 폼이 의미가 있으므로, models에 맞춰 조정하세요.
    # 기본적으로 damages_raw가 있으면 그것만이라도 편집 가능하도록 포함
    if "damages_raw" in MODEL_FIELDS:
        FIELDS = ["damages_raw"]

class AgreementForm(forms.ModelForm):
    # 날짜 위젯 자동 적용
    if "accident_date" in FIELDS:
        accident_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))

    class Meta:
        model = Agreement
        fields = FIELDS
        widgets = {
            **({"summary": forms.Textarea(attrs={"rows": 3})} if "summary" in FIELDS else {}),
            **({"damages_raw": forms.Textarea(attrs={"rows": 8, "spellcheck": "false"})} if "damages_raw" in FIELDS else {}),
        }
        labels = {
            "title": "제목",
            "accident_date": "사고일자",
            "accident_type": "사고유형",
            "summary": "사고 요약",
            "location": "장소",
            "status": "상태",
            "damages_raw": "원본 데이터(JSON)",
        }

    def clean_damages_raw(self):
        # 모델에 damages_raw가 없으면 패스
        if "damages_raw" not in self.fields:
            return self.cleaned_data.get("damages_raw")

        val = self.cleaned_data.get("damages_raw")
        if val in (None, ""):
            return "{}"
        if isinstance(val, dict):
            return json.dumps(val, ensure_ascii=False)

        if isinstance(val, str):
            try:
                json.loads(val)
            except json.JSONDecodeError:
                raise forms.ValidationError("damages_raw는 유효한 JSON 문자열이어야 합니다.")
            return val
        # 그 외 타입은 문자열로 직렬화
        try:
            return json.dumps(val, ensure_ascii=False)
        except Exception:
            raise forms.ValidationError("damages_raw 직렬화에 실패했습니다.")
