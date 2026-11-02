from io import BytesIO
from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.messages import get_messages
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from PIL import Image

from studio.models import PortfolioPhoto, PortfolioVideo, Service

Status = PortfolioVideo.Status


def jpeg(size=(1200, 1600), name="IMG_0001.jpg"):
    buffer = BytesIO()
    Image.new("RGB", size, "pink").save(buffer, "JPEG")
    return SimpleUploadedFile(name, buffer.getvalue(), "image/jpeg")


def clip(name="IMG_0002.MOV"):
    return SimpleUploadedFile(name, b"fake video", "video/quicktime")


def make_ready(video):
    """Ролик с результатом, как после перекодирования."""
    video.video = SimpleUploadedFile("out.mp4", b"mp4", "video/mp4")
    video.poster = jpeg(size=(1080, 1920), name="poster.jpg")
    video.status = Status.READY
    video.save()
    return video


@pytest.fixture
def photo(service):
    return PortfolioPhoto.objects.create(service=service, image=jpeg())


@pytest.fixture
def video(db):
    return PortfolioVideo.objects.create(
        title="Кератин на блонд", source=clip()
    )


def test_photo_gets_webp_thumbnail(photo):
    assert photo.image.name.endswith(".webp")
    assert photo.thumbnail.name.startswith("portfolio/thumbnails/")
    with Image.open(photo.thumbnail.path) as thumbnail:
        assert thumbnail.format == "WEBP"
        assert thumbnail.size == (450, 600)
    assert (photo.thumbnail_width, photo.thumbnail_height) == (450, 600)


def test_replaced_photo_files_are_deleted(
    photo, django_capture_on_commit_callbacks
):
    old_files = [Path(photo.image.path), Path(photo.thumbnail.path)]

    with django_capture_on_commit_callbacks(execute=True):
        photo.image = jpeg()
        photo.save()

    assert not any(path.exists() for path in old_files)
    assert Path(photo.thumbnail.path).exists()


def test_deleted_photo_files_are_removed(
    photo, django_capture_on_commit_callbacks
):
    files = [Path(photo.image.path), Path(photo.thumbnail.path)]

    with django_capture_on_commit_callbacks(execute=True):
        photo.delete()

    assert not any(path.exists() for path in files)


def test_cleared_image_is_removed_from_disk(
    service, django_capture_on_commit_callbacks
):
    service.image = jpeg()
    service.save()
    path = Path(service.image.path)

    with django_capture_on_commit_callbacks(execute=True):
        service.image = ""
        service.save()

    assert not path.exists()


def test_video_source_is_kept_out_of_public_media(video):
    path = Path(video.source.path)

    assert path.is_relative_to(settings.PRIVATE_MEDIA_ROOT)
    assert not path.is_relative_to(settings.MEDIA_ROOT)
    assert path.suffix == ".mov"
    assert "IMG" not in path.name
    with pytest.raises(ValueError):
        video.source.url  # noqa: B018


def test_new_source_puts_video_back_in_queue(
    video, django_capture_on_commit_callbacks
):
    make_ready(video)
    old_files = [
        Path(video.source.path),
        Path(video.video.path),
        Path(video.poster.path),
    ]

    with django_capture_on_commit_callbacks(execute=True):
        video.source = clip("new.mp4")
        video.save()

    assert video.status == Status.PENDING
    assert not video.video
    assert not video.poster
    assert video.width is None
    assert not any(path.exists() for path in old_files)


def test_deleted_video_files_are_removed(
    video, django_capture_on_commit_callbacks
):
    make_ready(video)
    files = [
        Path(video.source.path),
        Path(video.video.path),
        Path(video.poster.path),
    ]

    with django_capture_on_commit_callbacks(execute=True):
        video.delete()

    assert not any(path.exists() for path in files)


def test_video_upload_rejects_other_files(db):
    video = PortfolioVideo(
        title="Ролик", source=SimpleUploadedFile("run.exe", b"MZ")
    )

    with pytest.raises(ValidationError) as error:
        video.full_clean()

    assert "source" in error.value.message_dict


