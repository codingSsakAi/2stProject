from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import CustomUserCreationForm, UserProfileUpdateForm, UserUpdateForm
from .models import UserProfile


def register_view(request):
    """회원가입 뷰"""
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            # 사용자 생성 (프로필도 함께 생성됨)
            user = form.save()

            # 자동 로그인
            login(request, user)
            messages.success(request, "회원가입이 완료되었습니다!")
            return redirect("home")
        else:
            # 폼 오류 디버깅
    
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
            messages.error(
                request, "회원가입에 실패했습니다. 입력 정보를 확인해주세요."
            )
    else:
        form = CustomUserCreationForm()

    return render(request, "accounts/register.jinja.html", {"form": form})


def login_view(request):
    """로그인 뷰"""
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f"{user.username}님, 환영합니다!")
            next_url = request.GET.get("next", "home")
            return redirect(next_url)
        else:
            messages.error(request, "아이디 또는 비밀번호가 올바르지 않습니다.")

    return render(request, "accounts/login.jinja.html")


def logout_view(request):
    """로그아웃 뷰"""
    logout(request)
    messages.success(request, "로그아웃되었습니다.")
    return redirect("home")


@login_required
def profile_view(request):
    """사용자 프로필 뷰"""
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        # 프로필이 없는 경우 생성
        profile = UserProfile.objects.create(
            user=request.user, birth_date="2000-01-01", gender="M"  # 기본값  # 기본값
        )

    context = {"profile": profile, "user": request.user, "version": "1.1"}
    return render(request, "accounts/profile.jinja.html", context)


@login_required
def profile_update_view(request):
    """프로필 수정 뷰"""
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(
            user=request.user, birth_date="2000-01-01", gender="M"
        )

    if request.method == "POST":
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = UserProfileUpdateForm(request.POST, instance=profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "프로필이 성공적으로 수정되었습니다.")
            return redirect("accounts:profile")
        else:
            # 폼 오류 디버깅
    
            for field, errors in user_form.errors.items():
                for error in errors:
                    messages.error(request, f"사용자 정보 - {field}: {error}")
            for field, errors in profile_form.errors.items():
                for error in errors:
                    messages.error(request, f"프로필 정보 - {field}: {error}")
            messages.error(
                request, "프로필 수정에 실패했습니다. 입력 정보를 확인해주세요."
            )
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = UserProfileUpdateForm()  # 빈 폼으로 생성

    context = {"user_form": user_form, "profile_form": profile_form}
    return render(request, "accounts/profile_update.jinja.html", context)


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    """프로필 수정 클래스 기반 뷰 (대안)"""

    model = UserProfile
    form_class = UserProfileUpdateForm
    template_name = "accounts/profile_update.jinja.html"
    success_url = reverse_lazy("profile")

    def get_object(self):
        try:
            return self.request.user.profile
        except UserProfile.DoesNotExist:
            return UserProfile.objects.create(
                user=self.request.user, birth_date="2000-01-01", gender="M"
            )

    def form_valid(self, form):
        messages.success(self.request, "프로필이 성공적으로 수정되었습니다.")
        return super().form_valid(form)
