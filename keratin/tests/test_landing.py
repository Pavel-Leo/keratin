import importlib

import pytest
from django.apps import apps
from django.urls import reverse

from core.richtext import NBSP
from studio.models import HomePage, Question, Review, Service, SiteSettings

landing_texts = importlib.import_module("studio.migrations.0005_landing_texts")


def get_index(client):
    return client.get(reverse("studio:index")).content.decode()


@pytest.mark.django_db
def test_index_shows_default_texts_before_editing(client):
    html = get_index(client)

    assert not HomePage.objects.exists()
    assert "<title>Кератиновое выпрямление волос в Казани |" in html
    assert f"от 2{NBSP}500{NBSP}₽" in html
    assert "−15% на первое посещение" in html
    assert f"Опыт более 2{NBSP}лет" in html
    assert "Какая процедура вам подходит?" in html


@pytest.mark.django_db
def test_index_shows_texts_from_admin(client):
    HomePage.objects.create(
        hero_title="Новый заголовок",
        price_from=None,
        promo="",
        trust="Первый пункт\n\nВторой пункт",
        problems="",
    )

    html = get_index(client)

    assert '<h1 class="hero__title">Новый заголовок</h1>' in html
    assert "hero__price" not in html
    assert "promo-badge" not in html
    assert html.count('class="trust__item"') == 2
    assert "check-list" not in html


def test_only_published_reviews_are_shown(client, service):
    Review.objects.create(author="Анна", text="Всё отлично", service=service)
    Review.objects.create(author="ПРИМЕР", text="Пример", is_published=False)

    html = get_index(client)

    assert 'id="reviews"' in html
    assert "Анна<span>Кератин</span>" in html
    assert "ПРИМЕР" not in html


@pytest.mark.django_db
def test_reviews_block_is_hidden_without_published_reviews(client):
    Review.objects.create(author="ПРИМЕР", text="Пример", is_published=False)

    assert 'id="reviews"' not in get_index(client)


@pytest.mark.django_db
def test_faq_shows_published_questions(client):
    Question.objects.create(
        question="Сколько держится?",
        answer="<p>До года.</p><script>alert(1)</script>",
    )
    Question.objects.create(
        question="Скрытый вопрос", answer="<p>Нет.</p>", is_published=False
    )

    html = get_index(client)

    assert 'href="#faq"' in html
    assert "Сколько держится?" in html
    assert f"<p>До{NBSP}года.</p>" in html
    assert "alert(1)" not in html
    assert "Скрытый вопрос" not in html


@pytest.mark.django_db
def test_contacts_offer_route_call_and_telegram(client):
    contacts = SiteSettings.objects.create(
        city="Казань",
        street="Ю. Фучика, 90а",
        phone="+79297232435",
        telegram_url="https://t.me/studio",
    )

    html = get_index(client)

    assert contacts.map_url.startswith("https://yandex.ru/maps/?text=")
    assert f'href="{contacts.map_url}"' in html
    assert 'class="mobile-bar__call" href="tel:+79297232435"' in html
    assert "Получить консультацию в&nbsp;Telegram" in html


@pytest.mark.django_db
def test_mobile_bar_has_no_call_without_phone(client):
    html = get_index(client)

    assert 'class="mobile-bar__book"' in html
    assert "mobile-bar__call" not in html


@pytest.mark.django_db
def test_migration_updates_only_untouched_cards():
    old_teaser, new_teaser, price = landing_texts.CARDS["keratin"]
    keratin = Service.objects.create(
        title="Кератин",
        menu_title="Кератин",
        slug="keratin",
        teaser=old_teaser,
    )
    botox = Service.objects.create(
        title="Ботокс",
        menu_title="Ботокс",
        slug="botox",
        teaser="Свой текст",
        price_from=3000,
    )

    landing_texts.update_cards(apps, None)

    keratin.refresh_from_db()
    botox.refresh_from_db()
    assert (keratin.teaser, keratin.price_from) == (new_teaser, price)
    assert (botox.teaser, botox.price_from) == ("Свой текст", 3000)


def test_home_page_admin_opens_the_only_record(admin_client):
    home = HomePage.objects.create()
    change_url = reverse("admin:studio_homepage_change", args=[home.pk])

    response = admin_client.get(reverse("admin:studio_homepage_changelist"))

    assert response.status_code == 302
    assert response["Location"] == change_url
    assert admin_client.get(change_url).status_code == 200
    add_url = reverse("admin:studio_homepage_add")
    assert admin_client.get(add_url).status_code == 403
