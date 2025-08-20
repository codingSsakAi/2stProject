from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django import forms
from django.contrib.auth.models import User
from .forms import CustomUserCreationForm, UserProfileUpdateForm
from .models import UserProfile


# 사용자 기본 정보 폼 (User 모델)
class UserBasicInfoForm(forms.ModelForm):
    username = forms.CharField(
        label="아이디",
        widget=forms.TextInput(attrs={"class": "form-control", "readonly": "readonly"}),
        required=False,
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
        }
        labels = {
            "first_name": "이름",
            "last_name": "성",
            "email": "이메일",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["username"].initial = self.instance.username


# 비밀번호 변경 폼
class PasswordChangeForm(forms.Form):
    current_password = forms.CharField(
        label="현재 비밀번호",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        required=False,
    )
    new_password = forms.CharField(
        label="새 비밀번호",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        required=False,
    )
    confirm_password = forms.CharField(
        label="새 비밀번호 확인",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        required=False,
    )

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean(self):
        cleaned_data = super().clean()
        current_password = cleaned_data.get("current_password")
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")

        # 현재 비밀번호가 입력된 경우에만 검증
        if current_password:
            if not new_password:
                raise forms.ValidationError("새 비밀번호를 입력해주세요.")
            if not confirm_password:
                raise forms.ValidationError("새 비밀번호 확인을 입력해주세요.")
            if new_password != confirm_password:
                raise forms.ValidationError(
                    "새 비밀번호와 확인 비밀번호가 일치하지 않습니다."
                )
            if len(new_password) < 8:
                raise forms.ValidationError("새 비밀번호는 8자 이상이어야 합니다.")

            # 새 비밀번호가 현재 비밀번호와 같은지 확인
            if current_password == new_password:
                raise forms.ValidationError(
                    "새 비밀번호는 현재 비밀번호와 달라야 합니다."
                )

        return cleaned_data


@login_required
def profile_view(request):
    """사용자 프로필 뷰"""
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        # 프로필이 없으면 생성
        profile = UserProfile.objects.create(user=request.user)

    # 사용자의 최근 추천 내역 조회
    from chatbot.insurance_service import InsuranceRecommendationService
    from chatbot.models import ChatSession
    from django.utils import timezone
    from datetime import date, timedelta
    from .models import InsuranceRecommendation
    from django.db.models import Count, Avg

    insurance_service = InsuranceRecommendationService()
    # 최근 추천 내역 조회 (chat_session이 있는 항목만)
    recent_recommendations = InsuranceRecommendation.objects.filter(
        user=request.user, chat_session__isnull=False  # chat_session이 연결된 항목만
    ).order_by("-created_at")[:5]

    # 실제 통계 데이터 조회

    # 최근 30일간의 통계 데이터
    end_date = date.today()
    start_date = end_date - timedelta(days=30)

    # 연령대별 통계
    age_group_stats = {}
    gender_stats = {"M": 0, "F": 0}
    car_type_stats = {}
    company_preference_stats = {}
    coverage_level_stats = {}
    region_stats = {}

    # 최근 추천 내역에서 통계 계산
    recent_recommendations_data = InsuranceRecommendation.objects.filter(
        created_at__date__gte=start_date
    ).select_related("user__profile")

    for rec in recent_recommendations_data:
        try:
            profile_data = rec.user.profile

            # 연령대별
            age_group = profile_data.get_age_group()
            age_group_stats[age_group] = age_group_stats.get(age_group, 0) + 1

            # 성별
            gender_stats[profile_data.gender] += 1

            # 차종별
            car_type = profile_data.car_type
            if car_type:
                car_type_stats[car_type] = car_type_stats.get(car_type, 0) + 1

            # 지역별
            region = profile_data.residence_area
            if region:
                region_stats[region] = region_stats.get(region, 0) + 1

            # 보장 수준별
            coverage = profile_data.coverage_level
            coverage_level_stats[coverage] = coverage_level_stats.get(coverage, 0) + 1

            # 보험사별 선호도 (선택된 경우)
            if rec.is_selected and rec.selected_company:
                company_preference_stats[rec.selected_company] = (
                    company_preference_stats.get(rec.selected_company, 0) + 1
                )
        except Exception as e:
            print(f"통계 계산 중 오류: {e}")
            continue

    # 사용자 통계 계산
    total_recommendations = InsuranceRecommendation.objects.filter(
        user=request.user,
        chat_session__isnull=False,  # chat_session이 연결된 항목만 카운트
    ).count()
    total_chat_sessions = ChatSession.objects.filter(user=request.user).count()
    days_since_joined = (timezone.now().date() - request.user.date_joined.date()).days

    # 디버깅을 위한 출력
    print("=== 전달되는 통계 데이터 ===")
    print(f"총 추천: {total_recommendations}")
    print(f"총 채팅 세션: {total_chat_sessions}")
    print(f"가입일: {days_since_joined}")
    print(f"연령대별: {age_group_stats}")
    print(f"성별: {gender_stats}")
    print(f"차종별: {car_type_stats}")
    print(f"보험사별: {company_preference_stats}")
    print(f"보장수준별: {coverage_level_stats}")
    print(f"지역별: {region_stats}")

    context = {
        "profile": profile,
        "recent_recommendations": recent_recommendations,
        "total_recommendations": total_recommendations,
        "total_chat_sessions": total_chat_sessions,
        "days_since_joined": days_since_joined,
        "version": "1.0.0",  # 버전 정보
        "age_group_stats": age_group_stats,
        "gender_stats": gender_stats,
        "car_type_stats": car_type_stats,
        "company_preference_stats": company_preference_stats,
        "coverage_level_stats": coverage_level_stats,
        "region_stats": region_stats,
    }
    return render(request, "accounts/profile.jinja.html", context)


@login_required
def profile_update_view(request):
    """프로필 수정 뷰"""
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)

    if request.method == "POST":
        profile_form = UserProfileUpdateForm(request.POST, instance=profile)
        user_form = UserBasicInfoForm(request.POST, instance=request.user)
        password_form = PasswordChangeForm(user=request.user, data=request.POST)

        # 비밀번호 변경 처리
        password_changed = False
        current_password = password_form.data.get("current_password", "")
        new_password = password_form.data.get("new_password", "")
        confirm_password = password_form.data.get("confirm_password", "")

        # 비밀번호 변경 시도가 있는 경우에만 처리
        if current_password or new_password or confirm_password:
            print(f"DEBUG: 비밀번호 변경 시도 감지")
            print(f"DEBUG: 현재 비밀번호 입력: {current_password}")
            print(f"DEBUG: 새 비밀번호 입력: {new_password}")
            print(f"DEBUG: 확인 비밀번호 입력: {confirm_password}")
            print(f"DEBUG: 사용자 비밀번호 해시: {request.user.password[:50]}...")
            print(
                f"DEBUG: check_password 결과: {request.user.check_password(current_password)}"
            )

            if not current_password:
                messages.error(request, "현재 비밀번호를 입력해주세요.")
            elif not new_password:
                messages.error(request, "새 비밀번호를 입력해주세요.")
            elif not confirm_password:
                messages.error(request, "새 비밀번호 확인을 입력해주세요.")
            elif len(new_password) < 8:
                messages.error(request, "새 비밀번호는 8자 이상이어야 합니다.")
            elif new_password != confirm_password:
                messages.error(
                    request, "새 비밀번호와 확인 비밀번호가 일치하지 않습니다."
                )
            elif not request.user.check_password(current_password):
                print(f"DEBUG: 현재 비밀번호 확인 실패")
                print(f"DEBUG: 입력된 비밀번호: {current_password}")
                print(f"DEBUG: 사용자 ID: {request.user.id}")
                print(f"DEBUG: 사용자명: {request.user.username}")
                messages.error(request, "현재 비밀번호가 올바르지 않습니다.")
            else:
                try:
                    # 새 비밀번호 설정
                    request.user.set_password(new_password)
                    request.user.save()
                    print("DEBUG: 비밀번호 변경 완료")
                    password_changed = True
                    messages.success(request, "비밀번호가 성공적으로 변경되었습니다.")
                except Exception as e:
                    print(f"DEBUG: 비밀번호 변경 오류: {str(e)}")
                    messages.error(
                        request, f"비밀번호 변경 중 오류가 발생했습니다: {str(e)}"
                    )

        # 프로필 정보 저장
        profile_saved = False
        if profile_form.is_valid() and user_form.is_valid():
            # 실제로 변경사항이 있는지 확인
            profile_has_changes = profile_form.has_changed()
            user_has_changes = user_form.has_changed()

            if profile_has_changes or user_has_changes:
                try:
                    if profile_has_changes:
                        profile_form.save()
                    if user_has_changes:
                        user_form.save()
                    profile_saved = True
                    messages.success(request, "프로필이 성공적으로 업데이트되었습니다.")
                except Exception as e:
                    messages.error(
                        request, f"프로필 저장 중 오류가 발생했습니다: {str(e)}"
                    )
            else:
                messages.info(request, "변경사항이 없습니다.")

        # 성공적으로 처리된 경우 리다이렉트
        if password_changed or profile_saved:
            return redirect("accounts:profile")
    else:
        profile_form = UserProfileUpdateForm(instance=profile)
        user_form = UserBasicInfoForm(instance=request.user)
        password_form = PasswordChangeForm(user=request.user)

    context = {
        "profile_form": profile_form,
        "user_form": user_form,
        "password_form": password_form,
        "profile": profile,
    }
    return render(request, "accounts/profile_update.jinja.html", context)


