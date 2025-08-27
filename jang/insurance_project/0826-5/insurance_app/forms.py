from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser

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