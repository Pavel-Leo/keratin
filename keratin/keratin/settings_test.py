"""Настройки для тестов: без внешних зависимостей и сборки статики."""

import os
import tempfile

os.environ.setdefault("SECRET_KEY", "test-secret-key")

from keratin.settings import *  # noqa: E402,F403
from keratin.settings import STORAGES  # noqa: E402

DEBUG = False
SECURE_SSL_REDIRECT = False
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
MEDIA_ROOT = tempfile.mkdtemp(prefix="keratin-test-media-")
PRIVATE_MEDIA_ROOT = tempfile.mkdtemp(prefix="keratin-test-private-")
STATIC_ROOT = tempfile.mkdtemp(prefix="keratin-test-static-")
STORAGES = {
    **STORAGES,
    "private": {
        "BACKEND": "core.storage.PrivateStorage",
        "OPTIONS": {"location": PRIVATE_MEDIA_ROOT},
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}
