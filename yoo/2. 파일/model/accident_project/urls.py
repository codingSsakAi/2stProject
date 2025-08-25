# from django.urls import path
# from django.views.generic import TemplateView
# # from .views import generate_report
# from . import views


# app_name = 'report_form' # namespace 선언

# from django.urls import path
# from . import views

# app_name = 'report_form'  # namespace 선언

# urlpatterns = [
#     path("agreement/form/", views.form_view, name="agreement_form"),
#     path("agreement/print/", views.print_view, name="agreement_print"),
#     path('agreement/download/pdf/', views.download_pdf, name='download_pdf'),
#     path('agreement/download/image/', views.download_image, name='download_image'),
#     # path("print/", views.agreement_print, name="agreement_print"),
#     # path('generate/', views.generate_report, name='generate_report'),
# ]
# accident_project/urls.py
# from django.urls import path
# from django.views.generic import RedirectView
# from . import views

# app_name = "accident_project"   # 네임스페이스 이름

# urlpatterns = [
#     path("", views.home, name="home"),

#     # 새 작성 / 수정 / 보기(인쇄)
#     path("agreements/new/", views.agreement_form, name="agreement_new"),
#     path("agreements/<int:pk>/edit/", views.agreement_form, name="agreement_edit"),
#     path("agreements/<int:pk>/", views.agreement_print, name="agreement_print"),

#     # ★ 폼 POST 저장
#     path("agreements/submit/", views.agreement_submit, name="agreement_submit"),

#     # 파일 다운로드
#     path("agreements/<int:pk>/pdf/", views.agreement_pdf, name="agreement_pdf"),
#     path("agreements/<int:pk>/image/", views.agreement_image, name="agreement_image"),

#     # ★★★ 미리보기(정식 경로/네임스페이스 추가)
#     path("agreements/preview/", views.agreement_preview, name="agreement_preview"),

#     # 마이페이지
#     path("mypage/", views.mypage, name="mypage"),
#     path("mypage/agreements/", views.mypage_agreements, name="mypage_agreements"),

#     # ───── Legacy 경로 호환(리다이렉트) ─────
#     path("agreement/form/",   RedirectView.as_view(pattern_name="accident_project:agreement_new",  permanent=True)),
#     path("agreement/submit/", RedirectView.as_view(pattern_name="accident_project:agreement_new",  permanent=True)),
#     path("agreement/preview/",RedirectView.as_view(url="/agreements/new/", permanent=True)),  # 유지
#     path("agreement/print/<int:pk>/", RedirectView.as_view(pattern_name="accident_project:agreement_print", permanent=True)),
#     path("agreement/pdf/<int:pk>/",   RedirectView.as_view(pattern_name="accident_project:agreement_pdf",   permanent=True)),
#     path("agreement/jpg/<int:pk>/",   RedirectView.as_view(pattern_name="accident_project:agreement_image", permanent=True)),
#     path("records/<int:pk>/",         RedirectView.as_view(pattern_name="accident_project:agreement_edit",  permanent=True)),
#     path("records/<int:pk>/print/",   RedirectView.as_view(pattern_name="accident_project:agreement_print", permanent=True)),
# ]

from django.urls import path
from django.views.generic import RedirectView
from . import views

# app_name = "accident_project"

urlpatterns = [
    # 홈
    path("", views.home, name="home"),

    # 폼/출력
    path("agreements/new/", views.agreement_form, name="agreement_new"),
    path("agreements/<int:pk>/", views.agreement_print, name="agreement_print"),

    # 저장(POST)
    path("agreements/submit/", views.agreement_submit, name="agreement_submit"),

    # 미리보기(로컬스토리지 기반)
    path("agreements/preview/", views.agreement_preview, name="agreement_preview"),

    # 파일 다운로드(Fallback 서버 사이드)
    path("agreements/<int:pk>/pdf/", views.agreement_pdf, name="agreement_pdf"),
    path("agreements/<int:pk>/image/", views.agreement_image, name="agreement_image"),

    # 마이페이지
    path("mypage/", views.mypage, name="mypage"),
    path("mypage/agreements/", views.mypage_agreements, name="mypage_agreements"),

    # ───────── Legacy 경로 호환(과거 링크 살리기) ─────────
    path("agreement/form/",   RedirectView.as_view(pattern_name="accident_project:agreement_new",  permanent=True)),
    path("agreement/submit/", RedirectView.as_view(pattern_name="accident_project:agreement_new",  permanent=True)),
    path("agreement/preview/",RedirectView.as_view(pattern_name="accident_project:agreement_preview", permanent=True)),
    path("agreement/print/<int:pk>/", RedirectView.as_view(pattern_name="accident_project:agreement_print", permanent=True)),
    path("agreement/pdf/<int:pk>/",   RedirectView.as_view(pattern_name="accident_project:agreement_pdf",   permanent=True)),
    path("agreement/jpg/<int:pk>/",   RedirectView.as_view(pattern_name="accident_project:agreement_image", permanent=True)),
]