def register_view(request):
    """회원가입 뷰"""
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # 자동 로그인
            login(request, user)
            messages.success(request, "회원가입이 완료되었습니다!")
            return redirect("home")
    else:
        form = CustomUserCreationForm()

    context = {"form": form}
    return render(request, "accounts/register.jinja.html", context)


def login_view(request):
    """로그인 뷰"""
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"{username}님, 환영합니다!")
                return redirect("home")
    else:
        form = AuthenticationForm()

    context = {"form": form}
    return render(request, "accounts/login.jinja.html", context)


def logout_view(request):
    """로그아웃 뷰"""
    logout(request)
    messages.success(request, "로그아웃되었습니다.")
    return redirect("home")


@login_required
@require_http_methods(["GET"])
def api_statistics_view(request):
    """통계 데이터 API 뷰"""
    try:
        from django.db.models import Count, Avg
        from datetime import date, timedelta
        from .models import InsuranceRecommendation

        # 전체 데이터 조회 (최근 30일 제한 제거)
        recent_recommendations_data = (
            InsuranceRecommendation.objects.all().select_related("user__profile")
        )

        # 연령대별 통계
        age_group_stats = {}
        gender_stats = {"M": 0, "F": 0}
        car_type_stats = {}
        company_preference_stats = {}
        coverage_level_stats = {}
        region_stats = {}

        for rec in recent_recommendations_data:
            try:
                profile_data = rec.user.profile
                age_group = profile_data.get_age_group()
                age_group_stats[age_group] = age_group_stats.get(age_group, 0) + 1
                gender_stats[profile_data.gender] += 1
                car_type = profile_data.car_type
                if car_type:
                    car_type_stats[car_type] = car_type_stats.get(car_type, 0) + 1
                region = profile_data.residence_area
                if region:
                    region_stats[region] = region_stats.get(region, 0) + 1
                coverage = profile_data.coverage_level
                coverage_level_stats[coverage] = (
                    coverage_level_stats.get(coverage, 0) + 1
                )
                if rec.is_selected and rec.selected_company:
                    company_preference_stats[rec.selected_company] = (
                        company_preference_stats.get(rec.selected_company, 0) + 1
                    )
            except Exception as e:
                print(f"Error processing recommendation {rec.id}: {e}")
                continue

        statistics = {
            "age_groups": age_group_stats,
            "genders": gender_stats,
            "car_types": car_type_stats,
            "companies": company_preference_stats,
            "coverage_levels": coverage_level_stats,
            "regions": region_stats,
        }

        insights = [
            {
                "title": "인기 연령대",
                "content": f"가장 많은 추천을 받은 연령대는 {max(age_group_stats.items(), key=lambda x: x[1])[0] if age_group_stats else 'N/A'}입니다.",
            },
            {
                "title": "선호 보험사",
                "content": f"가장 인기 있는 보험사는 {max(company_preference_stats.items(), key=lambda x: x[1])[0] if company_preference_stats else 'N/A'}입니다.",
            },
        ]

        return JsonResponse(
            {"success": True, "statistics": statistics, "insights": insights}
        )

    except Exception as e:
        print(f"API Statistics Error: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)
