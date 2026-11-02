import json
import shutil
import subprocess
from pathlib import Path

import pytest
from django.conf import settings
from django.core.files import File
from django.core.management import call_command
from PIL import Image

from core import video as video_module
from core.video import (
    ConvertedVideo,
    VideoError,
    VideoInfo,
    convert,
    probe,
    run,
    transcode_args,
)
from studio.models import PortfolioVideo

Status = PortfolioVideo.Status
COMMAND = "studio.management.commands.process_videos"
MP4 = "mov,mp4,m4a,3gp,3g2,mj2"


def probe_output(format_name=MP4, duration="12.5", streams=None):
    container = {"format_name": format_name}
    if duration is not None:
        container["duration"] = duration
    if streams is None:
        streams = [
            {"codec_type": "video", "color_transfer": "bt709"},
            {"codec_type": "audio"},
        ]
    return json.dumps({"format": container, "streams": streams}).encode()


def fake_run(stdout):
    calls = []

    def run(args, timeout):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, stdout=stdout, stderr=b"")

    return run, calls


def test_probe_accepts_mp4_and_reads_only_local_files(monkeypatch):
    run, calls = fake_run(probe_output())
    monkeypatch.setattr(video_module, "run", run)

    info = probe("clip.mp4")

    assert info == VideoInfo(demuxer="mov", duration=12.5, is_hdr=False)
    args = calls[0]
    assert args[args.index("-protocol_whitelist") + 1] == "file"
    assert args[args.index("-format_whitelist") + 1] == "matroska,mov"


@pytest.mark.parametrize(
    ("output", "message"),
    [
        (probe_output(format_name="hls"), "Формат не поддерживается"),
        (probe_output(streams=[{"codec_type": "audio"}]), "нет видео"),
        (probe_output(duration=None), "длительность"),
        (probe_output(duration="181"), "длиннее 180 секунд"),
        (b"not json", "Не удалось прочитать"),
    ],
)
def test_probe_rejects_unsuitable_files(monkeypatch, output, message):
    monkeypatch.setattr(video_module, "run", fake_run(output)[0])

    with pytest.raises(VideoError, match=message):
        probe("clip.mp4")


def test_hdr_video_is_tone_mapped(monkeypatch):
    streams = [{"codec_type": "video", "color_transfer": "arib-std-b67"}]
    monkeypatch.setattr(
        video_module, "run", fake_run(probe_output(streams=streams))[0]
    )

    info = probe("iphone.mov")
    args = transcode_args("iphone.mov", "out.mp4", info)

    assert info.is_hdr
    assert "tonemap" in args[args.index("-vf") + 1]


def test_transcode_forces_demuxer_and_strips_metadata():
    info = VideoInfo(demuxer="matroska", duration=10, is_hdr=False)
    args = transcode_args("in.webm", "out.mp4", info)

    assert args[args.index("-f") + 1] == "matroska"
    assert args[args.index("-map_metadata") + 1] == "-1"
    assert args[args.index("-movflags") + 1] == "+faststart"
    assert "tonemap" not in args[args.index("-vf") + 1]


def test_convert_makes_video_and_poster(monkeypatch, tmp_path):
    run, calls = fake_run(probe_output(duration="0.6"))
    monkeypatch.setattr(video_module, "run", run)

    converted = convert("clip.mp4", tmp_path)

    assert converted.video == tmp_path / "video.mp4"
    assert converted.poster == tmp_path / "poster.png"
    poster_args = calls[2]
    assert poster_args[poster_args.index("-ss") + 1] == "0.30"


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (FileNotFoundError(), "Не найдена программа"),
        (subprocess.TimeoutExpired("ffmpeg", 1), "слишком много времени"),
        (
            subprocess.CalledProcessError(
                1, "ffmpeg", stderr=b"first\nInvalid data found"
            ),
            "Invalid data found$",
        ),
    ],
)
def test_run_reports_failures(monkeypatch, error, message):
    def broken(*args, **kwargs):
        raise error

    monkeypatch.setattr(subprocess, "run", broken)

    with pytest.raises(VideoError, match=message):
        run(["ffmpeg"], timeout=1)


def poster_png(path):
    Image.new("RGB", (720, 1280), "pink").save(path)
    return path


@pytest.fixture
def queued(transactional_db, tmp_path):
    # Обработчик закрывает старые соединения: внешняя транзакция не нужна.
    source = tmp_path / "phone.mp4"
    source.write_bytes(b"fake video")
    with source.open("rb") as file:
        return PortfolioVideo.objects.create(
            title="Кератин на блонд", source=File(file, name="phone.mp4")
        )


@pytest.fixture
def fake_convert(monkeypatch):
    def convert(source, workdir):
        video = Path(workdir) / "video.mp4"
        video.write_bytes(b"mp4")
        poster = poster_png(Path(workdir) / "poster.png")
        return ConvertedVideo(video=video, poster=poster, duration=12.4)

    monkeypatch.setattr(f"{COMMAND}.convert", convert)


def test_worker_makes_video_ready(queued, fake_convert):
    call_command("process_videos")

    queued.refresh_from_db()
    assert queued.status == Status.READY
    assert queued.video.name.startswith("portfolio/videos/")
    assert queued.poster.name.endswith(".webp")
    assert (queued.width, queued.height) == (540, 960)
    assert queued.duration == 12


