from __future__ import annotations

import base64
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from bananalecture_backend.core.config import Settings
from bananalecture_backend.infrastructure.audio_processing import AudioProcessingService
from bananalecture_backend.infrastructure.image_processing import ImageProcessingService
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


def _create_sine_mp3(
    path: Path,
    *,
    channels: int,
    sample_rate: int = 32000,
    duration: float = 0.6,
    volume_db: float = 0.0,
) -> None:
    channel_layout = "stereo" if channels == 2 else "mono"
    args = [
        FFMPEG_BIN or "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "lavfi",
        "-i",
        f"sine=frequency=880:sample_rate={sample_rate}:duration={duration}",
    ]
    if volume_db:
        args += ["-af", f"volume={volume_db}dB"]
    args += [
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
    _run_command(args)


def _create_silent_mp3(path: Path, *, duration: float = 2.0) -> None:
    _run_command(
        [
            FFMPEG_BIN or "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=32000",
            "-t",
            str(duration),
            "-c:a",
            "libmp3lame",
            "-b:a",
            "128k",
            str(path),
        ]
    )


_LOUDNESS_PATTERN = re.compile(r"I:\s+(-?\d+(?:\.\d+)?)\s+LUFS")
_TRUE_PEAK_PATTERN = re.compile(r"Peak:\s+(-?\d+(?:\.\d+)?)\s+dBFS")
_MAX_VOLUME_PATTERN = re.compile(r"max_volume:\s+(-?\d+(?:\.\d+)?)\s+dB")


def _probe_loudness(path: Path) -> tuple[float, float]:
    """Return integrated loudness (LUFS) and true peak (dBFS) for one audio file."""
    result = subprocess.run(
        [
            FFMPEG_BIN or "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-i",
            str(path),
            "-filter_complex",
            "ebur128=peak=true",
            "-f",
            "null",
            "-",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    loudness = _LOUDNESS_PATTERN.findall(result.stderr)
    true_peak = _TRUE_PEAK_PATTERN.search(result.stderr)
    assert loudness, result.stderr
    assert true_peak is not None, result.stderr
    return float(loudness[-1]), float(true_peak.group(1))


def _probe_max_volume_db(path: Path) -> float:
    result = subprocess.run(
        [
            FFMPEG_BIN or "ffmpeg",
            "-hide_banner",
            "-i",
            str(path),
            "-af",
            "volumedetect",
            "-f",
            "null",
            "-",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    match = _MAX_VOLUME_PATTERN.search(result.stderr)
    assert match is not None, result.stderr
    return float(match.group(1))


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


@pytest.mark.asyncio
async def test_image_preprocessing_resizes_and_pads_to_exact_dimensions(tmp_path: Path) -> None:
    service = ImageProcessingService()
    target_width = 320
    target_height = 240
    input_path = tmp_path / "input.png"
    output_path = tmp_path / "output.jpg"

    from PIL import Image

    # Create a small 100x100 test image
    original = Image.new("RGB", (100, 100), (255, 0, 0))
    original.save(input_path)

    await service.resize_image(input_path, output_path, target_width, target_height)

    assert output_path.exists()

    with Image.open(output_path) as result:
        assert result.width == target_width
        assert result.height == target_height
        # Image should be centered on black background
        # Check that corners are black (padded) and center is red
        center_pixel = result.getpixel((target_width // 2, target_height // 2))
        assert center_pixel[0] > 250 and center_pixel[1] == 0, f"Expected red center, got {center_pixel}"
        corner_pixel = result.getpixel((0, 0))
        assert corner_pixel == (0, 0, 0), f"Expected black corner, got {corner_pixel}"


@pytest.mark.asyncio
async def test_image_preprocessing_with_large_input(tmp_path: Path) -> None:
    service = ImageProcessingService()
    target_width = 320
    target_height = 240
    input_path = tmp_path / "input.png"
    output_path = tmp_path / "output.jpg"

    from PIL import Image

    # Create a large 4000x2000 test image (simulating wide 4K image)
    original = Image.new("RGB", (4000, 2000), (0, 255, 0))
    original.save(input_path)

    await service.resize_image(input_path, output_path, target_width, target_height)

    assert output_path.exists()

    with Image.open(output_path) as result:
        assert result.width == target_width
        assert result.height == target_height
        # Image should be letterboxed (padded top/bottom) since input is wider
        # The green area should be centered horizontally
        center_pixel = result.getpixel((target_width // 2, target_height // 2))
        assert center_pixel[1] > 250 and center_pixel[0] == 0, f"Expected green center, got {center_pixel}"


@pytest.mark.asyncio
async def test_audio_processing_normalizes_loudness_to_configured_target(
    tmp_path: Path,
    test_settings: Settings,
) -> None:
    loud_input = tmp_path / "loud.mp3"
    quiet_input = tmp_path / "quiet.mp3"
    loud_output = tmp_path / "loud-normalized.mp3"
    quiet_output = tmp_path / "quiet-normalized.mp3"

    # Simulate the real defect: one speaker rendered far louder than another.
    _create_sine_mp3(loud_input, channels=2, duration=2.0, volume_db=-6.0)
    _create_sine_mp3(quiet_input, channels=2, duration=2.0, volume_db=-30.0)

    service = AudioProcessingService(test_settings)
    await service.normalize_loudness(loud_input, loud_output)
    await service.normalize_loudness(quiet_input, quiet_output)

    normalization = test_settings.AUDIO_GENERATION.NORMALIZATION
    loud_lufs, loud_peak = _probe_loudness(loud_output)
    quiet_lufs, quiet_peak = _probe_loudness(quiet_output)

    assert loud_lufs == pytest.approx(normalization.TARGET_LUFS, abs=1.0)
    assert quiet_lufs == pytest.approx(normalization.TARGET_LUFS, abs=1.0)
    assert abs(loud_lufs - quiet_lufs) < 1.0
    assert loud_peak <= normalization.TARGET_TRUE_PEAK_DBTP + 0.5
    assert quiet_peak <= normalization.TARGET_TRUE_PEAK_DBTP + 0.5
    assert _probe_audio_channels(loud_output) == 2
    assert _probe_audio_sample_rate(loud_output) == test_settings.AUDIO_GENERATION.SAMPLE_RATE


@pytest.mark.asyncio
async def test_audio_processing_normalization_keeps_silence_silent(
    tmp_path: Path,
    test_settings: Settings,
) -> None:
    silent_input = tmp_path / "silent.mp3"
    output = tmp_path / "silent-normalized.mp3"

    _create_silent_mp3(silent_input)

    service = AudioProcessingService(test_settings)
    await service.normalize_loudness(silent_input, output)

    assert output.exists()
    _decode_media(output)
    # An unmeasurable (silent) input must not be amplified into noise.
    assert _probe_max_volume_db(output) <= -60.0
