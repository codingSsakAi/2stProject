# insurance_app/urls.py
# 마이페이지 루트 연결
    path(
        "",
        include(("accident_project.urls", "accident_project"), namespace="accident_project"),
    ),

# insurance_app/templates/insurance_app/home.html
        # <!-- 하단: 텍스트 링크 → 버튼화 -->
        <div class="nav-bar">
          <a class="nav-btn" href="{% url 'accident_project:mypage_agreements' %}">마이페이지</a>
          <a class="nav-btn" href="{% url 'accident_project:agreement_new' %}">+ 교통사고 협의서 작성</a>
        </div>

# insurance_project/settings.py
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    'insurance_app',
    'rest_framework',
    'insurance_portal',
    'accident_project', # 추가 
]

X_FRAME_OPTIONS = "SAMEORIGIN"  # 성미 추가 iframe 로 이동 가능