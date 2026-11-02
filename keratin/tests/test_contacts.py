import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from core.richtext import NBSP, WORD_JOINER
from core.templatetags.text import phone
from studio.models import SiteSettings


@pytest.fixture
def contacts(db):
    return SiteSettings.objects.create(
        name="Keratin studio",
        place="ТЦ «Франт»",
        street="Ю. Фучика, 90а",
        city="Казань",
        phone="+79297232435",
        email="studio@example.com",
        hours="Пн–пт: 10:00–21:00\n\nСб–вс: 11:00–20:00",
        vk_url="https://vk.com/studio",
    )


def test_contacts_are_shown_on_every_page(client, contacts, service):
    html = client.get(service.get_absolute_url()).content.decode()

    assert "<title>Кератиновое выпрямление | Keratin studio</title>" in html
    assert "ТЦ «Франт»<br>Ю. Фучика, 90а, г. Казань" in html
    assert 'href="tel:+79297232435"' in html
    assert f"8{NBSP}(929){NBSP}723-24-35" in html
    assert f"10:00–{WORD_JOINER}21:00<br>Сб–вс" in html
    assert 'href="https://vk.com/studio"' in html
    assert "instagram" not in html


def test_pages_work_before_contacts_are_filled(client, db):
    html = client.get(reverse("studio:index")).content.decode()

    assert "Keratin studio by Diana Bocharova</title>" in html
    assert "tel:" not in html
    assert "social-link" not in html


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("+79297232435", f"8{NBSP}(929){NBSP}723-24-35"),
        ("", ""),
        ("12345", "12345"),
    ],
)
def test_phone_is_formatted_for_people(value, expected):
    assert phone(value) == expected


def test_phone_must_be_in_international_format(contacts):
    contacts.phone = "8 929 723-24-35"

    with pytest.raises(ValidationError) as error:
        contacts.full_clean()

    assert "phone" in error.value.message_dict


def test_admin_opens_the_only_record(admin_client, contacts):
    url = reverse("admin:studio_sitesettings_changelist")
    response = admin_client.get(url)

    assert response.status_code == 302
    assert response["Location"] == reverse(
        "admin:studio_sitesettings_change", args=[contacts.pk]
    )
    add = admin_client.get(reverse("admin:studio_sitesettings_add"))
    assert add.status_code == 403
    change = admin_client.get(response["Location"])
    assert change.status_code == 200
    assert "Удалить" not in change.content.decode()


def test_admin_offers_to_create_missing_contacts(admin_client, db):
    response = admin_client.get(
        reverse("admin:studio_sitesettings_changelist")
    )

    assert response["Location"] == reverse("admin:studio_sitesettings_add")
    assert admin_client.get(response["Location"]).status_code == 200
