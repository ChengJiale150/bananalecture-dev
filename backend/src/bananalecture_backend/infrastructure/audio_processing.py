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


class AudioProcessingService:
    """ffmpeg-backed audio processing operations."""

    def __init__(self, settings: Settings) -> None:
        """Store immutable output settings."""
        self.settings = settings.AUDIO_GENERATION

    async def concatenate_mp3_files(self, inputs: Sequence[Path], output: Path) -> None:
        """Concatenate input mp3 files into a single output file."""
        paths = list(inputs)
        if not paths:
            message = "Audio concat inputs must not be empty"
            raise ExternalServiceError(message)
        await asyncio.to_thread(self._concatenate_sync, paths, output)

    def _concatenate_sync(self, inputs: list[Path], output: Path) -> None:
        for path in inputs:
            if not path.exists():
                message = f"Audio input file not found: {path}"
                raise ExternalServiceError(message)

        output.parent.mkdir(parents=True, exist_ok=True)
        manifest_path = self._write_manifest(output.parent, inputs)
        try:
            stream = ffmpeg.input(str(manifest_path), format="concat", safe=0)
            stream = ffmpeg.output(
                stream,
                str(output),
                acodec="libmp3lame",
                audio_bitrate=str(self.settings.BITRATE),
                ac=self.settings.CHANNELS,
                ar=self.settings.SAMPLE_RATE,
                format=self.settings.FORMAT,
                vn=None,
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


def build_audio_processing_service(settings: Settings) -> AudioProcessingService:
    """Build an audio processing service from application settings."""
    return AudioProcessingService(settings)
