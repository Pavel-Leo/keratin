import logging
import tempfile
import time
import uuid

from django.core.exceptions import ValidationError
from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import close_old_connections, transaction

from core.video import VideoError, convert
from studio.models import PortfolioVideo

Status = PortfolioVideo.Status
logger = logging.getLogger(__name__)


def claim_next():
    """Берёт из очереди один ролик и помечает, что он в работе."""
    with transaction.atomic():
        video = (
            PortfolioVideo.objects.select_for_update(skip_locked=True)
            .filter(status=Status.PENDING)
            .order_by("pk")
            .first()
        )
        if video is not None:
            video.status = Status.PROCESSING
            video.save(update_fields=["status"])
    return video


def in_progress(video):
    """Тот же ролик с тем же исходником, который всё ещё в работе.

    Если за время обработки мастер заменил файл или удалил ролик,
    результат больше не нужен.
    """
    return PortfolioVideo.objects.filter(
        pk=video.pk, source=video.source.name, status=Status.PROCESSING
    )


def store(video, converted):
    with transaction.atomic():
        current = in_progress(video).select_for_update().first()
        if current is None:
            return False
        with (
            converted.video.open("rb") as video_file,
            converted.poster.open("rb") as poster_file,
        ):
            current.video = File(video_file, name=f"{uuid.uuid4().hex}.mp4")
            current.poster = File(poster_file, name="poster.png")
            current.duration = round(converted.duration)
            current.status = Status.READY
            current.error = ""
            current.save()
    return True


def fail(video, message):
    in_progress(video).update(status=Status.FAILED, error=message)


def process(video):
    """Перекодирует ролик. Возвращает итог для журнала."""
    try:
        with tempfile.TemporaryDirectory(prefix="video-") as workdir:
            converted = convert(video.source.path, workdir)
            if not store(video, converted):
                return "пропущен: файл заменили или удалили"
    except (VideoError, ValidationError) as error:
        message = getattr(error, "message", None) or str(error)
        fail(video, message)
        return f"ошибка: {message}"
    except Exception:
        logger.exception("Не удалось обработать ролик %s", video.pk)
        fail(video, "Внутренняя ошибка, подробности в журнале сервера.")
        return "ошибка, подробности выше"
    return "готов"


class Command(BaseCommand):
    help = (
        "Перекодирует ролики, загруженные в админке. С --watch не "
        "завершается и ждёт новые."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--watch",
            action="store_true",
            help="Работать постоянно, проверяя очередь.",
        )
        parser.add_argument(
            "--interval",
            type=float,
            default=5,
            help="Пауза между проверками очереди, секунды.",
        )

    def handle(self, *args, watch, interval, **options):
        # Обработка, прерванная остановкой процесса, начинается заново.
        restarted = PortfolioVideo.objects.filter(
            status=Status.PROCESSING
        ).update(status=Status.PENDING)
        if restarted:
            self.stdout.write(f"Возвращено в очередь: {restarted}")
        while True:
            close_old_connections()
            video = claim_next()
            if video is None:
                if not watch:
                    return
                time.sleep(interval)
                continue
            self.stdout.write(f"Ролик «{video}»: обработка…")
            self.stdout.write(f"Ролик «{video}»: {process(video)}")
