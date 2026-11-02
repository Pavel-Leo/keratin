from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction

from studio.initial_content import (
    ARTICLES,
    CONTACTS,
    IMAGES_DIR,
    PORTFOLIO_PHOTOS,
    PORTFOLIO_VIDEOS,
    PRICE,
    QUESTIONS,
    REVIEW_EXAMPLE,
    SERVICES,
    VIDEOS_DIR,
)
from studio.models import (
    Article,
    ArticleSection,
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


def attach_image(instance, filename):
    with (IMAGES_DIR / filename).open("rb") as image:
        instance.image = File(image, name=filename)
        instance.save()


class Command(BaseCommand):
    help = (
        "Загружает начальные тексты, фото и цены. Существующие записи "
        "не изменяются, поэтому команду можно запускать повторно."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        created = []
        created += self.load_services()
        created += self.load_articles()
        created += self.load_price()
        created += self.load_portfolio()
        created += self.load_contacts()
        created += self.load_home()
        if created:
            self.stdout.write("Добавлено: " + ", ".join(created))
        else:
            self.stdout.write("Всё уже загружено, ничего не изменено.")

    def load_services(self):
        created = []
        for order, data in enumerate(SERVICES):
            if Service.objects.filter(slug=data["slug"]).exists():
                continue
            fields = {k: v for k, v in data.items() if k != "image"}
            service = Service(order=order, **fields)
            if "image" in data:
                attach_image(service, data["image"])
            else:
                service.save()
            created.append(f"услуга «{service.title}»")
        return created

    def load_articles(self):
        created = []
        for order, data in enumerate(ARTICLES):
            if Article.objects.filter(slug=data["slug"]).exists():
                continue
            fields = {k: v for k, v in data.items() if k != "sections"}
            article = Article.objects.create(order=order, **fields)
            for section_order, section_data in enumerate(data["sections"]):
                section_fields = {
                    k: v for k, v in section_data.items() if k != "image"
                }
                section = ArticleSection(
                    article=article, order=section_order, **section_fields
                )
                attach_image(section, section_data["image"])
            created.append(f"статья «{article.title}»")
        return created

    def load_price(self):
        if PriceCategory.objects.exists():
            return []
        for order, data in enumerate(PRICE):
            category = PriceCategory.objects.create(
                title=data["title"], note=data["note"], order=order
            )
            PriceItem.objects.bulk_create(
                PriceItem(category=category, name=name, price=price, order=i)
                for i, (name, price) in enumerate(data["items"])
            )
        return ["прайс"]

    def load_portfolio(self):
        created = []
        if not PortfolioPhoto.objects.exists():
            services = Service.objects.in_bulk(field_name="slug")
            for order, (filename, slug, alt) in enumerate(PORTFOLIO_PHOTOS):
                photo = PortfolioPhoto(
                    service=services.get(slug), image_alt=alt, order=order
                )
                attach_image(photo, filename)
            created.append("фото работ")
        if not PortfolioVideo.objects.exists():
            for order, (filename, title) in enumerate(PORTFOLIO_VIDEOS):
                slug = (
                    "nanoplastic" if filename.startswith("nano") else "keratin"
                )
                video = PortfolioVideo(
                    title=title,
                    order=order,
                    service=Service.objects.filter(slug=slug).first(),
                )
                with (VIDEOS_DIR / filename).open("rb") as source:
                    video.source = File(source, name=filename)
                    video.save()
            created.append(
                "ролики (появятся на сайте после команды process_videos)"
            )
        return created

    def load_contacts(self):
        if SiteSettings.objects.exists():
            return []
        SiteSettings.objects.create(**CONTACTS)
        return ["контакты"]

    def load_home(self):
        created = []
        if not HomePage.objects.exists():
            HomePage.objects.create()
            created.append("тексты главной страницы")
        if not Question.objects.exists():
            Question.objects.bulk_create(
                Question(question=question, answer=answer, order=order)
                for order, (question, answer) in enumerate(QUESTIONS)
            )
            created.append("частые вопросы")
        if not Review.objects.exists():
            Review.objects.create(**REVIEW_EXAMPLE)
            created.append("пример отзыва (не опубликован)")
        return created
