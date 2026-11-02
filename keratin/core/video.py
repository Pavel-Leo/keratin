"""Перекодирование роликов, загруженных через админку.

Загруженный файл считается недоверенным. ffprobe и ffmpeg читают только
локальные файлы и только разрешёнными демультиплексорами: плейлист или
другой контейнер, переименованный в .mp4, отклоняется до декодирования.
Результат: MP4 (H.264 + AAC) не больше 1280 px по длинной стороне,
без метаданных и геометки, с индексом в начале файла, чтобы ролик
начинал играть до полной загрузки.
"""

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings

# Имя контейнера в ответе ffprobe и демультиплексор для ffmpeg.
DEMUXERS = {
    "mov,mp4,m4a,3gp,3g2,mj2": "mov",
    "matroska,webm": "matroska",
}
INPUT_GUARD = [
    "-protocol_whitelist",
    "file",
    "-format_whitelist",
    ",".join(sorted(set(DEMUXERS.values()))),
]
HDR_TRANSFERS = {"arib-std-b67", "smpte2084"}
MAX_SIDE = 1280
MAX_FPS = 30
PROBE_TIMEOUT = 60

SCALE = (
    f"scale=w='min({MAX_SIDE},iw)':h='min({MAX_SIDE},ih)'"
    ":force_original_aspect_ratio=decrease:force_divisible_by=2"
)
# HDR с iPhone и части Android без перевода в SDR выглядит блёклым.
TONEMAP = (
    "zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,"
    "tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv"
)


class VideoError(Exception):
    """Файл нельзя обработать. Текст показывается мастеру в админке."""


@dataclass(frozen=True)
class VideoInfo:
    demuxer: str
    duration: float
    is_hdr: bool


@dataclass(frozen=True)
class ConvertedVideo:
    video: Path
    poster: Path
    duration: float


def run(args, timeout):
    try:
        # Без оболочки, аргументы списком; имена файлов задаёт сервер.
        return subprocess.run(  # noqa: S603
            args,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=timeout,
            check=True,
        )
    except FileNotFoundError as error:
        raise VideoError(f"Не найдена программа {args[0]}.") from error
    except subprocess.TimeoutExpired as error:
        raise VideoError("Обработка заняла слишком много времени.") from error
    except subprocess.CalledProcessError as error:
        lines = error.stderr.decode(errors="replace").strip().splitlines()
        detail = lines[-1] if lines else f"код {error.returncode}"
        raise VideoError(f"Файл не удалось обработать: {detail}") from error


def probe(path):
    result = run(
        [
            settings.FFPROBE_BINARY,
            "-v",
            "error",
            *INPUT_GUARD,
            "-show_entries",
            "format=format_name,duration:stream=codec_type,color_transfer",
            "-of",
            "json",
            str(path),
        ],
        PROBE_TIMEOUT,
    )
    try:
        data = json.loads(result.stdout)
        container = data["format"]
        streams = data.get("streams", [])
    except (ValueError, KeyError, TypeError) as error:
        raise VideoError("Не удалось прочитать файл.") from error

    demuxer = DEMUXERS.get(container.get("format_name"))
    if demuxer is None:
        raise VideoError("Формат не поддерживается. Нужен MP4, MOV или WebM.")
    video_streams = [s for s in streams if s.get("codec_type") == "video"]
    if not video_streams:
        raise VideoError("В файле нет видео.")
    try:
        duration = float(container["duration"])
    except (KeyError, ValueError) as error:
        raise VideoError("Не удалось определить длительность.") from error
    if duration > settings.VIDEO_MAX_SECONDS:
        raise VideoError(
            f"Ролик длиннее {settings.VIDEO_MAX_SECONDS} секунд, "
            "сократите его."
        )
    is_hdr = video_streams[0].get("color_transfer") in HDR_TRANSFERS
    return VideoInfo(demuxer=demuxer, duration=duration, is_hdr=is_hdr)


def transcode_args(source, target, info):
    filters = [TONEMAP, SCALE] if info.is_hdr else [SCALE]
    return [
        settings.FFMPEG_BINARY,
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        *INPUT_GUARD,
        "-f",
        info.demuxer,
        "-i",
        str(source),
        "-map",
        "0:v:0",
        "-map",
        "0:a:0?",
        "-t",
        str(settings.VIDEO_MAX_SECONDS),
        "-vf",
        ",".join([*filters, "format=yuv420p"]),
        "-fpsmax",
        str(MAX_FPS),
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "23",
        "-profile:v",
        "high",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-ac",
        "2",
        "-map_metadata",
        "-1",
        "-map_chapters",
        "-1",
        "-movflags",
        "+faststart",
        "-y",
        str(target),
    ]


def poster_args(video, target, duration):
    position = min(1.0, duration / 2)
    return [
        settings.FFMPEG_BINARY,
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        *INPUT_GUARD,
        "-f",
        "mov",
        "-ss",
        f"{position:.2f}",
        "-i",
        str(video),
        "-frames:v",
        "1",
        "-y",
        str(target),
    ]


def convert(source, workdir):
    """Проверяет исходник и готовит MP4 и кадр для обложки в workdir."""
    workdir = Path(workdir)
    info = probe(source)
    video = workdir / "video.mp4"
    poster = workdir / "poster.png"
    run(transcode_args(source, video, info), settings.VIDEO_TIMEOUT_SECONDS)
    run(poster_args(video, poster, info.duration), PROBE_TIMEOUT)
    return ConvertedVideo(video=video, poster=poster, duration=info.duration)
