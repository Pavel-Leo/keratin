import json
import re

import pytest
from django.conf import settings
from django.urls import reverse

from studio.models import Article, SiteSettings

JSON_LD = re.compile(
    r'<script type="application/ld\+json">(.*?)</script>', re.DOTALL
)


@pytest.fixture
def contacts(db):
    return SiteSettings.objects.create(
        name="Keratin studio",
        place="ТЦ «Франт»",
        street="Ю. Фучика, 90а",
        city="Казань",
        phone="+79297232435",
        vk_url="https://vk.com/studio",
    )


def test_sitemap_lists_only_published_pages(client, content):
    Article.objects.create(
        title="Черновик", slug="draft", teaser="", is_published=False
    )

    xml = client.get(reverse("studio:sitemap")).content.decode()

    assert "http://testserver/</loc>" in xml
    assert "/price/</loc>" in xml
    assert "/services/keratin/</loc>" in xml
    assert "/articles/care-tips/</loc>" in xml
    assert "/articles/draft/" not in xml


def test_robots_points_to_sitemap_and_hides_admin(client, db):
    response = client.get(reverse("studio:robots"))
    text = response.content.decode()

    assert response["Content-Type"].startswith("text/plain")
    assert "Sitemap: http://testserver/sitemap.xml" in text
    assert settings.ADMIN_URL.strip("/") not in text


def test_favicon_is_served_from_site_root(client, db):
    response = client.get("/favicon.ico")

    assert response.status_code == 200
    assert response["Content-Type"] == "image/x-icon"


def test_service_page_has_link_preview(client, service):
    html = client.get(service.get_absolute_url()).content.decode()

    assert (
        '<link rel="canonical" href="http://testserver/services/keratin/">'
        in html
    )
    assert '<meta property="og:title" content="Кератиновое выпрямление">' in (
        html
    )
    assert "http://testserver/static/img/og-image.jpg" in html
    assert '<meta property="og:type" content="website">' in html


def test_article_is_marked_as_article(client, article):
    html = client.get(article.get_absolute_url()).content.decode()

    assert '<meta property="og:type" content="article">' in html


def test_index_describes_salon_for_search(client, contacts):
    html = client.get(reverse("studio:index")).content.decode()

    data = json.loads(JSON_LD.search(html).group(1))
    assert data["@type"] == "HairSalon"
    assert data["name"] == "Keratin studio"
    assert data["telephone"] == "+79297232435"
    assert data["address"] == {
        "@type": "PostalAddress",
        "addressCountry": "RU",
        "streetAddress": "Ю. Фучика, 90а, ТЦ «Франт»",
        "addressLocality": "Казань",
    }
    assert data["sameAs"] == ["https://vk.com/studio"]


def test_salon_data_cannot_close_script_tag(client, contacts):
    contacts.name = "</script><script>alert(1)</script>"
    contacts.save()

    html = client.get(reverse("studio:index")).content.decode()
    block = JSON_LD.search(html).group(1)

    assert "</script>" not in block
    assert json.loads(block)["name"] == contacts.name
