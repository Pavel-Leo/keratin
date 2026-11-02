"""Очистка, нормализация и типографика текстов из визуального редактора.

Разрешённая разметка задаётся набором расширений редактора: что можно
сделать кнопками редактора, то и пропускает очистка на сервере.
"""

import re
from functools import cache

from django_prose_editor.fields import create_sanitizer

NBSP = " "
WORD_JOINER = "\u2060"

RICH_TEXT_EXTENSIONS = {
    "Bold": True,
    "Italic": True,
    "Link": {
        "enableTarget": False,
        "protocols": ["http", "https", "mailto", "tel"],
    },
    "Heading": {"levels": [3]},
    "BulletList": True,
    "OrderedList": True,
    "ListItem": True,
    "Blockquote": True,
    "HardBreak": True,
}

BLOCK_TAGS = "p|h3|li|blockquote"
BR = r"<br\s*/?>"
SPACE = rf"(?:\s|{NBSP})"

EMPTY_BLOCK = re.compile(
    rf"<(?P<tag>p|h3)>(?:{SPACE}|{BR})*</(?P=tag)>", re.IGNORECASE
)
BREAKS_AT_START = re.compile(
    rf"(<(?:{BLOCK_TAGS})>)(?:{SPACE}|{BR})+", re.IGNORECASE
)
BREAKS_AT_END = re.compile(
    rf"(?:{SPACE}|{BR})+(</(?:{BLOCK_TAGS})>)", re.IGNORECASE
)
REPEATED_BREAKS = re.compile(rf"{SPACE}*(?:{BR}{SPACE}*)+", re.IGNORECASE)
SPACES_WITH_NBSP = re.compile(rf"[ \t]*{NBSP}[ \t{NBSP}]*")
REPEATED_SPACES = re.compile(r"[ \t]{2,}")

# Предлоги, союзы и частицы, после которых нельзя переносить строку.
SHORT_WORDS = (
    "а|б|в|и|к|о|с|у|я|бы|во|да|до|же|за|из|ко|ли|на|не|ни|но|об|от|по|"
    "со|то|без|для|или|как|над|под|при|про|что"
)
AFTER_SHORT_WORD = re.compile(
    rf"(?<![^\s{NBSP}(«„\"'])({SHORT_WORDS})[ \t\r\n]+(?=\S)",
    re.IGNORECASE,
)
BEFORE_PARTICLE = re.compile(
    r"(?<=[^\W\d_])[ \t\r\n]+(?=(?:же|ли|бы|ль)(?![^\W\d_]))", re.IGNORECASE
)
BEFORE_DASH = re.compile(r"[ \t\r\n]+(?=[—–](?:\s|$))")
NUMBER_AND_UNIT = re.compile(r"(?<=\d)[ \t\r\n]+(?=[^\W\d_]|%|₽)")
# Диапазон чисел или времени («6–12», «10:00–21:00») не рвётся после тире.
NUMBER_RANGE = re.compile(r"(?<=\d)([–—])(?=\d)")
TAG = re.compile(r"(<[^>]*>)")


@cache
def _sanitizer():
    return create_sanitizer(RICH_TEXT_EXTENSIONS)


def sanitize(html):
    """Оставляет только разметку, которую умеет создавать редактор."""
    return _sanitizer()(html or "")


def normalize(html):
    """Убирает пустые абзацы, лишние переносы и пробелы по краям блоков."""
    html = (html or "").replace("&nbsp;", NBSP)
    html = SPACES_WITH_NBSP.sub(NBSP, html)
    html = REPEATED_SPACES.sub(" ", html)
    html = REPEATED_BREAKS.sub("<br>", html)
    html = BREAKS_AT_START.sub(r"\1", html)
    html = BREAKS_AT_END.sub(r"\1", html)
    html = EMPTY_BLOCK.sub("", html)
    return html.strip()


def clean_rich_text(html):
    return normalize(sanitize(html))


def typograph_text(text):
    """Неразрывные пробелы и связанные диапазоны в тексте без разметки."""
    text = AFTER_SHORT_WORD.sub(rf"\1{NBSP}", text)
    text = BEFORE_PARTICLE.sub(NBSP, text)
    text = BEFORE_DASH.sub(NBSP, text)
    text = NUMBER_RANGE.sub(rf"\1{WORD_JOINER}", text)
    return NUMBER_AND_UNIT.sub(NBSP, text)


def typograph(html):
    """Неразрывные пробелы в HTML: меняется только текст между тегами."""
    parts = TAG.split(html or "")
    return "".join(
        part if part.startswith("<") else typograph_text(part)
        for part in parts
    )
