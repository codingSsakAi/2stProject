from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.db import transaction
from datetime import date
from .forms import UserRegistrationForm, UserProfileForm, UserLoginForm
from .models import UserProfile


def register_view(request):
    """회원가입 뷰"""
    if request.user.is_authenticated:
        return redirect("main_page")

    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # 사용자 생성
                    user = form.save(commit=False)
                    user.email = form.cleaned_data["email"]
                    user.save()

                    # UserProfile 생성
                    birth_date = form.cleaned_data["birth_date"]
                    age = calculate_age(birth_date)

                    UserProfile.objects.create(user=user, age=age)

                    # 자동 로그인
                    login(request, user)
                    messages.success(request, "회원가입이 완료되었습니다!")
                    return redirect("profile")

            except Exception as e:
                messages.error(request, f"회원가입 중 오류가 발생했습니다: {str(e)}")
    else:
        form = UserRegistrationForm()

    return render(
        request, "users/register.jinja.html", {"form": form, "title": "회원가입"}
    )


def login_view(request):
    """로그인 뷰"""
    if request.user.is_authenticated:
        return redirect("main_page")

    if request.method == "POST":
        form = UserLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]
            remember_me = form.cleaned_data.get("remember_me", False)

            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)

                # 로그인 성공 메시지
                messages.success(request, f"{user.username}님, 환영합니다!")

                # 다음 페이지로 리다이렉트
                next_url = request.GET.get("next", "main_page")
                return redirect(next_url)
            else:
                messages.error(request, "아이디 또는 비밀번호가 올바르지 않습니다.")
    else:
        form = UserLoginForm()

    return render(request, "users/login.jinja.html", {"form": form, "title": "로그인"})


@login_required
def logout_view(request):
    """로그아웃 뷰"""
    logout(request)
    messages.success(request, "로그아웃되었습니다.")
    return redirect("main_page")


@login_required
def profile_view(request):
    """프로필 관리 뷰"""
    user = request.user

    # UserProfile이 없으면 생성
    profile, created = UserProfile.objects.get_or_create(user=user)

    if request.method == "POST":
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "프로필이 업데이트되었습니다.")
            return redirect("profile")
    else:
        form = UserProfileForm(instance=profile)

    # 프로필 완성도 계산
    completion_rate = calculate_profile_completion(profile)

    return render(
        request,
        "users/profile.jinja.html",
        {
            "form": form,
            "profile": profile,
            "completion_rate": completion_rate,
            "title": "프로필 관리",
        },
    )


@login_required
def profile_completion_view(request):
    """프로필 완성도 안내 뷰"""
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    completion_rate = calculate_profile_completion(profile)

    return render(
        request,
        "users/profile_completion.jinja.html",
        {
            "profile": profile,
            "completion_rate": completion_rate,
            "title": "프로필 완성도",
        },
    )


def calculate_age(birth_date):
    """나이 계산"""
    today = date.today()
    age = (
        today.year
        - birth_date.year
        - ((today.month, today.day) < (birth_date.month, birth_date.day))
    )
    return age


def calculate_profile_completion(profile):
    """프로필 완성도 계산"""
    total_fields = 6  # 총 필드 수
    completed_fields = 0

    # 각 필드별 완성도 체크
    if profile.car_number:
        completed_fields += 1
    if profile.driving_experience is not None:
        completed_fields += 1
    if profile.gender:
        completed_fields += 1
    if profile.residence_area:
        completed_fields += 1
    if profile.annual_mileage is not None:
        completed_fields += 1
    if profile.accident_history is not None:
        completed_fields += 1

    return int((completed_fields / total_fields) * 100)
