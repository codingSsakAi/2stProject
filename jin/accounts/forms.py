from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import UserProfile


class CustomUserCreationForm(UserCreationForm):
    """사용자 회원가입 폼 - 기본 사용자 정보 + 프로필 정보"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 비밀번호 검증 완화
        self.fields["password1"].validators = []
        self.fields["password2"].validators = []

    # 기본 사용자 정보
    first_name = forms.CharField(
        label="이름",
        max_length=30,
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "이름을 입력하세요",
                "autocomplete": "off",
            }
        ),
    )
    last_name = forms.CharField(
        label="성",
        max_length=30,
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "성을 입력하세요",
                "autocomplete": "off",
            }
        ),
    )
    email = forms.EmailField(
        label="이메일",
        required=True,
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "이메일을 입력하세요",
                "autocomplete": "off",
            }
        ),
    )

    # 프로필 정보
    birth_date = forms.DateField(
        label="생년월일",
        required=True,
        widget=forms.DateInput(
            attrs={"class": "form-control", "type": "date", "autocomplete": "off"}
        ),
    )

    GENDER_CHOICES = [
        ("M", "남성"),
        ("F", "여성"),
    ]
    gender = forms.ChoiceField(
        label="성별",
        choices=GENDER_CHOICES,
        required=True,
        widget=forms.Select(attrs={"class": "form-control", "autocomplete": "off"}),
    )

    RESIDENCE_CHOICES = [
        ("", "선택하세요"),
        ("서울", "서울"),
        ("부산", "부산"),
        ("대구", "대구"),
        ("인천", "인천"),
        ("광주", "광주"),
        ("대전", "대전"),
        ("울산", "울산"),
        ("세종", "세종"),
        ("기타", "기타"),
    ]
    residence_area = forms.ChoiceField(
        label="거주 지역",
        choices=RESIDENCE_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "form-control", "autocomplete": "off"}),
    )

    driving_experience = forms.IntegerField(
        label="운전 경력 (년)",
        required=False,
        min_value=0,
        max_value=50,
        widget=forms.NumberInput(
            attrs={"class": "form-control", "autocomplete": "off"}
        ),
    )

    CAR_TYPE_CHOICES = [
        ("", "선택하세요"),
        ("경차", "경차"),
        ("소형", "소형"),
        ("준중형", "준중형"),
        ("중형", "중형"),
        ("대형", "대형"),
        ("SUV", "SUV"),
    ]
    car_type = forms.ChoiceField(
        label="차종",
        choices=CAR_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "form-control", "autocomplete": "off"}),
    )

    annual_mileage = forms.IntegerField(
        label="연간 주행거리 (km)",
        required=False,
        min_value=1000,
        max_value=100000,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "placeholder": "연간 주행거리를 입력하세요 (1,000~100,000km)",
                "autocomplete": "off",
            }
        ),
    )

    accident_history = forms.IntegerField(
        label="사고 경력 횟수",
        required=False,
        min_value=0,
        max_value=10,
        widget=forms.NumberInput(
            attrs={"class": "form-control", "autocomplete": "off"}
        ),
    )

    COVERAGE_LEVEL_CHOICES = [
        ("", "선택하세요"),
        ("기본", "기본"),
        ("표준", "표준"),
        ("고급", "고급"),
        ("프리미엄", "프리미엄"),
    ]
    coverage_level = forms.ChoiceField(
        label="보장 수준",
        choices=COVERAGE_LEVEL_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "form-control", "autocomplete": "off"}),
    )

    additional_coverage_interest = forms.BooleanField(
        label="추가 특약에 관심이 있나요?",
        required=False,
        widget=forms.CheckboxInput(
            attrs={"class": "form-check-input", "autocomplete": "off"}
        ),
    )

    class Meta:
        model = User
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "password1",
            "password2",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 비밀번호 필드 스타일링
        self.fields["username"].widget.attrs.update(
            {
                "class": "form-control",
                "placeholder": "아이디를 입력하세요",
                "autocomplete": "off",
            }
        )
        self.fields["password1"].widget.attrs.update(
            {
                "class": "form-control",
                "placeholder": "비밀번호를 입력하세요",
                "autocomplete": "new-password",
            }
        )
        self.fields["password2"].widget.attrs.update(
            {
                "class": "form-control",
                "placeholder": "비밀번호를 다시 입력하세요",
                "autocomplete": "new-password",
            }
        )

        # 필드 레이블 한글화
        self.fields["username"].label = "아이디"
        self.fields["password1"].label = "비밀번호"
        self.fields["password2"].label = "비밀번호 확인"

        # 도움말 텍스트
        self.fields["username"].help_text = (
            "150자 이하의 영문, 숫자, 특수문자만 사용 가능합니다."
        )
        self.fields["password1"].help_text = "8자 이상의 비밀번호를 입력하세요."
        self.fields["password2"].help_text = "위와 동일한 비밀번호를 입력하세요."

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            # 프로필 생성
            profile = UserProfile.objects.create(
                user=user,
                birth_date=self.cleaned_data.get("birth_date"),
                gender=self.cleaned_data.get("gender"),
                residence_area=self.cleaned_data.get("residence_area"),
                driving_experience=self.cleaned_data.get("driving_experience"),
                car_type=self.cleaned_data.get("car_type"),
                annual_mileage=self.cleaned_data.get("annual_mileage"),
                accident_history=self.cleaned_data.get("accident_history"),
                coverage_level=self.cleaned_data.get("coverage_level"),
                additional_coverage_interest=self.cleaned_data.get(
                    "additional_coverage_interest"
                ),
            )
        return user


class UserProfileUpdateForm(forms.ModelForm):
    """사용자 프로필 수정 폼"""

    # Choice 필드들 정의
    GENDER_CHOICES = [
        ("M", "남성"),
        ("F", "여성"),
    ]
    gender = forms.ChoiceField(
        label="성별",
        choices=GENDER_CHOICES,
        required=True,
        widget=forms.Select(attrs={"class": "form-control", "autocomplete": "off"}),
    )

    RESIDENCE_CHOICES = [
        ("", "선택하세요"),
        ("서울", "서울"),
        ("부산", "부산"),
        ("대구", "대구"),
        ("인천", "인천"),
        ("광주", "광주"),
        ("대전", "대전"),
        ("울산", "울산"),
        ("세종", "세종"),
        ("기타", "기타"),
    ]
    residence_area = forms.ChoiceField(
        label="거주 지역",
        choices=RESIDENCE_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "form-control", "autocomplete": "off"}),
    )

    CAR_TYPE_CHOICES = [
        ("", "선택하세요"),
        ("경차", "경차"),
        ("소형", "소형"),
        ("준중형", "준중형"),
        ("중형", "중형"),
        ("대형", "대형"),
        ("SUV", "SUV"),
    ]
    car_type = forms.ChoiceField(
        label="차종",
        choices=CAR_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "form-control", "autocomplete": "off"}),
    )

    COVERAGE_LEVEL_CHOICES = [
        ("", "선택하세요"),
        ("기본", "기본"),
        ("표준", "표준"),
        ("고급", "고급"),
        ("프리미엄", "프리미엄"),
    ]
    coverage_level = forms.ChoiceField(
        label="보장 수준",
        choices=COVERAGE_LEVEL_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "form-control", "autocomplete": "off"}),
    )

    class Meta:
        model = UserProfile
        fields = [
            "birth_date",
            "gender",
            "residence_area",
            "driving_experience",
            "car_type",
            "annual_mileage",
            "accident_history",
            "coverage_level",
            "additional_coverage_interest",
        ]
        widgets = {
            "birth_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date", "autocomplete": "off"}
            ),
            "driving_experience": forms.NumberInput(
                attrs={"class": "form-control", "autocomplete": "off"}
            ),
            "annual_mileage": forms.NumberInput(
                attrs={"class": "form-control", "autocomplete": "off"}
            ),
            "accident_history": forms.NumberInput(
                attrs={"class": "form-control", "autocomplete": "off"}
            ),
            "additional_coverage_interest": forms.CheckboxInput(
                attrs={"class": "form-check-input", "autocomplete": "off"}
            ),
        }
        labels = {
            "birth_date": "생년월일",
            "driving_experience": "운전 경력 (년)",
            "annual_mileage": "연간 주행거리 (km)",
            "accident_history": "사고 경력 횟수",
            "additional_coverage_interest": "추가 특약에 관심이 있나요?",
        }


class UserUpdateForm(forms.ModelForm):
    """사용자 기본 정보 수정 폼"""

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]
        widgets = {
            "first_name": forms.TextInput(
                attrs={"class": "form-control", "autocomplete": "off"}
            ),
            "last_name": forms.TextInput(
                attrs={"class": "form-control", "autocomplete": "off"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control", "autocomplete": "off"}
            ),
        }
        labels = {
            "first_name": "이름",
            "last_name": "성",
            "email": "이메일",
        }
