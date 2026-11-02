from django.conf import settings


def booking(request):
    """Адрес онлайн-записи для кнопок «Записаться» на всех страницах."""
    return {"booking_url": settings.BOOKING_URL}