def test_worker_records_error(queued, monkeypatch):
    def convert(source, workdir):
        raise VideoError("Формат не поддерживается.")

    monkeypatch.setattr(f"{COMMAND}.convert", convert)

    call_command("process_videos")

    queued.refresh_from_db()
    assert queued.status == Status.FAILED
    assert queued.error == "Формат не поддерживается."


def test_worker_survives_unexpected_error(queued, monkeypatch, capsys):
    def convert(source, workdir):
        raise RuntimeError("disk is full")

    monkeypatch.setattr(f"{COMMAND}.convert", convert)

    call_command("process_videos")

    queued.refresh_from_db()
    assert queued.status == Status.FAILED
    assert "журнале" in queued.error
    assert "disk is full" not in queued.error


def test_worker_drops_result_when_source_replaced(queued, monkeypatch, capsys):
    calls = []

    def convert(source, workdir):
        calls.append(source)
        if len(calls) == 1:
            # Мастер загрузил другой файл, пока шло перекодирование.
            PortfolioVideo.objects.filter(pk=queued.pk).update(
                source="videos/other.mp4", status=Status.PENDING
            )
        video = Path(workdir) / "video.mp4"
        video.write_bytes(b"mp4")
        poster = poster_png(Path(workdir) / "poster.png")
        return ConvertedVideo(video=video, poster=poster, duration=3)

    monkeypatch.setattr(f"{COMMAND}.convert", convert)

    call_command("process_videos")

    queued.refresh_from_db()
    assert "пропущен" in capsys.readouterr().out
    assert len(calls) == 2
    assert queued.source.name == "videos/other.mp4"
    assert queued.status == Status.READY


def test_worker_restarts_interrupted_processing(queued, fake_convert, capsys):
    queued.status = Status.PROCESSING
    queued.save()

    call_command("process_videos")

    queued.refresh_from_db()
    assert queued.status == Status.READY
    assert "Возвращено в очередь: 1" in capsys.readouterr().out


def test_watch_mode_waits_for_new_videos(transactional_db, monkeypatch):
    class Stop(Exception):
        pass

    def sleep(seconds):
        assert seconds == 0.5
        raise Stop

    monkeypatch.setattr(f"{COMMAND}.time.sleep", sleep)

    with pytest.raises(Stop):
        call_command("process_videos", "--watch", "--interval", "0.5")


FFMPEG = shutil.which(settings.FFMPEG_BINARY)
FFPROBE = shutil.which(settings.FFPROBE_BINARY)
needs_ffmpeg = pytest.mark.skipif(
    not (FFMPEG and FFPROBE), reason="нужны ffmpeg и ffprobe"
)


def make_clip(path, *options):
    subprocess.run(  # noqa: S603
        [
            FFMPEG,
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc=duration=2:size=1080x1920:rate=60",
            "-f",
            "lavfi",
            "-i",
            "sine=duration=2",
            *options,
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            "-shortest",
            str(path),
        ],
        check=True,
    )
    return path


def stream_info(path):
    result = subprocess.run(  # noqa: S603
        [
            FFPROBE,
            "-v",
            "error",
            "-show_entries",
            "stream=codec_name,width,height,r_frame_rate:format_tags",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        check=True,
    )
    return json.loads(result.stdout)


@needs_ffmpeg
def test_real_video_is_converted(tmp_path):
    source = make_clip(
        tmp_path / "phone.mov", "-metadata", "location=+55.7+037.6/"
    )

    converted = convert(source, tmp_path)

    info = stream_info(converted.video)
    video, audio = info["streams"]
    assert (video["codec_name"], video["width"], video["height"]) == (
        "h264",
        720,
        1280,
    )
    assert video["r_frame_rate"] == "30/1"
    assert audio["codec_name"] == "aac"
    assert "location" not in json.dumps(info.get("format", {}))
    with Image.open(converted.poster) as poster:
        assert poster.size == (720, 1280)


@needs_ffmpeg
def test_real_hdr_video_is_converted(tmp_path):
    source = make_clip(
        tmp_path / "iphone.mov",
        "-vf",
        "format=yuv420p,setparams=color_primaries=bt2020:"
        "color_trc=arib-std-b67:colorspace=bt2020nc",
    )

    assert probe(source).is_hdr
    assert convert(source, tmp_path).video.exists()


@needs_ffmpeg
def test_playlist_disguised_as_video_is_rejected(tmp_path):
    secret = tmp_path / "secret.txt"
    secret.write_text("password")
    fake = tmp_path / "clip.mp4"
    fake.write_text(
        "\n".join(
            [
                "#EXTM3U",
                "#EXT-X-MEDIA-SEQUENCE:0",
                "#EXTINF:10.0,",
                secret.as_uri(),
                "#EXT-X-ENDLIST",
            ]
        )
    )

    with pytest.raises(VideoError):
        convert(fake, tmp_path)


@needs_ffmpeg
def test_worker_processes_real_upload(transactional_db, tmp_path):
    source = make_clip(tmp_path / "phone.mp4")
    with source.open("rb") as file:
        video = PortfolioVideo.objects.create(
            title="Кератин", source=File(file, name="phone.mp4")
        )

    call_command("process_videos")

    video.refresh_from_db()
    assert video.status == Status.READY, video.error
    assert (video.width, video.height) == (540, 960)
    assert video.duration == 2
