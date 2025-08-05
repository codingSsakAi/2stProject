"""
Django settings for insurance_project project.
"""

import os
from pathlib import Path
from decouple import config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config(
    "SECRET_KEY",
    default="django-insecure-s(=fut_i1fz@a=&ky!5i*eiu8^nzx^*-yg#%e2dnh^942oj@58",
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config("DEBUG", default=True, cast=bool)

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1").split(",")

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "insurance",
    "users",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "insurance_project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "insurance_project.wsgi.application"

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = config("LANGUAGE_CODE", default="ko-kr")

TIME_ZONE = config("TIME_ZONE", default="Asia/Seoul")

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = "static/"
STATICFILES_DIRS = [
    BASE_DIR / "static",
]
STATIC_ROOT = BASE_DIR / "staticfiles"

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Media files
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# REST Framework settings
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
}

# CORS settings
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS", default="http://localhost:3000,http://127.0.0.1:3000"
).split(",")
CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS", default="http://localhost:3000,http://127.0.0.1:3000"
).split(",")

# File Upload Settings
MAX_UPLOAD_SIZE = config("MAX_UPLOAD_SIZE", default="10485760", cast=int)  # 10MB
ALLOWED_FILE_TYPES = config("ALLOWED_FILE_TYPES", default="pdf,docx").split(",")

# Pinecone Settings
PINECONE_API_KEY = config("PINECONE_API_KEY", default="")
PINECONE_ENVIRONMENT = config("PINECONE_ENVIRONMENT", default="gcp-starter")
PINECONE_INDEX_NAME = config("PINECONE_INDEX_NAME", default="insurance-documents-main")

# OpenAI Settings
OPENAI_API_KEY = config("OPENAI_API_KEY", default="")
OPENAI_MODEL = config("OPENAI_MODEL", default="gpt-4.1-nano")
OPENAI_MAX_TOKENS = config("OPENAI_MAX_TOKENS", default=2000, cast=int)
OPENAI_TEMPERATURE = config("OPENAI_TEMPERATURE", default=0.7, cast=float)

# Upstage Embedding Settings
UPSTAGE_API_KEY = config("UPSTAGE_API_KEY", default="")
UPSTAGE_EMBEDDING_MODEL = config(
    "UPSTAGE_EMBEDDING_MODEL", default="solar-embedding-1-large"
)
UPSTAGE_EMBEDDING_DIMENSION = config(
    "UPSTAGE_EMBEDDING_DIMENSION", default=4096, cast=int
)

# RAG Settings
CHUNK_SIZE = config("CHUNK_SIZE", default=1000, cast=int)
CHUNK_OVERLAP = config("CHUNK_OVERLAP", default=200, cast=int)
MAX_TOKENS_PER_CHUNK = config("MAX_TOKENS_PER_CHUNK", default=4000, cast=int)

# Mock API Settings
MOCK_API_BASE_URL = config("MOCK_API_BASE_URL", default="http://localhost:8001")
MOCK_API_TIMEOUT = config("MOCK_API_TIMEOUT", default=30, cast=int)