@override_settings(VIDEO_MAX_UPLOAD_MB=0)
def test_video_upload_size_is_limited(db):
    video = PortfolioVideo(title="Ролик", source=clip())

    with pytest.raises(ValidationError, match="больше 0 МБ"):
        video.full_clean()


def test_index_shows_only_ready_videos(client, video):
    make_ready(video)
    PortfolioVideo.objects.create(title="Ещё не готов", source=clip())
    hidden = make_ready(
        PortfolioVideo.objects.create(title="Снят с сайта", source=clip())
    )
    hidden.is_published = False
    hidden.save()

    html = client.get(reverse("studio:index")).content.decode()

    assert video.video.url in html
    assert video.poster.url in html
    assert 'width="540" height="960"' in html
    assert "Ещё не готов" not in html
    assert "Снят с сайта" not in html


def test_index_shows_photos_with_lazy_thumbnails(client, photo):
    html = client.get(reverse("studio:index")).content.decode()

    assert photo.thumbnail.url in html
    assert photo.image.url in html
    assert 'loading="lazy"' in html
    assert 'alt="Кератин"' in html


def test_photo_filter_needs_several_services(client, service, photo):
    html = client.get(reverse("studio:index")).content.decode()
    assert "portfolio-filter" not in html

    botox = Service.objects.create(
        title="Ботокс", menu_title="Ботокс", slug="botox", teaser="", body=""
    )
    PortfolioPhoto.objects.create(service=botox, image=jpeg())
    html = client.get(reverse("studio:index")).content.decode()

    assert 'data-filter="keratin"' in html
    assert 'data-filter="botox"' in html


def test_site_does_not_depend_on_youtube(client, video):
    make_ready(video)
    response = client.get(reverse("studio:index"))

    assert "youtube" not in response.content.decode()
    assert "youtube" not in response["Content-Security-Policy"]


def test_portfolio_filter_includes_video_services(client, photo, video):
    botox = Service.objects.create(
        title="Ботокс", menu_title="Ботокс", slug="botox", teaser=""
    )
    video.service = botox
    make_ready(video)

    html = client.get(reverse("studio:index")).content.decode()

    assert 'data-filter="keratin"' in html
    assert 'data-filter="botox"' in html
    assert 'class="video-card" data-service="botox"' in html
    assert html.index('class="portfolio-filter"') < html.index(
        'class="video-strip"'
    )


ADMIN_PAGES = [
    "admin:studio_portfoliophoto_changelist",
    "admin:studio_portfoliophoto_add",
    "admin:studio_portfoliovideo_changelist",
    "admin:studio_portfoliovideo_add",
]


@pytest.mark.parametrize("url_name", ADMIN_PAGES)
def test_portfolio_admin_pages_open(admin_client, photo, video, url_name):
    make_ready(video)

    assert admin_client.get(reverse(url_name)).status_code == 200


def test_admin_upload_puts_video_in_queue(admin_client):
    response = admin_client.post(
        reverse("admin:studio_portfoliovideo_add"),
        {"title": "Нанопластика", "source": clip(), "order": 0},
    )

    video = PortfolioVideo.objects.get()
    assert response.status_code == 302
    assert video.status == Status.PENDING
    messages = [str(m) for m in get_messages(response.wsgi_request)]
    assert any("очередь" in message for message in messages)


def test_admin_does_not_link_to_video_source(admin_client, video):
    url = reverse("admin:studio_portfoliovideo_change", args=[video.pk])
    html = admin_client.get(url).content.decode()

    assert video.source.name not in html
    assert "Ждёт обработки" in html


def test_admin_shows_processing_error(admin_client, video):
    video.status = Status.FAILED
    video.error = "Ролик длиннее 180 секунд, сократите его."
    video.save()

    html = admin_client.get(
        reverse("admin:studio_portfoliovideo_changelist")
    ).content.decode()

    assert "Ошибка: Ролик длиннее 180 секунд" in html


def test_admin_action_requeues_videos(admin_client, video):
    video.status = Status.FAILED
    video.error = "Файл не удалось обработать."
    video.save()

    admin_client.post(
        reverse("admin:studio_portfoliovideo_changelist"),
        {"action": "process_again", "_selected_action": [video.pk]},
    )

    video.refresh_from_db()
    assert video.status == Status.PENDING
    assert video.error == ""
