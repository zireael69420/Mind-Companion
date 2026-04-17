import os
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-change-me-in-production')
DEBUG      = os.environ.get('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost 127.0.0.1').split()

# Render injects RENDER_EXTERNAL_HOSTNAME automatically.
# Without it every request is rejected with 400 → gunicorn shows 502.
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
    'anymail',
    'wellness',
]

# ── Middleware ────────────────────────────────────────────────────────────────
# ORDER IS MANDATORY:
#   1. SecurityMiddleware  — must be first
#   2. WhiteNoiseMiddleware — must be immediately after Security, before everything else
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',   # serves static files in production
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
        'DIRS': [BASE_DIR / 'templates'],  # project-level templates/registration/
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
# Uses DATABASE_URL env var on Render (Neon PostgreSQL).
# Falls back to SQLite locally when DATABASE_URL is not set.
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
#
# STATIC_URL   : URL prefix used in {% static '...' %} template tags.
# STATIC_ROOT  : Absolute path where collectstatic copies every static file.
#                WhiteNoise serves files from here in production.
# STORAGES     : Django 4.2+ way to configure storage backends.
#                CompressedManifestStaticFilesStorage adds a content-hash to
#                filenames (e.g. admin.css → admin.abc123.css) for cache-busting.
#
# WHITENOISE_MANIFEST_STRICT = False  ← THE KEY FIX
#   By default, CompressedManifestStaticFilesStorage raises ValueError when any
#   file referenced inside a CSS or JS file is not found in the manifest.
#   Django admin's CSS references font files (.woff2 etc.) that are sometimes
#   absent from the manifest after collectstatic runs on certain platforms.
#   Setting this to False makes WhiteNoise skip missing files instead of crashing,
#   which eliminates the 500 on every admin page click.

STATIC_URL  = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Django 5 / whitenoise 6 correct way — replaces deprecated STATICFILES_STORAGE
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

# Do NOT raise ValueError for manifest misses (admin fonts, etc.)
WHITENOISE_MANIFEST_STRICT = False

# ── Email — 2FA verification codes via Resend ─────────────────────────────────
# Uses django-anymail to route through Resend's transactional API.
#
# Required Render environment variable:
#   RESEND_API_KEY     — from Resend dashboard → API Keys → Create API Key
#
# DEFAULT_FROM_EMAIL must match a domain you have verified in Resend.
# Set it as a Render env var, e.g.: Mind Companion <noreply@yourdomain.com>
# If you haven't verified a custom domain yet, Resend allows sending from
# onboarding@resend.dev for testing only — set up a real domain for production.

EMAIL_BACKEND = 'anymail.backends.resend.EmailBackend'

ANYMAIL = {
    'RESEND_API_KEY': os.environ.get('RESEND_API_KEY', ''),
}

DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@mindcompanion.app')

# ── API keys ──────────────────────────────────────────────────────────────────
YOUTUBE_API_KEY   = os.environ.get('YOUTUBE_API_KEY', '')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── Logging ───────────────────────────────────────────────────────────────────
#
# When DEBUG=False Django normally swallows 500 tracebacks and just sends an
# email to ADMINS (which we haven't configured). This config forces the full
# Python traceback of every 500 error to print to stdout/stderr, which Render
# captures and shows in the Logs tab — making production errors debuggable.
#
# How to read the logs on Render:
#   Dashboard → your web service → Logs tab → filter by "ERROR" or "CRITICAL"

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,  # keep Django's default loggers active

    'formatters': {
        'verbose': {
            # Each log line: timestamp  level  logger_name  message
            'format': '{asctime} {levelname} {name} {message}',
            'style':  '{',
        },
    },

    'handlers': {
        # StreamHandler with no filename → writes to stdout → Render captures it
        'console': {
            'class':     'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },

    'loggers': {
        # Root logger: catches everything not handled by a more specific logger
        '': {
            'handlers': ['console'],
            'level':    'WARNING',   # WARNING and above go to Render logs
        },

        # Django's own request logger emits the 500 traceback here
        'django.request': {
            'handlers':  ['console'],
            'level':     'ERROR',    # logs every 5xx with full traceback
            'propagate': False,      # don't double-log via root logger
        },

        # Catches unhandled exceptions in views, signals, management commands
        'django': {
            'handlers':  ['console'],
            'level':     'ERROR',
            'propagate': False,
        },

        # Your app's own logger — use logger = logging.getLogger(__name__) in views
        'wellness': {
            'handlers':  ['console'],
            'level':     'DEBUG',    # show DEBUG+ from your own code
            'propagate': False,
        },
    },
}
