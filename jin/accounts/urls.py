from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    # 인증 관련
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    # 프로필 관련
    path("profile/", views.profile_view, name="profile"),
    path("profile/update/", views.profile_update_view, name="profile_update"),
]
