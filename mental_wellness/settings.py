import os
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-change-me-in-production')
DEBUG      = os.environ.get('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost 127.0.0.1').split()

# Render injects this automatically — it is the app's public hostname.
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'anymail',    # ← required for django-anymail
    'wellness',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'mental_wellness.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'mental_wellness.wsgi.application'

# ── Database ──────────────────────────────────────────────────────────────────
DATABASES = {
    'default': dj_database_url.config(
        default=f'sqlite:///{BASE_DIR / "db.sqlite3"}',
        conn_max_age=600,
    )
}

# ── Password validation ───────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ── Auth redirects ────────────────────────────────────────────────────────────
LOGIN_URL           = '/login/'
LOGIN_REDIRECT_URL  = '/'
LOGOUT_REDIRECT_URL = '/'

# ── Internationalisation ──────────────────────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE     = 'UTC'
USE_I18N      = True
USE_TZ        = True

# ── Static files ─────────────────────────────────────────────────────────────
STATIC_URL  = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Django 4.2+ / whitenoise 6 correct way to configure storage.
# WHITENOISE_MANIFEST_STRICT = False prevents ValueError on admin font
# references that are absent from the manifest after collectstatic.
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}
WHITENOISE_MANIFEST_STRICT = False

# ── Email — Anymail / Resend HTTP API ─────────────────────────────────────────
#
# Why Anymail + Resend instead of SMTP:
#   Render Free blocks outbound port 587 (SMTP), causing [Errno 101]
#   Network is unreachable. Anymail sends via Resend's HTTPS API instead,
#   which is never blocked. The existing send_mail() calls in views.py
#   do NOT need to change — Django routes them through this backend.
#
# Setup:
#   1. Create a free account at https://resend.com
#   2. Add and verify your sender domain (or use onboarding@resend.dev for testing)
#   3. Create an API key at https://resend.com/api-keys
#   4. Add RESEND_API_KEY to your Render environment variables
#   5. Set DEFAULT_FROM_EMAIL to a verified sender address

EMAIL_BACKEND   = 'anymail.backends.resend.EmailBackend'
DEFAULT_FROM_EMAIL = os.environ.get(
    'DEFAULT_FROM_EMAIL', 'Mind Companion <onboarding@resend.dev>'
)

ANYMAIL = {
    'RESEND_API_KEY': os.environ.get('RESEND_API_KEY', ''),
}

# ── Device Trust cookie (2FA bypass for trusted browsers) ────────────────────
#
# When a user passes 2FA, we set a signed cookie named TRUSTED_DEVICE_COOKIE.
# On next login, if the cookie is present and valid, 2FA is skipped.
# The cookie is signed with Django's SECRET_KEY via get_signed_cookie() /
# set_signed_cookie(), so it cannot be forged by the user.

TRUSTED_DEVICE_COOKIE     = 'mc_trusted_device'   # cookie name
TRUSTED_DEVICE_COOKIE_AGE = 60 * 60 * 24 * 30     # 30 days in seconds

# ── API keys ──────────────────────────────────────────────────────────────────
YOUTUBE_API_KEY   = os.environ.get('YOUTUBE_API_KEY', '')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── Logging ───────────────────────────────────────────────────────────────────
# Forces full tracebacks to stdout (visible in Render's Logs tab)
# even when DEBUG = False.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{asctime} {levelname} {name} {message}',
            'style':  '{',
        },
    },
    'handlers': {
        'console': {
            'class':     'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level':    'WARNING',
        },
        'django.request': {
            'handlers':  ['console'],
            'level':     'ERROR',
            'propagate': False,
        },
        'django': {
            'handlers':  ['console'],
            'level':     'ERROR',
            'propagate': False,
        },
        'wellness': {
            'handlers':  ['console'],
            'level':     'DEBUG',
            'propagate': False,
        },
    },
}
