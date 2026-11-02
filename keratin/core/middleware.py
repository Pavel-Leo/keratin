import base64
import hashlib
import re
from functools import cache

from django.conf import settings
from django_prose_editor.widgets import importmap

IMPORTMAP_BODY = re.compile(r"<script[^>]*>(.*)</script>", re.DOTALL)


@cache
def editor_importmap_source():
    """CSP-источник с хешем карты импортов визуального редактора."""
    body = IMPORTMAP_BODY.search(str(importmap.render())).group(1)
    digest = hashlib.sha256(body.encode()).digest()
    return f"'sha256-{base64.b64encode(digest).decode()}'"


class AdminEditorCSPMiddleware:
    """Разрешает в админке карту импортов визуального редактора.

    Редактор подключает свои модули через встроенный
    <script type="importmap">, а политика CSP запрещает встроенные
    скрипты. Разрешается только этот блок, по хешу его содержимого.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.prefix = f"/{settings.ADMIN_URL}"

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith(self.prefix):
            response._csp_update = {"script-src": [editor_importmap_source()]}
        return response
