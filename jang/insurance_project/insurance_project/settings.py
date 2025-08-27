from pathlib import Path
from dotenv import load_dotenv
import os
import sys

BASE_DIR = Path(__file__).resolve().parent.parent

# 0826-5 안의 앱들을 파이썬 import 경로에 추가 (아카이브 폴더 인식용)
sys.path.append(str(BASE_DIR / "0826-5"))

# ───────────────── 보안/디버그 ─────────────────
SECRET_KEY = "django-insecure-^=1vv+pprwz$1uft-f*mx157fvf(n9v#nnb%ygm$np!o&%wb_s"
DEBUG = True
ALLOWED_HOSTS = ["*", "localhost", "127.0.0.1"]

# ───────────────── 앱 구성 ─────────────────
INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    # 프로젝트 앱
    "insurance_app",
    "accident_project",
    # 서드파티
    "rest_framework",
]

# 아카이브(0826-5/insurance_portal) 또는 프로젝트 루트(insurance_portal) 중 존재하는 쪽만 앱으로 등록
if (BASE_DIR / "insurance_portal").exists() or (BASE_DIR / "0826-5" / "insurance_portal").exists():
    INSTALLED_APPS.append("insurance_portal")

AUTH_USER_MODEL = "insurance_app.CustomUser"

# ───────────────── 환경 변수 ─────────────────
load_dotenv()
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENV = os.getenv("PINECONE_ENV")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ───────────────── 미들웨어 ─────────────────
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "insurance_project.urls"
WSGI_APPLICATION = "insurance_project.wsgi.application"

# ───────────────── 템플릿 ─────────────────
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "templates",
            BASE_DIR / "insurance_app" / "templates",
            # ✅ 아카이브 템플릿 경로(이 폴더에 partial들이 들어있음)
            BASE_DIR / "0826-5" / "insurance_portal" / "templates",
            # 루트에 풀어뒀다면 이것도 커버
            BASE_DIR / "insurance_portal" / "templates",
        ],
        "APP_DIRS": True,  # 각 앱의 templates 자동 탐색
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ───────────────── 데이터베이스 ─────────────────
DATABASES = {
    "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}
}

# ───────────────── 인증/국제화 ─────────────────
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "ko-kr"
TIME_ZONE = "Asia/Seoul"
USE_I18N = True
USE_TZ = True

# ───────────────── 정적/미디어 ─────────────────
STATIC_URL = "/static/"

# 존재하는 폴더만 추가(아카이브 정적파일 경로 포함)
_static_candidates = [
    BASE_DIR / "insurance_app" / "static",
    BASE_DIR / "accident_project" / "static",
    BASE_DIR / "insurance_portal" / "static",                    # 루트에 둘 때
    BASE_DIR / "0826-5" / "insurance_portal" / "static",         # ✅ 아카이브 폴더에 둘 때
]
STATICFILES_DIRS = [p for p in _static_candidates if p.exists()]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ───────────────── 기타 ─────────────────
USE_MOCK_API = True
LOGIN_URL = "/login/"
X_FRAME_OPTIONS = "SAMEORIGIN"

DOCUMENTS_URL = "/documents/"
DOCUMENTS_ROOT = BASE_DIR / "documents"
