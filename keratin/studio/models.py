import uuid
from pathlib import PurePath
from urllib.parse import urlencode

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.validators import FileExtensionValidator, RegexValidator
from django.db import models
from django.urls import reverse

from core.fields import OwnedFileField, RichTextField, WebPImageField
from core.storage import private_storage

LINE_BREAK_HINT = "Enter переносит строку. Пустые строки не выводятся."
IMAGE_HINT = "JPEG, PNG или WebP. Фото уменьшится и сохранится в WebP."
ALT_HINT = "Что изображено на фото. Читают поисковики и незрячие люди."
SLUG_HINT = "Латинские буквы, цифры и дефис. Часть адреса страницы."


class PublishedQuerySet(models.QuerySet):
    def published(self):
        return self.filter(is_published=True)


class ServiceQuerySet(PublishedQuerySet):
    def with_page(self):
        """Опубликованные услуги, у которых есть своя страница."""
        return self.published().exclude(body="")


class Service(models.Model):
    title = models.CharField("Заголовок", max_length=120)
    menu_title = models.CharField(
        "Название в меню", max_length=40, help_text="Коротко, одно-два слова."
    )
    slug = models.SlugField("Адрес", unique=True, help_text=SLUG_HINT)
    teaser = models.TextField(
        "Коротко на главной",
        max_length=300,
        help_text="Текст в карточке процедуры на главной.",
    )
    price_from = models.PositiveIntegerField(
        "Цена от, ₽",
        null=True,
        blank=True,
        help_text="Выводится в карточке на главной. Если пусто, цены нет.",
    )
    subtitle = models.TextField(
        "Подзаголовок", max_length=300, blank=True, help_text=LINE_BREAK_HINT
    )
    body = RichTextField(
        "Текст",
        blank=True,
        help_text=(
            "Маркированный список выводится с галочками. Shift+Enter "
            "переносит строку внутри пункта. Если текста нет, своей "
            "страницы у услуги нет, а кнопка в карточке ведёт к ценам."
        ),
    )
    image = WebPImageField(
        "Фото",
        upload_to="services/",
        width_field="image_width",
        height_field="image_height",
        blank=True,
        help_text=IMAGE_HINT,
    )
    image_width = models.PositiveIntegerField(null=True, editable=False)
    image_height = models.PositiveIntegerField(null=True, editable=False)
    image_alt = models.CharField(
        "Описание фото", max_length=200, blank=True, help_text=ALT_HINT
    )
    seo_title = models.CharField(
        "Заголовок вкладки браузера",
        max_length=70,
        blank=True,
        help_text="Если пусто, берётся заголовок.",
    )
    seo_description = models.CharField(
        "Описание для поисковиков", max_length=300, blank=True
    )
    order = models.PositiveSmallIntegerField("Порядок", default=0)
    is_published = models.BooleanField("Опубликовано", default=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ServiceQuerySet.as_manager()

    class Meta:
        ordering = ["order", "pk"]
        verbose_name = "вид услуги"
        verbose_name_plural = "услуги"

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("studio:service", kwargs={"slug": self.slug})

    @property
    def has_page(self):
        return bool(self.body)


class Article(models.Model):
    title = models.CharField("Заголовок", max_length=120)
    slug = models.SlugField("Адрес", unique=True, help_text=SLUG_HINT)
    subtitle = models.TextField(
        "Подзаголовок", max_length=300, blank=True, help_text=LINE_BREAK_HINT
    )
    teaser = models.TextField(
        "Анонс", max_length=300, help_text="Текст в списке статей."
    )
    seo_description = models.CharField(
        "Описание для поисковиков", max_length=300, blank=True
    )
    order = models.PositiveSmallIntegerField("Порядок", default=0)
    is_published = models.BooleanField("Опубликовано", default=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = PublishedQuerySet.as_manager()

    class Meta:
        ordering = ["order", "pk"]
        verbose_name = "материал"
        verbose_name_plural = "статьи"

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("studio:article", kwargs={"slug": self.slug})

    @property
    def cover(self):
        """Первое фото статьи для карточки в списке."""
        for section in self.sections.all():
            if section.image:
                return section
        return None


class ArticleSection(models.Model):
    article = models.ForeignKey(
        Article, on_delete=models.CASCADE, related_name="sections"
    )
    heading = models.TextField(
        "Заголовок раздела",
        max_length=200,
        blank=True,
        help_text=LINE_BREAK_HINT,
    )
    body = RichTextField("Текст")
    image = WebPImageField(
        "Фото",
        upload_to="articles/",
        width_field="image_width",
        height_field="image_height",
        blank=True,
        help_text=IMAGE_HINT,
    )
    image_width = models.PositiveIntegerField(null=True, editable=False)
    image_height = models.PositiveIntegerField(null=True, editable=False)
    image_alt = models.CharField(
        "Описание фото", max_length=200, blank=True, help_text=ALT_HINT
    )
    order = models.PositiveSmallIntegerField("Порядок", default=0)

    class Meta:
        ordering = ["order", "pk"]
        verbose_name = "раздел"
        verbose_name_plural = "разделы"

    def __str__(self):
        return self.heading.splitlines()[0] if self.heading else "Раздел"


class PriceCategory(models.Model):
    title = models.CharField("Название", max_length=80)
    note = models.TextField(
        "Примечание",
        blank=True,
        help_text="Выводится под ценами. " + LINE_BREAK_HINT,
    )
    order = models.PositiveSmallIntegerField("Порядок", default=0)
    is_published = models.BooleanField("Опубликовано", default=True)

    objects = PublishedQuerySet.as_manager()

    class Meta:
        ordering = ["order", "pk"]
        verbose_name = "раздел прайса"
        verbose_name_plural = "прайс"

    def __str__(self):
        return self.title


class PriceItem(models.Model):
    category = models.ForeignKey(
        PriceCategory, on_delete=models.CASCADE, related_name="items"
    )
    name = models.CharField(
        "Позиция", max_length=120, help_text="Например: 25 см."
    )
    price = models.PositiveIntegerField("Цена, ₽")
    price_from = models.BooleanField(
        "Цена «от»", default=False, help_text="Перед ценой выводится «от»."
    )
    order = models.PositiveSmallIntegerField("Порядок", default=0)

    class Meta:
        ordering = ["order", "pk"]
        verbose_name = "пункт прайса"
        verbose_name_plural = "пункты прайса"

    def __str__(self):
        return f"{self.category}, {self.name}, {self.price} ₽"


THUMBNAIL_SIDE = 600
POSTER_SIDE = 960
VIDEO_EXTENSIONS = ["mp4", "mov", "m4v", "webm", "3gp"]


def video_source_path(instance, filename):
    suffix = PurePath(filename).suffix.lower()
    return f"videos/{uuid.uuid4().hex}{suffix}"


def validate_video_size(file):
    limit = settings.VIDEO_MAX_UPLOAD_MB
    if file.size > limit * 1024 * 1024:
        raise ValidationError(f"Файл больше {limit} МБ.")


class PortfolioPhoto(models.Model):
    service = models.ForeignKey(
        Service,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="photos",
        verbose_name="Услуга",
        help_text="По услугам работает фильтр в портфолио.",
    )
    image = WebPImageField(
        "Фото",
        upload_to="portfolio/photos/",
        width_field="image_width",
        height_field="image_height",
        help_text=IMAGE_HINT,
    )
    image_width = models.PositiveIntegerField(null=True, editable=False)
    image_height = models.PositiveIntegerField(null=True, editable=False)
    thumbnail = WebPImageField(
        upload_to="portfolio/thumbnails/",
        max_side=THUMBNAIL_SIDE,
        width_field="thumbnail_width",
        height_field="thumbnail_height",
        blank=True,
        editable=False,
    )
    thumbnail_width = models.PositiveIntegerField(null=True, editable=False)
    thumbnail_height = models.PositiveIntegerField(null=True, editable=False)
    image_alt = models.CharField(
        "Описание фото",
        max_length=200,
        blank=True,
        help_text=ALT_HINT + " Если пусто, берётся название услуги.",
    )
    order = models.PositiveSmallIntegerField("Порядок", default=0)
    is_published = models.BooleanField("Опубликовано", default=True)

    objects = PublishedQuerySet.as_manager()

    class Meta:
        ordering = ["order", "pk"]
        verbose_name = "снимок"
        verbose_name_plural = "фото работ"

    def __str__(self):
        if self.image_alt:
            return self.image_alt
        if self.service:
            return self.service.menu_title
        return f"Фото {self.pk}"

    def save(self, *args, **kwargs):
        # Новое фото: превью для сетки делается из того же файла.
        if self.image and not self.image._committed:
            self.image.seek(0)
            self.thumbnail = ContentFile(self.image.read(), name="thumbnail")
        super().save(*args, **kwargs)


class PortfolioVideoQuerySet(PublishedQuerySet):
    def ready(self):
        return self.published().filter(status=PortfolioVideo.Status.READY)


class PortfolioVideo(models.Model):
    service = models.ForeignKey(
        Service,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="videos",
        verbose_name="Услуга",
        help_text="По услугам работает фильтр в портфолио.",
    )

    class Status(models.TextChoices):
        PENDING = "pending", "Ждёт обработки"
        PROCESSING = "processing", "Обрабатывается"
        READY = "ready", "Готов"
        FAILED = "failed", "Ошибка"

    title = models.CharField(
        "Подпись", max_length=120, help_text="Выводится под роликом."
    )
    source = OwnedFileField(
        "Видеофайл",
        upload_to=video_source_path,
        storage=private_storage,
        validators=[
            FileExtensionValidator(VIDEO_EXTENSIONS),
            validate_video_size,
        ],
    )
    video = OwnedFileField(
        upload_to="portfolio/videos/", blank=True, editable=False
    )
    poster = WebPImageField(
        upload_to="portfolio/posters/",
        max_side=POSTER_SIDE,
        width_field="width",
        height_field="height",
        blank=True,
        editable=False,
    )
    width = models.PositiveIntegerField(null=True, editable=False)
    height = models.PositiveIntegerField(null=True, editable=False)
    duration = models.PositiveIntegerField(
        "Длительность, с", null=True, editable=False
    )
    status = models.CharField(
        "Состояние",
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
        editable=False,
    )
    error = models.TextField("Ошибка", blank=True, editable=False)
    order = models.PositiveSmallIntegerField("Порядок", default=0)
    is_published = models.BooleanField("Опубликовано", default=True)

    objects = PortfolioVideoQuerySet.as_manager()

    class Meta:
        ordering = ["order", "pk"]
        verbose_name = "ролик"
        verbose_name_plural = "видео работ"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # Новый исходник: прежний результат удаляется, ролик снова
        # встаёт в очередь на перекодирование.
        if self.source and not self.source._committed:
            self.status = self.Status.PENDING
            self.error = ""
            self.video = ""
            self.poster = ""
            self.duration = None
        super().save(*args, **kwargs)


class SiteSettings(models.Model):
    """Контакты студии. Запись одна, правится в админке."""

    name = models.CharField(
        "Название студии",
        max_length=120,
        default="Keratin studio by Diana Bocharova",
        help_text="Выводится во вкладке браузера и в подвале.",
    )
    place = models.CharField(
        "Место",
        max_length=120,
        blank=True,
        help_text="Например: ТЦ «Франт».",
    )
    street = models.CharField("Улица и дом", max_length=120, blank=True)
    city = models.CharField("Город", max_length=60, blank=True)
    phone = models.CharField(
        "Телефон",
        max_length=12,
        blank=True,
        validators=[
            RegexValidator(r"^\+7\d{10}$", "Номер в формате +79991234567.")
        ],
        help_text="В формате +79991234567, на сайте будет 8 (999) 123-45-67.",
    )
    email = models.EmailField("Почта", blank=True)
    hours = models.TextField(
        "Часы работы", blank=True, help_text=LINE_BREAK_HINT
    )
    vk_url = models.URLField("ВКонтакте", blank=True)
    instagram_url = models.URLField("Instagram", blank=True)
    telegram_url = models.URLField("Telegram", blank=True)

    class Meta:
        verbose_name = "блок контактов"
        verbose_name_plural = "контакты"

    def __str__(self):
        return "Контакты студии"

    @classmethod
    def load(cls):
        """Сохранённые контакты или пустая запись, если их ещё не задали."""
        return cls.objects.first() or cls()

    @property
    def social_links(self):
        links = [
            ("vk", "ВКонтакте", self.vk_url),
            ("instagram", "Instagram", self.instagram_url),
            ("telegram", "Telegram", self.telegram_url),
        ]
        return [(icon, title, url) for icon, title, url in links if url]

    @property
    def map_url(self):
        """Адрес студии в Яндекс Картах."""
        address = ", ".join(part for part in [self.city, self.street] if part)
        if not address:
            return ""
        return "https://yandex.ru/maps/?" + urlencode({"text": address})


def text_lines(text):
    """Непустые строки текста: каждая строка поля выводится пунктом."""
    return [line.strip() for line in text.splitlines() if line.strip()]


ONE_PER_LINE_HINT = "Каждый пункт с новой строки."


class HomePage(models.Model):
    """Тексты главной страницы. Запись одна, правится в админке."""

    hero_title = models.CharField(
        "Заголовок",
        max_length=150,
        default="Кератиновое выпрямление, ботокс и нанопластика волос "
        "в Казани",
    )
    hero_subtitle = models.TextField(
        "Подзаголовок",
        max_length=300,
        blank=True,
        default="Гладкие и послушные волосы без пуха: укладка за 5 минут "
        "феном и расчёской",
    )
    price_from = models.PositiveIntegerField(
        "Цена от, ₽",
        null=True,
        blank=True,
        default=2500,
        help_text="Выводится на первом экране. Если пусто, цены нет.",
    )
    promo = models.CharField(
        "Акция",
        max_length=80,
        blank=True,
        default="−15% на первое посещение",
        help_text="Плашка на первом экране и под ценами. Если пусто, её нет.",
    )
    trust = models.TextField(
        "Преимущества",
        blank=True,
        default="Сертифицированный мастер: кератин, ботокс, нанопластика\n"
        "Опыт более 2 лет\n"
        "Только безопасные составы\n"
        "Нанопластика: эффект до 12 месяцев",
        help_text=ONE_PER_LINE_HINT + " Лучше всего смотрятся 4 пункта.",
    )
    problems_title = models.CharField(
        "Заголовок", max_length=120, default="Какая процедура вам подходит?"
    )
    problems_intro = models.TextField(
        "Вступление",
        blank=True,
        default="Процедуры подходят не только для кудрявых волос. Если "
        "узнаёте себя хотя бы в одном пункте, одна из них решит проблему.",
    )
    problems = models.TextField(
        "Пункты",
        blank=True,
        default="Волосы прямые, но очень пушатся или потеряли блеск. "
        "Сухие, ломкие или секущиеся кончики.\n"
        "Не получается отрастить волосы. Стрижёте кончики каждый месяц, "
        "но они секутся.\n"
        "Волосы потеряли свой привычный вид или испорчены после "
        "осветления или окрашивания.\n"
        "Волосы сильно вьются или вьются только на концах. Вы "
        "обладательница афрокудрей.\n"
        "Волосы по длине полностью устраивают, но концы смотрят в разные "
        "стороны.\n"
        "Не можете сделать красивый хвост, потому что волосы торчат "
        "в разные стороны.",
        help_text=ONE_PER_LINE_HINT,
    )
    master_name = models.CharField("Имя", max_length=60, default="Диана")
    master_text = models.TextField(
        "О мастере",
        blank=True,
        default="Сертифицированный специалист по кератину, ботоксу "
        "и нанопластике. Опыт работы более двух лет. Использую только "
        "безопасные составы.",
        help_text=LINE_BREAK_HINT,
    )
    master_photo = WebPImageField(
        "Фото мастера",
        upload_to="master/",
        max_side=POSTER_SIDE,
        width_field="master_photo_width",
        height_field="master_photo_height",
        blank=True,
        help_text=IMAGE_HINT + " Лучше квадратное, лицо по центру. Если "
        "фото нет, выводится прежнее.",
    )
    master_photo_width = models.PositiveIntegerField(null=True, editable=False)
    master_photo_height = models.PositiveIntegerField(
        null=True, editable=False
    )

    class Meta:
        verbose_name = "текст главной страницы"
        verbose_name_plural = "главная страница"

    def __str__(self):
        return "Главная страница"

    @classmethod
    def load(cls):
        """Сохранённые тексты или тексты по умолчанию."""
        return cls.objects.first() or cls()

    @property
    def trust_items(self):
        return text_lines(self.trust)

    @property
    def problem_items(self):
        return text_lines(self.problems)


class Review(models.Model):
    author = models.CharField("Имя", max_length=80)
    text = models.TextField(
        "Отзыв", max_length=1500, help_text=LINE_BREAK_HINT
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviews",
        verbose_name="Процедура",
    )
    order = models.PositiveSmallIntegerField("Порядок", default=0)
    is_published = models.BooleanField(
        "Опубликовано",
        default=True,
        help_text="Блок отзывов появляется на сайте, когда опубликован "
        "хотя бы один.",
    )

    objects = PublishedQuerySet.as_manager()

    class Meta:
        ordering = ["order", "pk"]
        verbose_name = "отзыв"
        verbose_name_plural = "отзывы"

    def __str__(self):
        return self.author


class Question(models.Model):
    question = models.CharField("Вопрос", max_length=200)
    answer = RichTextField("Ответ")
    order = models.PositiveSmallIntegerField("Порядок", default=0)
    is_published = models.BooleanField("Опубликовано", default=True)

    objects = PublishedQuerySet.as_manager()

    class Meta:
        ordering = ["order", "pk"]
        verbose_name = "вопрос"
        verbose_name_plural = "частые вопросы"

    def __str__(self):
        return self.question
