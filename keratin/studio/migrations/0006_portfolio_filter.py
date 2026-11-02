"""Общий фильтр фото и видео по процедурам."""

import django.db.models.deletion
from django.db import migrations, models


def update_initial_content(apps, schema_editor):
    """Связывает начальные ролики с услугами и уточняет срок эффекта."""
    service_model = apps.get_model("studio", "Service")
    video_model = apps.get_model("studio", "PortfolioVideo")
    home_model = apps.get_model("studio", "HomePage")
    titles = {
        "nanoplastic": ["Нанопластика"],
        "keratin": [
            "Кератиновое выпрямление на тёмных волосах",
            "Кератиновое выпрямление на блонд",
            "Кератиновое выпрямление на светлых волосах",
        ],
    }
    for slug, names in titles.items():
        service = service_model.objects.filter(slug=slug).first()
        if service:
            video_model.objects.filter(
                title__in=names, service__isnull=True
            ).update(service=service)
    old_trust = (
        "Сертифицированный мастер: кератин, ботокс, нанопластика\n"
        "Опыт более 2 лет\nТолько безопасные составы\n"
        "Эффект до 12 месяцев"
    )
    home_model.objects.filter(trust=old_trust).update(
        trust=old_trust.replace(
            "Эффект до 12 месяцев", "Нанопластика: эффект до 12 месяцев"
        )
    )


class Migration(migrations.Migration):
    dependencies = [
        ('studio', '0005_landing_texts'),
    ]

    operations = [
        migrations.AddField(
            model_name='portfoliovideo',
            name='service',
            field=models.ForeignKey(
                blank=True,
                help_text="По услугам работает фильтр в портфолио.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="videos",
                to="studio.service",
                verbose_name="Услуга",
            ),
        ),
        migrations.AlterField(
            model_name='homepage',
            name='trust',
            field=models.TextField(
                blank=True,
                default=(
                    "Сертифицированный мастер: кератин, ботокс, "
                    "нанопластика\nОпыт более 2 лет\n"
                    "Только безопасные составы\n"
                    "Нанопластика: эффект до 12 месяцев"
                ),
                help_text="Каждый пункт с новой строки. "
                "Лучше всего смотрятся 4 пункта.",
                verbose_name="Преимущества",
            ),
        ),
        migrations.RunPython(
            update_initial_content, migrations.RunPython.noop
        ),
    ]
