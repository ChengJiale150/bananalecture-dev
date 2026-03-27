from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import ffmpeg  # type: ignore[import-untyped]

from bananalecture_backend.core.errors import ConfigurationError, ExternalServiceError

if TYPE_CHECKING:
    from collections.abc import Sequence

    from bananalecture_backend.core.config import Settings


class VideoProcessingService:
    """ffmpeg-backed video processing operations."""

    def __init__(self, settings: Settings) -> None:
        """Store immutable output settings."""
        self.settings = settings.VIDEO_GENERATION

    async def render_static_slide_clip(self, image: Path, audio: Path, output: Path) -> None:
        """Render a single slide clip from one image and one audio file."""
        await asyncio.to_thread(self._render_static_slide_clip_sync, image, audio, output)

    async def concatenate_mp4_files(self, inputs: Sequence[Path], output: Path) -> None:
        """Concatenate slide clips into a single project video."""
        paths = list(inputs)
        if not paths:
            message = "Video concat inputs must not be empty"
            raise ExternalServiceError(message)
        await asyncio.to_thread(self._concatenate_sync, paths, output)

    def _render_static_slide_clip_sync(self, image: Path, audio: Path, output: Path) -> None:
        if not image.exists():
            message = f"Video input image not found: {image}"
            raise ExternalServiceError(message)
        if not audio.exists():
            message = f"Video input audio not found: {audio}"
            raise ExternalServiceError(message)

        output.parent.mkdir(parents=True, exist_ok=True)

        try:
            image_stream = ffmpeg.input(str(image), loop=1, framerate=self.settings.FPS)
            audio_stream = ffmpeg.input(str(audio))
            video_stream = image_stream.video.filter(
                "scale",
                self.settings.WIDTH,
                self.settings.HEIGHT,
                force_original_aspect_ratio="decrease",
            ).filter(
                "pad",
                self.settings.WIDTH,
                self.settings.HEIGHT,
                "(ow-iw)/2",
                "(oh-ih)/2",
                color=self.settings.BACKGROUND_COLOR,
            )
            stream = ffmpeg.output(
                video_stream,
                audio_stream.audio,
                str(output),
                vcodec=self.settings.VIDEO_CODEC,
                acodec=self.settings.AUDIO_CODEC,
                ac=self.settings.AUDIO_CHANNELS,
                ar=self.settings.AUDIO_SAMPLE_RATE,
                audio_bitrate=str(self.settings.AUDIO_BITRATE),
                pix_fmt=self.settings.PIXEL_FORMAT,
                r=self.settings.FPS,
                shortest=None,
                movflags="+faststart",
            )
            ffmpeg.run(stream, overwrite_output=True, capture_stdout=True, capture_stderr=True)
        except FileNotFoundError as exc:
            message = "ffmpeg is not installed"
            raise ConfigurationError(message) from exc
        except ffmpeg.Error as exc:
            stderr = exc.stderr.decode("utf-8", errors="ignore").strip()
            message = stderr or str(exc)
            error_message = f"ffmpeg failed: {message}"
            raise ExternalServiceError(error_message) from exc

        if not output.exists():
            message = "ffmpeg did not produce an output file"
            raise ExternalServiceError(message)

    def _concatenate_sync(self, inputs: list[Path], output: Path) -> None:
        for path in inputs:
            if not path.exists():
                message = f"Video input file not found: {path}"
                raise ExternalServiceError(message)

        output.parent.mkdir(parents=True, exist_ok=True)
        manifest_path = self._write_manifest(output.parent, inputs)
        try:
            stream = ffmpeg.input(str(manifest_path), format="concat", safe=0)
            stream = ffmpeg.output(
                stream,
                str(output),
                c="copy",
                movflags="+faststart",
            )
            ffmpeg.run(stream, overwrite_output=True, capture_stdout=True, capture_stderr=True)
        except FileNotFoundError as exc:
            message = "ffmpeg is not installed"
            raise ConfigurationError(message) from exc
        except ffmpeg.Error as exc:
            stderr = exc.stderr.decode("utf-8", errors="ignore").strip()
            message = stderr or str(exc)
            error_message = f"ffmpeg failed: {message}"
            raise ExternalServiceError(error_message) from exc
        finally:
            manifest_path.unlink(missing_ok=True)

        if not output.exists():
            message = "ffmpeg did not produce an output file"
            raise ExternalServiceError(message)

    def _write_manifest(self, directory: Path, inputs: list[Path]) -> Path:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".txt",
            prefix="concat-",
            dir=directory,
            encoding="utf-8",
            delete=False,
        ) as manifest:
            for path in inputs:
                escaped = str(path.resolve()).replace("'", r"'\''")
                manifest.write(f"file '{escaped}'\n")
        return Path(manifest.name)


def build_video_processing_service(settings: Settings) -> VideoProcessingService:
    """Build a video processing service from application settings."""
    return VideoProcessingService(settings)
