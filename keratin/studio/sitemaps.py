from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Article, Service


class PageSitemap(Sitemap):
    def items(self):
        return ["studio:index", "studio:price"]

    def location(self, item):
        return reverse(item)


class ServiceSitemap(Sitemap):
    def items(self):
        return Service.objects.with_page()

    def lastmod(self, obj):
        return obj.updated_at


class ArticleSitemap(Sitemap):
    def items(self):
        return Article.objects.published()

    def lastmod(self, obj):
        return obj.updated_at


SITEMAPS = {
    "pages": PageSitemap,
    "services": ServiceSitemap,
    "articles": ArticleSitemap,
}
