from axes.apps import AppConfig as BaseAxesConfig
from django.apps import AppConfig
from django.contrib.admin.apps import AdminConfig


class CoreConfig(AppConfig):
    name = "core"

    def ready(self):
        from . import security  # noqa: F401  регистрация проверок


class StudioAdminConfig(AdminConfig):
    default_site = "core.admin_site.StudioAdminSite"


# Русские названия разделов сторонних приложений в админке.
class AxesConfig(BaseAxesConfig):
    verbose_name = "Блокировки входа"
