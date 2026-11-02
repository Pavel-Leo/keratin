from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.db import models
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.html import format_html

from .models import (
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


@admin.display(description="Сейчас на сайте")
def image_preview(obj):
    if obj and obj.image:
        return format_html(
            '<img src="{}" alt="" class="admin-image-preview">', obj.image.url
        )
    return "Фото не загружено"


class StudioMedia:
    css = {"all": ["css/admin.css"]}


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    Media = StudioMedia
    list_display = ["title", "price_from", "order", "is_published"]
    list_editable = ["order", "is_published"]
    prepopulated_fields = {"slug": ["menu_title"]}
    readonly_fields = [image_preview]
    fieldsets = [
        (
            None,
            {
                "fields": [
                    "title",
                    "menu_title",
                    "slug",
                    "order",
                    "is_published",
                ]
            },
        ),
        ("Карточка на главной", {"fields": ["teaser", "price_from"]}),
        ("Страница услуги", {"fields": ["subtitle", "body"]}),
        ("Фото", {"fields": ["image", image_preview, "image_alt"]}),
        (
            "Для поисковиков",
            {
                "fields": ["seo_title", "seo_description"],
                "classes": ["collapse"],
            },
        ),
    ]


class ArticleSectionInline(admin.StackedInline):
    model = ArticleSection
    extra = 0
    fields = ["heading", "body", "image", image_preview, "image_alt", "order"]
    readonly_fields = [image_preview]


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    Media = StudioMedia
    list_display = ["title", "order", "is_published"]
    list_editable = ["order", "is_published"]
    prepopulated_fields = {"slug": ["title"]}
    inlines = [ArticleSectionInline]
    fieldsets = [
        (None, {"fields": ["title", "slug", "order", "is_published"]}),
        ("Текст", {"fields": ["subtitle", "teaser"]}),
        (
            "Для поисковиков",
            {"fields": ["seo_description"], "classes": ["collapse"]},
        ),
    ]


class PriceItemInline(admin.StackedInline):
    model = PriceItem
    extra = 1
    fields = [("name", "price", "price_from", "order")]


@admin.register(PriceCategory)
class PriceCategoryAdmin(admin.ModelAdmin):
    Media = StudioMedia
    list_display = ["title", "order", "is_published"]
    list_editable = ["order", "is_published"]
    fields = ["title", "note", "order", "is_published"]
    inlines = [PriceItemInline]


@admin.display(description="Превью")
def photo_thumbnail(obj):
    if obj.thumbnail:
        return format_html(
            '<img src="{}" alt="" class="admin-list-thumbnail">',
            obj.thumbnail.url,
        )
    return None


@admin.register(PortfolioPhoto)
class PortfolioPhotoAdmin(admin.ModelAdmin):
    Media = StudioMedia
    list_display = [
        photo_thumbnail,
        "__str__",
        "service",
        "order",
        "is_published",
    ]
    list_display_links = [photo_thumbnail, "__str__"]
    list_editable = ["order", "is_published"]
    list_filter = ["service", "is_published"]
    fields = [
        "image",
        image_preview,
        "image_alt",
        "service",
        "order",
        "is_published",
    ]
    readonly_fields = [image_preview]


class PortfolioVideoForm(forms.ModelForm):
    class Meta:
        model = PortfolioVideo
        fields = ["title", "service", "source", "order", "is_published"]
        # Без ссылки на текущий файл: исходники не раздаются.
        widgets = {"source": forms.FileInput(attrs={"accept": "video/*"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        hint = (
            f"MP4, MOV или WebM, до {settings.VIDEO_MAX_UPLOAD_MB} МБ "
            f"и {settings.VIDEO_MAX_SECONDS // 60} мин. Ролик "
            "перекодируется для сайта за несколько минут и появится "
            "на сайте сам."
        )
        if self.instance.pk:
            hint = "Выберите файл, только чтобы заменить ролик. " + hint
        self.fields["source"].help_text = hint


@admin.display(description="Превью")
def video_thumbnail(obj):
    if obj.poster:
        return format_html(
            '<img src="{}" alt="" class="admin-list-thumbnail">',
            obj.poster.url,
        )
    return None


@admin.display(description="Сейчас на сайте")
def video_preview(obj):
    if obj.status == PortfolioVideo.Status.READY and obj.video:
        return format_html(
            '<video src="{}" poster="{}" controls preload="none" '
            'class="admin-video-preview"></video>',
            obj.video.url,
            obj.poster.url if obj.poster else "",
        )
    return "Ролик ещё не готов"


@admin.display(description="Состояние")
def video_status(obj):
    if obj.status == PortfolioVideo.Status.FAILED and obj.error:
        return f"{obj.get_status_display()}: {obj.error}"
    return obj.get_status_display()


@admin.register(PortfolioVideo)
class PortfolioVideoAdmin(admin.ModelAdmin):
    Media = StudioMedia
    form = PortfolioVideoForm
    list_display = [
        video_thumbnail,
        "title",
        video_status,
        "order",
        "is_published",
    ]
    list_display_links = [video_thumbnail, "title"]
    list_editable = ["order", "is_published"]
    readonly_fields = [video_status, video_preview, "duration"]
    actions = ["process_again"]

    def get_fields(self, request, obj=None):
        fields = ["title", "service", "source", "order", "is_published"]
        if obj is None:
            return fields
        return [*fields, video_status, video_preview, "duration"]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if "source" in form.changed_data:
            self.message_user(
                request,
                "Ролик загружен и встал в очередь на перекодирование. "
                "Через несколько минут он появится на сайте.",
                messages.INFO,
            )

    @admin.action(description="Перекодировать заново")
    def process_again(self, request, queryset):
        count = queryset.exclude(
            status=PortfolioVideo.Status.PROCESSING
        ).update(status=PortfolioVideo.Status.PENDING, error="")
        self.message_user(request, f"Поставлено в очередь: {count}.")


class SingletonAdmin(admin.ModelAdmin):
    """Одна запись: список сразу открывает её форму."""

    def has_add_permission(self, request):
        return not self.model.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        opts = self.model._meta
        name = f"admin:{opts.app_label}_{opts.model_name}"
        obj = self.model.objects.first()
        if obj is None:
            return redirect(reverse(f"{name}_add"))
        return redirect(reverse(f"{name}_change", args=[obj.pk]))


@admin.register(SiteSettings)
class SiteSettingsAdmin(SingletonAdmin):
    formfield_overrides = {models.URLField: {"assume_scheme": "https"}}
    fieldsets = [
        (None, {"fields": ["name"]}),
        ("Адрес", {"fields": ["place", "street", "city", "hours"]}),
        ("Связь", {"fields": ["phone", "email"]}),
        (
            "Социальные сети",
            {"fields": ["vk_url", "instagram_url", "telegram_url"]},
        ),
    ]


@admin.display(description="Сейчас на сайте")
def master_photo_preview(obj):
    if obj and obj.master_photo:
        return format_html(
            '<img src="{}" alt="" class="admin-image-preview">',
            obj.master_photo.url,
        )
    return "Прежнее фото"


@admin.register(HomePage)
class HomePageAdmin(SingletonAdmin):
    Media = StudioMedia
    readonly_fields = [master_photo_preview]
    fieldsets = [
        (
            "Первый экран",
            {"fields": ["hero_title", "hero_subtitle", "price_from", "promo"]},
        ),
        ("Под первым экраном", {"fields": ["trust"]}),
        (
            "Блок «Какая процедура вам подходит?»",
            {"fields": ["problems_title", "problems_intro", "problems"]},
        ),
        (
            "Мастер",
            {
                "fields": [
                    "master_name",
                    "master_text",
                    "master_photo",
                    master_photo_preview,
                ]
            },
        ),
    ]


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["author", "service", "order", "is_published"]
    list_editable = ["order", "is_published"]
    list_filter = ["is_published"]
    fields = ["author", "text", "service", "order", "is_published"]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    Media = StudioMedia
    list_display = ["question", "order", "is_published"]
    list_editable = ["order", "is_published"]
    fields = ["question", "answer", "order", "is_published"]
