from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import CustomUser
from django.contrib.auth import password_validation

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    birth_date = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text='생년월일을 입력해주세요.'
    )
    gender = forms.ChoiceField(
        choices=CustomUser.GENDER_CHOICES,
        required=True,
        help_text='성별을 선택해주세요.'
    )
    has_license = forms.BooleanField(
        required=False,
        help_text='운전면허증을 소지하고 계신가요?'
    )

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'password1', 'password2', 'birth_date', 'gender', 'has_license')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.birth_date = self.cleaned_data['birth_date']
        user.gender = self.cleaned_data['gender']
        user.has_license = self.cleaned_data['has_license']
        if commit:
            user.save()
        return user
    
class CustomUserChangeForm(UserChangeForm):
    email = forms.EmailField(required=True)
    birth_date = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text='생년월일을 입력해주세요.'
    )
    gender = forms.ChoiceField(
        choices=CustomUser.GENDER_CHOICES,
        required=True,
        help_text='성별을 선택해주세요.'
    )
    has_license = forms.BooleanField(
        required=False,
        help_text='운전면허증을 소지하고 계신가요?'
    )

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'birth_date', 'gender', 'has_license')
        # username을 수정불가로 하고 싶다면 disabled 속성 사용 가능

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.birth_date = self.cleaned_data['birth_date']
        user.gender = self.cleaned_data['gender']
        user.has_license = self.cleaned_data['has_license']
        if commit:
            user.save()
        return user
    
class EmailPasswordChangeForm(forms.ModelForm):
    current_password = forms.CharField(
        label="현재 비밀번호",
        widget=forms.PasswordInput,
        required=True
    )
    new_password1 = forms.CharField(
        label="새 비밀번호",
        widget=forms.PasswordInput,
        required=False,
        help_text=password_validation.password_validators_help_text_html(),
    )
    new_password2 = forms.CharField(
        label="새 비밀번호 확인",
        widget=forms.PasswordInput,
        required=False
    )

    class Meta:
        model = CustomUser
        fields = ('email',)  # 수정가능한 필드만

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        self.fields['email'].required = True

    def clean_current_password(self):
        current_password = self.cleaned_data.get("current_password")
        if not self.user.check_password(current_password):
            raise forms.ValidationError("현재 비밀번호가 일치하지 않습니다.")
        return current_password

    def clean(self):
        cleaned_data = super().clean()
        pwd1 = cleaned_data.get("new_password1")
        pwd2 = cleaned_data.get("new_password2")
        if pwd1 or pwd2:
            if pwd1 != pwd2:
                self.add_error("new_password2", "새 비밀번호가 일치하지 않습니다.")
            else:
                password_validation.validate_password(pwd1, self.user)
        return cleaned_data

    def save(self, commit=True):
        user = self.user
        user.email = self.cleaned_data.get("email")
        pwd1 = self.cleaned_data.get("new_password1")
        if pwd1:
            user.set_password(pwd1)
        if commit:
            user.save()
        return user
    
class UserProfileChangeForm(forms.ModelForm):
    current_password = forms.CharField(
        label="현재 비밀번호",
        widget=forms.PasswordInput,
        required=True
    )
    new_password1 = forms.CharField(
        label="새 비밀번호",
        widget=forms.PasswordInput,
        required=False,
        help_text=password_validation.password_validators_help_text_html(),
    )
    new_password2 = forms.CharField(
        label="새 비밀번호 확인",
        widget=forms.PasswordInput,
        required=False
    )

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'birth_date', 'gender', 'has_license')
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        self.fields['username'].required = True
        self.fields['email'].required = True
        self.fields['birth_date'].required = True
        self.fields['gender'].required = True
        # 운전면허는 불리언

    def clean_current_password(self):
        current_password = self.cleaned_data.get("current_password")
        if not self.user.check_password(current_password):
            raise forms.ValidationError("현재 비밀번호가 일치하지 않습니다.")
        return current_password

    def clean(self):
        cleaned_data = super().clean()
        pwd1 = cleaned_data.get("new_password1")
        pwd2 = cleaned_data.get("new_password2")
        if pwd1 or pwd2:
            if pwd1 != pwd2:
                self.add_error("new_password2", "새 비밀번호가 일치하지 않습니다.")
            else:
                password_validation.validate_password(pwd1, self.user)
        return cleaned_data

    def save(self, commit=True):
        user = self.user
        for field in ['username', 'email', 'birth_date', 'gender', 'has_license']:
            setattr(user, field, self.cleaned_data.get(field))
        pwd1 = self.cleaned_data.get("new_password1")
        if pwd1:
            user.set_password(pwd1)
        if commit:
            user.save()
        return user