from io import BytesIO
from pathlib import Path

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from core.images import to_webp


def jpeg_with_exif(size=(2400, 1200)):
    image = Image.new("RGB", size, "pink")
    exif = Image.Exif()
    exif[0x010F] = "Phone maker"
    buffer = BytesIO()
    image.save(buffer, "JPEG", exif=exif)
    return SimpleUploadedFile(
        "IMG_2024 my photo.jpg", buffer.getvalue(), "image/jpeg"
    )


def test_to_webp_resizes_and_strips_metadata():
    converted = to_webp(jpeg_with_exif(), max_side=1600)

    with Image.open(converted) as image:
        assert image.format == "WEBP"
        assert image.size == (1600, 800)
        assert not image.getexif()
    assert converted.name.endswith(".webp")
    assert "photo" not in converted.name


def test_to_webp_rejects_non_images():
    fake = SimpleUploadedFile("photo.jpg", b"<?php echo 1; ?>", "image/jpeg")

    with pytest.raises(ValidationError):
        to_webp(fake, max_side=1600)


@pytest.mark.django_db
def test_model_image_is_converted_on_save(service):
    service.image = jpeg_with_exif()
    service.save()

    assert service.image.name.startswith("services/")
    assert service.image.name.endswith(".webp")
    assert (service.image_width, service.image_height) == (1600, 800)


@pytest.mark.django_db
def test_old_image_is_deleted_when_replaced_or_removed(
    service, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        service.image = jpeg_with_exif()
        service.save()
    first = Path(service.image.path)

    with django_capture_on_commit_callbacks(execute=True):
        service.image = jpeg_with_exif()
        service.save()
    second = Path(service.image.path)

    assert not first.exists()
    assert second.exists()

    with django_capture_on_commit_callbacks(execute=True):
        service.delete()

    assert not second.exists()
