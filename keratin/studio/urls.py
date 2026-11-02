from django.contrib.sitemaps.views import sitemap
from django.urls import path, reverse_lazy
from django.views.generic import RedirectView

from . import views
from .sitemaps import SITEMAPS

app_name = "studio"


def moved_to(url_name, **kwargs):
    url = reverse_lazy(url_name, kwargs=kwargs or None)
    return RedirectView.as_view(url=url, permanent=True)


urlpatterns = [
    path("", views.IndexView.as_view(), name="index"),
    path(
        "services/<slug:slug>/",
        views.ServiceDetailView.as_view(),
        name="service",
    ),
    path(
        "articles/",
        moved_to("studio:article", slug="care-tips"),
        name="articles",
    ),
    path(
        "articles/<slug:slug>/",
        views.ArticleDetailView.as_view(),
        name="article",
    ),
    path("price/", views.PriceView.as_view(), name="price"),
    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": SITEMAPS},
        name="sitemap",
    ),
    path("robots.txt", views.robots_txt, name="robots"),
    # Адреса первой версии сайта.
    path("keratin_procedure/", moved_to("studio:service", slug="keratin")),
    path("botox_procedure/", moved_to("studio:service", slug="botox")),
    path(
        "nano_plastic_procedure/",
        moved_to("studio:service", slug="nanoplastic"),
    ),
    path("care_tips/", moved_to("studio:article", slug="care-tips")),
]
