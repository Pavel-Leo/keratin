from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

from core.richtext import NBSP, clean_rich_text, typograph, typograph_text

register = template.Library()


@register.filter
def rich(value):
    """Текст из визуального редактора, готовый к выводу.

    Очистка повторяется при выводе, чтобы на страницу не попала разметка,
    записанная в базу в обход формы админки.
    """
    return mark_safe(typograph(clean_rich_text(value)))  # noqa: S308


@register.filter
def plain(value):
    """Обычный текст: переносы строк из админки становятся <br>.

    Пустые строки пропускаются, поэтому двойной Enter не даёт пустого места.
    """
    lines = (line.strip() for line in str(escape(value or "")).splitlines())
    text = "<br>".join(typograph_text(line) for line in lines if line)
    return mark_safe(text)  # noqa: S308


@register.filter
def rub(value):
    """Цена в рублях с разбиением на разряды: 2500 -> «2 500 ₽»."""
    return f"{int(value):,}".replace(",", NBSP) + f"{NBSP}₽"


@register.filter
def phone(value):
    """Номер для показа: +79297232435 -> «8 (929) 723-24-35»."""
    digits = str(value or "")[-10:]
    if len(digits) != 10 or not digits.isdigit():
        return value
    return (
        f"8{NBSP}({digits[:3]}){NBSP}{digits[3:6]}-{digits[6:8]}-{digits[8:]}"
    )
