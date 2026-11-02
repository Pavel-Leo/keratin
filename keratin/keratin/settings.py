"""Настройки проекта. Все значения для окружения берутся из переменных."""

import os
from pathlib import Path
from urllib.parse import urlsplit

from csp.constants import NONE, SELF, UNSAFE_INLINE
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def env(name, default=None):
    return os.environ.get(name, default)


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name, default):
    value = os.environ.get(name)
    return default if value is None else int(value)


def env_list(name, default=""):
    raw = os.environ.get(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


DEBUG = env_bool("DEBUG")

SECRET_KEY = env("SECRET_KEY", "")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured("SECRET_KEY must be set when DEBUG is off")
    SECRET_KEY = "insecure-key-for-local-development-only"  # noqa: S105

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "core.apps.StudioAdminConfig",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    "core.apps.AxesConfig",
    "csp",
    "django_prose_editor",
    "studio.apps.StudioConfig",
    "core.apps.CoreConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.gzip.GZipMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "csp.middleware.CSPMiddleware",
    "core.middleware.AdminEditorCSPMiddleware",
    "axes.middleware.AxesMiddleware",
]

ROOT_URLCONF = "keratin.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.year.year",
                "core.context_processors.booking.booking",
                "studio.context_processors.menu",
                "studio.context_processors.contacts",
            ],
        },
    },
]

WSGI_APPLICATION = "keratin.wsgi.application"

if env("POSTGRES_DB"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("POSTGRES_DB"),
            "USER": env("POSTGRES_USER"),
            "PASSWORD": env("POSTGRES_PASSWORD"),
            "HOST": env("POSTGRES_HOST", "db"),
            "PORT": env("POSTGRES_PORT", "5432"),
            "CONN_MAX_AGE": 60,
            "CONN_HEALTH_CHECKS": True,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation.MinimumLengthValidator"
        ),
        "OPTIONS": {"min_length": 12},
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation.CommonPasswordValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation.NumericPasswordValidator"
        ),
    },
]

LANGUAGE_CODE = "ru-ru"
TIME_ZONE = "Europe/Moscow"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = Path(env("STATIC_ROOT", BASE_DIR / "staticfiles"))
STATICFILES_DIRS = [BASE_DIR / "static"]
# Файлы, которые браузеры и поисковики ищут в корне сайта.
WHITENOISE_ROOT = BASE_DIR / "public"

MEDIA_URL = "/media/"
MEDIA_ROOT = Path(env("MEDIA_ROOT", BASE_DIR / "media"))
# Исходники роликов до перекодирования. Каталог не раздаётся по ссылке.
PRIVATE_MEDIA_ROOT = Path(
    env("PRIVATE_MEDIA_ROOT", BASE_DIR / "private_media")
)
# Куда Django складывает большие загрузки, пока запрос не обработан.
FILE_UPLOAD_TEMP_DIR = env("FILE_UPLOAD_TEMP_DIR") or None

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "private": {
        "BACKEND": "core.storage.PrivateStorage",
        "OPTIONS": {"location": PRIVATE_MEDIA_ROOT},
    },
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        ),
    },
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# За nginx: он завершает HTTPS и передаёт исходную схему в заголовке.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", not DEBUG)
SECURE_REDIRECT_EXEMPT = [r"^healthz/$"]
SECURE_HSTS_SECONDS = env_int("SECURE_HSTS_SECONDS", 0 if DEBUG else 31536000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool(
    "SECURE_HSTS_INCLUDE_SUBDOMAINS", True
)
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_AGE = 60 * 60 * 12
X_FRAME_OPTIONS = "DENY"

# Включение HSTS preload необратимо на месяцы, решение за владельцем домена.
SILENCED_SYSTEM_CHECKS = ["security.W021"]

# Админка: неочевидный адрес и блокировка перебора паролей.
ADMIN_URL = env("ADMIN_URL", "admin/").strip("/") + "/"
if ADMIN_URL == "/":
    raise ImproperlyConfigured("ADMIN_URL must not be empty")

# Адрес клиента берётся из X-Real-IP, только если перед сайтом стоит nginx.
USE_X_REAL_IP = env_bool("USE_X_REAL_IP")
AXES_CLIENT_IP_CALLABLE = "core.security.client_ip"
AXES_FAILURE_LIMIT = env_int("AXES_FAILURE_LIMIT", 5)
AXES_COOLOFF_TIME = env_int("AXES_COOLOFF_HOURS", 1)
AXES_LOCKOUT_PARAMETERS = ["ip_address"]
AXES_RESET_ON_SUCCESS = True
AXES_LOCKOUT_TEMPLATE = "core/lockout.html"

# Онлайн-запись BookNow (старая страница студии на EasyWeek
# заблокирована и сама отсылает сюда) открывается во фрейме,
# их скрипт не подключается.
BOOKING_URL = env(
    "BOOKING_URL",
    "https://booking.booknow.ru/keratin-studio-by-diana-bocharova",
)
_booking = urlsplit(BOOKING_URL)
BOOKING_ORIGIN = f"{_booking.scheme}://{_booking.netloc}"

# Ролики портфолио: загрузка в админке, перекодирование отдельным процессом.
FFMPEG_BINARY = env("FFMPEG_BINARY", "ffmpeg")
FFPROBE_BINARY = env("FFPROBE_BINARY", "ffprobe")
VIDEO_MAX_UPLOAD_MB = env_int("VIDEO_MAX_UPLOAD_MB", 500)
VIDEO_MAX_SECONDS = env_int("VIDEO_MAX_SECONDS", 180)
VIDEO_TIMEOUT_SECONDS = env_int("VIDEO_TIMEOUT_SECONDS", 30 * 60)

# Встроенные стили нужны галерее: при открытии видео она добавляет <style>.
# Скрипты только с собственного домена.
CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": [SELF],
        "script-src": [SELF],
        "style-src": [SELF, UNSAFE_INLINE],
        "font-src": [SELF],
        "img-src": [SELF, "data:"],
        "media-src": [SELF],
        "connect-src": [SELF],
        "frame-src": [BOOKING_ORIGIN],
        "object-src": [NONE],
        "base-uri": [SELF],
        "form-action": [SELF],
        "frame-ancestors": [NONE],
    },
}
if not DEBUG:
    CONTENT_SECURITY_POLICY["DIRECTIVES"]["upgrade-insecure-requests"] = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", "INFO")},
}
