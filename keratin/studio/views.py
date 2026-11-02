from django.http import HttpResponse
from django.urls import reverse
from django.views.generic import DetailView, TemplateView

from .models import (
    Article,
    HomePage,
    PortfolioPhoto,
    PortfolioVideo,
    PriceCategory,
    Question,
    Review,
    Service,
)


def price_categories():
    """Опубликованные разделы прайса, в которых есть цены."""
    return (
        PriceCategory.objects.published()
        .filter(items__isnull=False)
        .distinct()
        .prefetch_related("items")
    )


class IndexView(TemplateView):
    template_name = "studio/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["home"] = HomePage.load()
        context["services"] = Service.objects.published()
        photos = list(
            PortfolioPhoto.objects.published().select_related("service")
        )
        context["photos"] = photos
        videos = list(PortfolioVideo.objects.ready().select_related("service"))
        context["photo_services"] = sorted(
            {item.service for item in [*photos, *videos] if item.service},
            key=lambda service: (service.order, service.pk),
        )
        context["videos"] = videos
        context["categories"] = price_categories()
        context["reviews"] = Review.objects.published().select_related(
            "service"
        )
        context["questions"] = Question.objects.published()
        return context


class ServiceDetailView(DetailView):
    queryset = Service.objects.with_page()
    template_name = "studio/service_detail.html"
    context_object_name = "service"


class ArticleDetailView(DetailView):
    queryset = Article.objects.published().prefetch_related("sections")
    template_name = "studio/article_detail.html"
    context_object_name = "article"


class PriceView(TemplateView):
    template_name = "studio/price.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = price_categories()
        return context


def robots_txt(request):
    """Правила для поисковиков. Адрес админки здесь не упоминается."""
    sitemap = request.build_absolute_uri(reverse("studio:sitemap"))
    lines = ["User-agent: *", "Disallow:", "", f"Sitemap: {sitemap}", ""]
    return HttpResponse(
        "\n".join(lines), content_type="text/plain; charset=utf-8"
    )
