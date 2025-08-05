from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import UserProfile
from datetime import date

class UserRegistrationForm(UserCreationForm):
    """회원가입 폼"""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': '이메일을 입력하세요'
        })
    )
    birth_date = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'placeholder': '생년월일을 선택하세요'
        }),
        help_text='보험료 계산에 필요한 정보입니다.'
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'birth_date', 'password1', 'password2']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 폼 필드 스타일링
        for field in self.fields.values():
            if isinstance(field.widget, (forms.TextInput, forms.PasswordInput)):
                field.widget.attrs.update({
                    'class': 'form-control',
                    'placeholder': field.label
                })
    
    def clean_birth_date(self):
        birth_date = self.cleaned_data.get('birth_date')
        if birth_date:
            today = date.today()
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
            if age < 18:
                raise forms.ValidationError('18세 이상만 가입 가능합니다.')
            if age > 100:
                raise forms.ValidationError('올바른 생년월일을 입력해주세요.')
        return birth_date

class UserProfileForm(forms.ModelForm):
    """사용자 프로필 수정 폼"""
    GENDER_CHOICES = [
        ('', '성별 선택'),
        ('M', '남성'),
        ('F', '여성'),
    ]
    
    gender = forms.ChoiceField(
        choices=GENDER_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    car_type_choices = [
        ('', '차종 선택'),
        ('경차', '경차'),
        ('소형', '소형차'),
        ('준중형', '준중형차'),
        ('중형', '중형차'),
        ('대형', '대형차'),
        ('SUV', 'SUV'),
    ]
    
    car_type = forms.ChoiceField(
        choices=car_type_choices,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    region_choices = [
        ('', '지역 선택'),
        ('서울', '서울'),
        ('부산', '부산'),
        ('대구', '대구'),
        ('인천', '인천'),
        ('광주', '광주'),
        ('대전', '대전'),
        ('울산', '울산'),
        ('세종', '세종'),
        ('경기', '경기도'),
        ('강원', '강원도'),
        ('충북', '충청북도'),
        ('충남', '충청남도'),
        ('전북', '전라북도'),
        ('전남', '전라남도'),
        ('경북', '경상북도'),
        ('경남', '경상남도'),
        ('제주', '제주도'),
    ]
    
    residence_area = forms.ChoiceField(
        choices=region_choices,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    class Meta:
        model = UserProfile
        fields = [
            'car_number', 'driving_experience', 'gender', 'residence_area',
            'annual_mileage', 'accident_history', 'car_type'
        ]
        widgets = {
            'car_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '예: 12가3456'
            }),
            'driving_experience': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '운전 경력 (년)',
                'min': '0',
                'max': '50'
            }),
            'annual_mileage': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '연간 주행거리 (km)',
                'min': '0',
                'max': '100000'
            }),
            'accident_history': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '사고 이력 (건)',
                'min': '0',
                'max': '10'
            }),
        }
    
    def clean_car_number(self):
        car_number = self.cleaned_data.get('car_number')
        if car_number:
            # 차량번호 형식 검증 (간단한 예시)
            if len(car_number) < 6:
                raise forms.ValidationError('올바른 차량번호를 입력해주세요.')
        return car_number
    
    def clean_driving_experience(self):
        experience = self.cleaned_data.get('driving_experience')
        if experience is not None and experience < 0:
            raise forms.ValidationError('운전 경력은 0년 이상이어야 합니다.')
        return experience
    
    def clean_annual_mileage(self):
        mileage = self.cleaned_data.get('annual_mileage')
        if mileage is not None and mileage < 0:
            raise forms.ValidationError('연간 주행거리는 0km 이상이어야 합니다.')
        return mileage
    
    def clean_accident_history(self):
        accidents = self.cleaned_data.get('accident_history')
        if accidents is not None and accidents < 0:
            raise forms.ValidationError('사고 이력은 0건 이상이어야 합니다.')
        return accidents

class UserLoginForm(forms.Form):
    """로그인 폼"""
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '아이디를 입력하세요'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '비밀번호를 입력하세요'
        })
    )
    remember_me = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    ) 