from django.conf import settings
from django.core.checks import Tags, Warning, register


def client_ip(request):
    """Адрес клиента для блокировки перебора паролей.

    За nginx настоящий адрес приходит в заголовке X-Real-IP, nginx всегда
    перезаписывает его сам. Без прокси заголовок может прислать кто угодно,
    поэтому ему доверяют только при включённой настройке USE_X_REAL_IP.
    """
    if settings.USE_X_REAL_IP:
        real_ip = request.META.get("HTTP_X_REAL_IP", "").strip()
        if real_ip:
            return real_ip
    return request.META.get("REMOTE_ADDR")


@register(Tags.security, deploy=True)
def check_admin_protection(app_configs, **kwargs):
    warnings = []
    if settings.ADMIN_URL.strip("/") == "admin":
        warnings.append(
            Warning(
                "Админка доступна по стандартному адресу /admin/.",
                hint="Задайте неочевидный адрес в переменной ADMIN_URL.",
                id="core.W001",
            )
        )
    return warnings
