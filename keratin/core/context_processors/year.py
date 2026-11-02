from django.utils import timezone as tz


def year(request):
    """Добавляет переменную с текущим годом для отображения в footer."""
    return {"year": tz.now().year}
