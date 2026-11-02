import pytest
from django.template import Context, Template

from core.richtext import NBSP, WORD_JOINER, clean_rich_text, typograph


def render(template, **context):
    return Template("{% load text %}" + template).render(Context(context))


@pytest.mark.parametrize(
    "html",
    [
        '<p onclick="steal()">текст</p>',
        "<p>текст<script>alert(1)</script></p>",
        '<p><a href="javascript:alert(1)">текст</a></p>',
        '<p><img src="x" onerror="alert(1)">текст</p>',
        '<p><span style="color:red">текст</span></p>',
    ],
)
def test_sanitizer_removes_dangerous_markup(html):
    cleaned = clean_rich_text(html)

    for marker in ("onclick", "script", "javascript", "img", "style"):
        assert marker not in cleaned
    assert "текст" in cleaned


def test_sanitizer_keeps_editor_markup():
    html = (
        "<h3>Заголовок</h3><p><strong>жирный</strong> и <em>курсив</em>"
        '<br>строка <a href="/services/keratin/">ссылка</a></p>'
        "<ul><li><p>пункт</p></li></ul><blockquote><p>цитата</p></blockquote>"
    )

    assert clean_rich_text(html) == html


@pytest.mark.parametrize(
    ("html", "expected"),
    [
        ("<p></p><p>текст</p><p><br></p>", "<p>текст</p>"),
        ("<p>раз<br><br><br>два</p>", "<p>раз<br>два</p>"),
        ("<p><br>текст<br></p>", "<p>текст</p>"),
        ("<p>&nbsp; текст &nbsp;</p>", "<p>текст</p>"),
        ("<p>раз   два</p>", "<p>раз два</p>"),
        ("<p> </p>", ""),
    ],
)
def test_normalizer_removes_extra_breaks_and_spaces(html, expected):
    assert clean_rich_text(html) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("в дождь и снег", f"в{NBSP}дождь и{NBSP}снег"),
        ("решение — ботокс", f"решение{NBSP}— ботокс"),
        ("5 минут и 50 %", f"5{NBSP}минут и{NBSP}50{NBSP}%"),
        ("цена 2500 ₽", f"цена 2500{NBSP}₽"),
        ("он же", f"он{NBSP}же"),
        ("10:00–21:00", f"10:00–{WORD_JOINER}21:00"),
    ],
)
def test_typograph_binds_short_words(text, expected):
    assert typograph(text) == expected


def test_typograph_does_not_touch_tags():
    html = '<a href="/в путь/" title="и в">в путь</a>'

    assert typograph(html) == f'<a href="/в путь/" title="и в">в{NBSP}путь</a>'


def test_plain_filter_turns_lines_into_breaks_and_escapes():
    result = render("{{ text|plain }}", text="Раз\n\n\nдва <b>\n")

    assert result == "Раз<br>два &lt;b&gt;"


def test_rich_filter_sanitizes_content_saved_past_the_form():
    result = render("{{ html|rich }}", html="<p>ок<script>x()</script></p>")

    assert result == "<p>ок</p>"


@pytest.mark.parametrize(
    ("value", "expected"),
    [(850, f"850{NBSP}₽"), (2500, f"2{NBSP}500{NBSP}₽")],
)
def test_rub_filter_groups_thousands(value, expected):
    assert render("{{ value|rub }}", value=value) == expected


@pytest.mark.django_db
def test_model_validation_cleans_rich_text(service):
    service.body = "<p></p><p>Текст<br><br></p><script>x()</script>"

    service.full_clean()

    assert service.body == "<p>Текст</p>"
