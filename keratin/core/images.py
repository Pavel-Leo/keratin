"""Перекодирование загруженных фото в WebP.

Файл открывается Pillow и сохраняется заново: из него пропадают EXIF
(в том числе геометка телефона) и любые данные, не относящиеся к картинке.
Имя файла заменяется случайным.
"""

import uuid
from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_PIXELS = 50_000_000
WEBP_QUALITY = 82


def to_webp(file, max_side):
    file.seek(0)
    try:
        with Image.open(file) as image:
            if image.width * image.height > MAX_PIXELS:
                raise ValidationError("Слишком большое изображение.")
            image = ImageOps.exif_transpose(image)
            has_alpha = image.mode in {"RGBA", "LA"} or (
                image.mode == "P" and "transparency" in image.info
            )
            image = image.convert("RGBA" if has_alpha else "RGB")
            image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
            buffer = BytesIO()
            image.save(buffer, "WEBP", quality=WEBP_QUALITY, method=6)
    except (UnidentifiedImageError, OSError) as error:
        raise ValidationError("Файл не похож на изображение.") from error
    return ContentFile(buffer.getvalue(), name=f"{uuid.uuid4().hex}.webp")
