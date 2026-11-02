import re

import pytest
from django.core.management import call_command
from django.urls import reverse

from core.middleware import editor_importmap_source
from core.richtext import NBSP
from studio.models import (
    Article,
    HomePage,
    PortfolioPhoto,
    PortfolioVideo,
    PriceCategory,
    PriceItem,
    Question,
    Review,
    Service,
    SiteSettings,
)


def test_service_page_shows_content(client, service):
    html = client.get(service.get_absolute_url()).content.decode()

    assert "Кератиновое выпрямление" in html
    assert "Первая строка<br>вторая строка" in html
    assert "rich-text--checks" in html
    assert f"Гладкие и{NBSP}ровные волосы." in html


def test_unpublished_service_is_hidden(client, service):
    service.is_published = False
    service.save()

    assert client.get(service.get_absolute_url()).status_code == 404
    assert (
        service.get_absolute_url()
        not in client.get("/price/").content.decode()
    )


def test_index_lists_published_services(client, service):
    service.price_from = 2500
    service.save()

    html = client.get(reverse("studio:index")).content.decode()

    assert f'href="{service.get_absolute_url()}"' in html
    assert service.teaser.replace(" ", NBSP, 1) in html
    assert f"от 2{NBSP}500{NBSP}₽" in html


def test_service_without_text_has_no_page(client, service):
    service.body = ""
    service.save()

    html = client.get(reverse("studio:index")).content.decode()
    sitemap = client.get(reverse("studio:sitemap")).content.decode()

    assert client.get(service.get_absolute_url()).status_code == 404
    assert f'href="{service.get_absolute_url()}"' not in html
    assert 'href="#prices">Подробнее' in html
    assert service.get_absolute_url() not in sitemap


def test_service_page_offers_booking(client, service):
    service.price_from = 2500
    service.save()

    html = client.get(service.get_absolute_url()).content.decode()

    assert f"от 2{NBSP}500{NBSP}₽" in html
    assert 'href="/price/">Все цены' in html


def test_article_page_shows_sections(client, article):
    html = client.get(article.get_absolute_url()).content.decode()

    assert f"правильно,<br>и{NBSP}они" in html
    assert "Используйте термозащиту." in html


def test_article_list_links_to_articles(client, article):
    html = client.get(reverse("studio:articles")).content.decode()

    assert f'href="{article.get_absolute_url()}"' in html


def test_price_page_formats_prices(client, price):
    html = client.get(reverse("studio:price")).content.decode()

    assert f"2{NBSP}500{NBSP}₽" in html
    assert f"от&nbsp;6{NBSP}500{NBSP}₽" in html
    assert "Адаптивная нанопластика" in html


def test_price_page_hides_empty_and_unpublished_categories(client, price):
    PriceCategory.objects.create(title="Пустой раздел")
    hidden = PriceCategory.objects.create(title="Скрытый", is_published=False)
    PriceItem.objects.create(category=hidden, name="позиция", price=100)

    html = client.get(reverse("studio:price")).content.decode()

    assert "Пустой раздел" not in html
    assert "Скрытый" not in html


@pytest.mark.parametrize(
    ("old_url", "new_url"),
    [
        ("/keratin_procedure/", "/services/keratin/"),
        ("/botox_procedure/", "/services/botox/"),
        ("/nano_plastic_procedure/", "/services/nanoplastic/"),
        ("/care_tips/", "/articles/"),
    ],
)
def test_old_urls_redirect_permanently(client, old_url, new_url):
    response = client.get(old_url)

    assert response.status_code == 301
    assert response["Location"] == new_url


@pytest.mark.django_db
def test_initial_content_is_loaded_once(capsys):
    call_command("load_initial_content")
    call_command("load_initial_content")

    assert Service.objects.count() == 4
    assert Service.objects.with_page().count() == 3
    assert Service.objects.get(slug="restoration").price_from == 850
    assert HomePage.objects.count() == 1
    assert Question.objects.published().count() == 5
    assert not Review.objects.get().is_published
    assert Article.objects.get().sections.count() == 2
    assert PriceItem.objects.filter(price=2500).exists()
    service = Service.objects.get(slug="botox")
    assert service.image.name.endswith(".webp")
    assert PortfolioPhoto.objects.filter(service=service).count() == 1
    assert PortfolioVideo.objects.filter(status="pending").count() == 4
    assert SiteSettings.objects.get().phone == "+79297232435"
    assert "ничего не изменено" in capsys.readouterr().out


ADMIN_PAGES = [
    "admin:studio_service_changelist",
    "admin:studio_service_add",
    "admin:studio_article_add",
    "admin:studio_pricecategory_add",
    "admin:studio_homepage_add",
    "admin:studio_review_add",
    "admin:studio_question_add",
]


@pytest.mark.parametrize("url_name", ADMIN_PAGES)
def test_admin_pages_open(admin_client, url_name):
    assert admin_client.get(reverse(url_name)).status_code == 200


def test_admin_allows_only_editor_importmap(admin_client):
    response = admin_client.get(reverse("admin:studio_service_add"))
    html = response.content.decode()

    block = re.search(r'<script type="importmap">(.*?)</script>', html, re.S)
    policy = response["Content-Security-Policy"]
    script_src = re.search(r"script-src ([^;]*)", policy).group(1).split()
    assert block
    assert script_src == ["'self'", editor_importmap_source()]


def test_site_pages_do_not_allow_importmap(client, service):
    policy = client.get(service.get_absolute_url())["Content-Security-Policy"]

    assert "sha256" not in policy
