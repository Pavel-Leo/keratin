from django.utils.functional import SimpleLazyObject

from .models import Service, SiteSettings


def menu(request):
    """Услуги для верхнего меню. Запрос выполняется лениво."""
    return {
        "menu_services": Service.objects.with_page().only("menu_title", "slug")
    }


def contacts(request):
    """Контакты студии для подвала, заголовков и разметки для поисковиков."""
    return {"contacts": SimpleLazyObject(SiteSettings.load)}
