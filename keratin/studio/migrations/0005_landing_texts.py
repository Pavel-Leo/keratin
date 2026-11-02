"""Тексты и цены карточек процедур для уже заполненной базы.

Анонс меняется, только если в нём остался текст первой версии сайта,
цена ставится, только если её ещё нет.
"""

from django.db import migrations

CARDS = {
    "keratin": (
        "5 причин сделать кератиновое выпрямление и вычеркнуть проблемы "
        "с волосами из своей жизни.",
        "Гладкие ровные волосы без пуха даже в дождь и снег, укладка "
        "за 5 минут.",
        2500,
    ),
    "botox": (
        "Сухость, сечение, ломкость и спутанность волос. Знакомо? Пора "
        "принимать меры! Со всеми перечисленными проблемами поможет "
        "справиться ботокс.",
        "Восстанавливает сухие, ломкие и секущиеся волосы, возвращает "
        "блеск. Разглаживает, но не выпрямляет.",
        2500,
    ),
    "nanoplastic": (
        "Что такое нанопластика волос, когда её следует применять и в чём "
        "её ключевые отличия от других подобных процедур для выпрямления "
        "волос. Разберём подробнее...",
        "Щадящий состав, эффект от 6 до 12 месяцев, можно завивать "
        "и делать причёски.",
        4000,
    ),
}


def update_cards(apps, schema_editor):
    service_model = apps.get_model("studio", "Service")
    for slug, (old_teaser, teaser, price) in CARDS.items():
        service = service_model.objects.filter(slug=slug).first()
        if service is None:
            continue
        if service.teaser == old_teaser:
            service.teaser = teaser
        if service.price_from is None:
            service.price_from = price
        service.save(update_fields=["teaser", "price_from"])


class Migration(migrations.Migration):
    dependencies = [
        ("studio", "0004_landing"),
    ]

    operations = [
        migrations.RunPython(update_cards, migrations.RunPython.noop),
    ]
