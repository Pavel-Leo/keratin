import pytest
from django.urls import reverse
from django.utils import timezone

PAGES = [
    ("/", "studio/index.html"),
    ("/services/keratin/", "studio/service_detail.html"),
    ("/articles/care-tips/", "studio/article_detail.html"),
    ("/price/", "studio/price.html"),
]


@pytest.mark.parametrize(("url", "template"), PAGES)
def test_page_renders_with_base_layout(client, content, url, template):
    response = client.get(url)

    assert response.status_code == 200
    templates = [t.name for t in response.templates]
    assert template in templates
    assert "base.html" in templates
    assert "studio/includes/nav.html" in templates


@pytest.mark.parametrize(
    ("url", "active_url"),
    [
        ("/services/keratin/", "/services/keratin/"),
        ("/articles/care-tips/", "/articles/care-tips/"),
        ("/price/", "/price/"),
    ],
)
def test_inner_page_marks_current_menu_item(client, content, url, active_url):
    response = client.get(url)

    assert f'href="{active_url}" class="active"' in response.content.decode()


@pytest.mark.django_db
def test_index_menu_uses_anchors(client, service):
    content = client.get(reverse("studio:index")).content.decode()

    assert 'href="#services"' in content
    assert 'href="#contact"' in content
    assert 'class="active"' not in content


def test_index_header_links_to_service_and_care(client, service):
    html = client.get(reverse("studio:index")).content.decode()
    nav = html.split("<nav ", 1)[1].split("</nav>", 1)[0]

    assert '<details class="nav-dropdown">' in nav
    assert f'href="{service.get_absolute_url()}"' in nav
    assert 'href="/articles/care-tips/"' in nav
    assert 'href="/articles/"' not in nav


@pytest.mark.django_db
def test_unknown_page_returns_custom_404(client):
    response = client.get("/no-such-page/")

    assert response.status_code == 404
    assert "core/404.html" in [t.name for t in response.templates]
    assert reverse("studio:index") in response.content.decode()


def test_healthz_answers_without_database(client):
    response = client.get(reverse("healthz"))

    assert response.status_code == 200
    assert response.content == b"ok"


@pytest.mark.django_db
def test_footer_shows_current_year(client):
    content = client.get(reverse("studio:index")).content.decode()

    assert f"© {timezone.now().year}" in content
