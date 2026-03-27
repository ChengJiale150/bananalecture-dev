from __future__ import annotations

import base64
import shutil
import subprocess
from pathlib import Path

import pytest

from bananalecture_backend.core.config import Settings
from bananalecture_backend.infrastructure.audio_processing import AudioProcessingService
from bananalecture_backend.infrastructure.video_processing import VideoProcessingService

FFMPEG_BIN = shutil.which("ffmpeg")
FFPROBE_BIN = shutil.which("ffprobe")

pytestmark = pytest.mark.skipif(
    FFMPEG_BIN is None or FFPROBE_BIN is None,
    reason="ffmpeg/ffprobe are required for media processing tests",
)

TEST_PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO7Z0xQAAAAASUVORK5CYII="
)


def _run_command(args: list[str]) -> None:
    subprocess.run(args, check=True, capture_output=True, text=True)


def _write_test_png(path: Path) -> None:
    path.write_bytes(TEST_PNG_BYTES)


def _create_sine_mp3(path: Path, *, channels: int, sample_rate: int = 32000, duration: float = 0.6) -> None:
    channel_layout = "stereo" if channels == 2 else "mono"
    _run_command(
        [
            FFMPEG_BIN or "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=880:sample_rate={sample_rate}:duration={duration}",
            "-ac",
            str(channels),
            "-ar",
            str(sample_rate),
            "-c:a",
            "libmp3lame",
            "-b:a",
            "128k",
            "-channel_layout",
            channel_layout,
            str(path),
        ]
    )


def _probe_audio_channels(path: Path) -> int:
    result = subprocess.run(
        [
            FFPROBE_BIN or "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=channels",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return int(result.stdout.strip())


def _probe_audio_sample_rate(path: Path) -> int:
    result = subprocess.run(
        [
            FFPROBE_BIN or "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=sample_rate",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return int(result.stdout.strip())


def _decode_media(path: Path) -> None:
    _run_command(
        [
            FFMPEG_BIN or "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(path),
            "-f",
            "null",
            "-",
        ]
    )


def test_audio_processing_normalizes_concatenated_output_to_stereo(tmp_path: Path, test_settings: Settings) -> None:
    first_mono_input = tmp_path / "first-mono.mp3"
    second_mono_input = tmp_path / "second-mono.mp3"
    output = tmp_path / "merged.mp3"

    _create_sine_mp3(first_mono_input, channels=1, sample_rate=32000)
    _create_sine_mp3(second_mono_input, channels=1, sample_rate=32000)

    service = AudioProcessingService(test_settings)

    import asyncio

    asyncio.run(service.concatenate_mp3_files([first_mono_input, second_mono_input], output))

    assert _probe_audio_channels(output) == 2
    assert _probe_audio_sample_rate(output) == test_settings.AUDIO_GENERATION.SAMPLE_RATE


def test_video_processing_normalizes_clip_and_concat_audio_to_stereo(
    tmp_path: Path,
    test_settings: Settings,
) -> None:
    first_image = tmp_path / "first.png"
    second_image = tmp_path / "second.png"
    first_audio = tmp_path / "first.mp3"
    second_audio = tmp_path / "second.mp3"
    first_clip = tmp_path / "001.mp4"
    second_clip = tmp_path / "002.mp4"
    output = tmp_path / "project-video.mp4"

    _write_test_png(first_image)
    _write_test_png(second_image)
    _create_sine_mp3(first_audio, channels=2)
    _create_sine_mp3(second_audio, channels=1)

    service = VideoProcessingService(test_settings)

    import asyncio

    asyncio.run(service.render_static_slide_clip(first_image, first_audio, first_clip))
    asyncio.run(service.render_static_slide_clip(second_image, second_audio, second_clip))
    asyncio.run(service.concatenate_mp4_files([first_clip, second_clip], output))

    assert _probe_audio_channels(first_clip) == 2
    assert _probe_audio_channels(second_clip) == 2
    assert _probe_audio_channels(output) == 2
    assert _probe_audio_sample_rate(output) == test_settings.AUDIO_GENERATION.SAMPLE_RATE
    _decode_media(output)
