import gzip

from django.urls import reverse


def test_pages_are_compressed(client, db):
    response = client.get(
        reverse("studio:index"), HTTP_ACCEPT_ENCODING="gzip, br"
    )

    assert response["Content-Encoding"] == "gzip"
    assert "Accept-Encoding" in response["Vary"]
    assert "<h1" in gzip.decompress(response.content).decode()


def test_home_page_preloads_header_image(client, db):
    html = client.get(reverse("studio:index")).content.decode()

    assert 'rel="preload"' in html
    assert 'fetchpriority="high"' in html
