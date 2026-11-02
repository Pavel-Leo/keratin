import re

import pytest
from django.conf import settings
from django.test import RequestFactory, override_settings
from django.urls import reverse

from core.security import check_admin_protection, client_ip

# Данные для поисковиков (application/ld+json) не выполняются браузером.
INLINE_SCRIPT = re.compile(
    r'<script(?![^>]*\b(?:src=|type="application/ld\+json"))[^>]*>',
    re.IGNORECASE,
)


@pytest.fixture
def admin_urls():
    return reverse("admin:login"), reverse("admin:index")


def login_data(index_url, **extra):
    return {
        "username": "admin",
        "password": "password",
        "next": index_url,
        **extra,
    }


def test_admin_is_served_from_configured_url():
    assert reverse("admin:index") == f"/{settings.ADMIN_URL}"


@pytest.mark.django_db
def test_admin_login_with_username_and_password(
    client, admin_user, admin_urls
):
    login_url, index_url = admin_urls

    assert 'name="otp_token"' not in client.get(login_url).content.decode()
    response = client.post(login_url, login_data(index_url))

    assert response.status_code == 302
    assert client.get(index_url).status_code == 200


@pytest.mark.django_db
def test_admin_rejects_wrong_password(client, admin_user, admin_urls):
    login_url, index_url = admin_urls
    response = client.post(
        login_url, login_data(index_url, password="wrong-password")
    )

    assert response.status_code == 200
    assert client.get(index_url).status_code == 302
    assert 'value="wrong-password"' not in response.content.decode()


@pytest.mark.django_db
def test_admin_locks_out_after_failed_logins(client, admin_user, admin_urls):
    login_url, index_url = admin_urls
    wrong = login_data(index_url, password="wrong-password")

    for _ in range(settings.AXES_FAILURE_LIMIT):
        client.post(login_url, wrong)
    response = client.post(login_url, login_data(index_url))

    assert response.status_code == 429
    assert "core/lockout.html" in [t.name for t in response.templates]


@pytest.mark.parametrize(
    ("use_header", "expected"), [(True, "203.0.113.7"), (False, "10.0.0.2")]
)
def test_client_ip_trusts_header_only_behind_proxy(use_header, expected):
    request = RequestFactory().get(
        "/", REMOTE_ADDR="10.0.0.2", HTTP_X_REAL_IP="203.0.113.7"
    )

    with override_settings(USE_X_REAL_IP=use_header):
        assert client_ip(request) == expected


def test_deploy_check_warns_about_weak_admin_protection():
    with override_settings(ADMIN_URL="admin/"):
        ids = {warning.id for warning in check_admin_protection(None)}
    assert ids == {"core.W001"}

    with override_settings(ADMIN_URL="studio-panel-7f3a/"):
        assert check_admin_protection(None) == []


@pytest.mark.django_db
def test_pages_send_content_security_policy(client):
    policy = client.get(reverse("studio:index"))["Content-Security-Policy"]

    parts = (part.strip() for part in policy.split(";"))
    directives = dict(part.split(" ", 1) for part in parts if " " in part)
    assert directives["script-src"] == "'self'"
    assert directives["font-src"] == "'self'"
    assert settings.BOOKING_ORIGIN in directives["frame-src"].split()
    assert directives["frame-ancestors"] == "'none'"
    assert directives["object-src"] == "'none'"


@pytest.mark.parametrize(
    "url",
    [
        "/",
        "/services/keratin/",
        "/articles/",
        "/articles/care-tips/",
        "/price/",
    ],
)
def test_pages_have_no_inline_scripts(client, content, url):
    html = client.get(url).content.decode()

    assert not INLINE_SCRIPT.search(html)
    assert not re.search(r"\son[a-z]+=", html)
    assert "googleapis" not in html


@pytest.mark.django_db
def test_booking_button_works_without_javascript(client):
    html = client.get(reverse("studio:index")).content.decode()

    assert f'href="{settings.BOOKING_URL}"' in html
    assert f'data-src="{settings.BOOKING_URL}"' in html
    assert "widget.js" not in html
