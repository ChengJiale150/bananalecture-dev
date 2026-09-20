from __future__ import annotations

import asyncio
import json
import math
import re
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import ffmpeg  # type: ignore[import-untyped]

from bananalecture_backend.core.errors import ConfigurationError, ExternalServiceError
from bananalecture_backend.core.logging_config import get_global_logger

if TYPE_CHECKING:
    from collections.abc import Sequence

    from bananalecture_backend.core.config import Settings

global_logger = get_global_logger()

_LOUDNORM_JSON_PATTERN = re.compile(r"\{\s*\"input_i\".*?\}", re.DOTALL)
"""Matches the JSON measurement block loudnorm writes to stderr."""

_REQUIRED_MEASUREMENTS = ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset")
"""Measurements loudnorm must report before a linear second pass is possible."""


class AudioProcessingService:
    """ffmpeg-backed audio processing operations."""

    def __init__(self, settings: Settings) -> None:
        """Store immutable output settings."""
        self.settings = settings.AUDIO_GENERATION

    async def normalize_loudness(self, source: Path, output: Path) -> None:
        """Normalize one audio file to the configured loudness target."""
        await asyncio.to_thread(self._normalize_loudness_sync, source, output)

    async def concatenate_mp3_files(self, inputs: Sequence[Path], output: Path) -> None:
        """Concatenate input mp3 files into a single output file."""
        paths = list(inputs)
        if not paths:
            message = "Audio concat inputs must not be empty"
            raise ExternalServiceError(message)
        await asyncio.to_thread(self._concatenate_sync, paths, output)

    def _normalize_loudness_sync(self, source: Path, output: Path) -> None:
        if not source.exists():
            message = f"Audio input file not found: {source}"
            raise ExternalServiceError(message)

        output.parent.mkdir(parents=True, exist_ok=True)
        measurements = self._measure_loudness(source)
        if measurements is None:
            # Silence and near-silence yield no usable measurement. Normalizing them
            # would drive the gain to infinity and emit NaN samples, so only the
            # container/format normalization is applied.
            global_logger.bind(source=str(source)).warning("audio_loudness_unmeasurable")
            audio_filter = None
        else:
            audio_filter = self._build_loudnorm_filter(measurements)

        self._encode_mp3(source=source, output=output, audio_filter=audio_filter)

        if not output.exists():
            message = "ffmpeg did not produce an output file"
            raise ExternalServiceError(message)

        global_logger.bind(
            source=str(source),
            output=str(output),
            target_lufs=self.settings.NORMALIZATION.TARGET_LUFS,
            measured_lufs=measurements["input_i"] if measurements is not None else None,
        ).info("audio_loudness_normalized")

    def _measure_loudness(self, source: Path) -> dict[str, str] | None:
        """Run the loudnorm analysis pass and return its measurements."""
        if not source.exists():
            message = f"Audio input file not found: {source}"
            raise ExternalServiceError(message)

        try:
            stream = ffmpeg.input(str(source))
            # The null muxer keeps this pass decode-only: handing NaN samples from
            # unmeasurable input to an mp3 encoder aborts inside libmp3lame.
            stream = ffmpeg.output(
                stream,
                "-",
                af=self._build_loudnorm_filter(None, print_format="json"),
                format="null",
            )
            _, stderr = ffmpeg.run(stream, capture_stdout=True, capture_stderr=True)
        except FileNotFoundError as exc:
            message = "ffmpeg is not installed"
            raise ConfigurationError(message) from exc
        except ffmpeg.Error as exc:
            raise self._ffmpeg_error(exc) from exc
        return self._parse_measurements(stderr.decode("utf-8", errors="ignore"))

    def _encode_mp3(self, *, source: Path, output: Path, audio_filter: str | None) -> None:
        """Re-encode one audio file to the configured mp3 format."""
        try:
            stream = ffmpeg.input(str(source))
            output_kwargs: dict[str, object] = {
                "acodec": "libmp3lame",
                "audio_bitrate": str(self.settings.BITRATE),
                "ac": self.settings.CHANNELS,
                "ar": self.settings.SAMPLE_RATE,
                "format": self.settings.FORMAT,
                "vn": None,
            }
            if audio_filter is not None:
                output_kwargs["af"] = audio_filter
            stream = ffmpeg.output(stream, str(output), **output_kwargs)
            ffmpeg.run(stream, overwrite_output=True, capture_stdout=True, capture_stderr=True)
        except FileNotFoundError as exc:
            message = "ffmpeg is not installed"
            raise ConfigurationError(message) from exc
        except ffmpeg.Error as exc:
            raise self._ffmpeg_error(exc) from exc

    @staticmethod
    def _ffmpeg_error(exc: ffmpeg.Error) -> ExternalServiceError:
        stderr_bytes = exc.stderr or b""
        message = stderr_bytes.decode("utf-8", errors="ignore").strip() or str(exc)
        return ExternalServiceError(f"ffmpeg failed: {message}")

    def _build_loudnorm_filter(
        self,
        measurements: dict[str, str] | None,
        print_format: str = "summary",
    ) -> str:
        """Build the loudnorm filter expression for measurement or application."""
        normalization = self.settings.NORMALIZATION
        options = [
            f"I={normalization.TARGET_LUFS}",
            f"TP={normalization.TARGET_TRUE_PEAK_DBTP}",
            f"LRA={normalization.TARGET_LRA}",
            f"print_format={print_format}",
        ]
        if measurements is not None:
            options.extend(
                [
                    f"measured_I={measurements['input_i']}",
                    f"measured_TP={measurements['input_tp']}",
                    f"measured_LRA={measurements['input_lra']}",
                    f"measured_thresh={measurements['input_thresh']}",
                    f"offset={measurements['target_offset']}",
                    "linear=true",
                ]
            )
        return f"loudnorm={':'.join(options)}"

    @staticmethod
    def _parse_measurements(stderr: str) -> dict[str, str] | None:
        """Extract loudnorm measurements from ffmpeg stderr, or ``None`` when unusable."""
        match = _LOUDNORM_JSON_PATTERN.search(stderr)
        if match is None:
            return None
        try:
            payload = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, dict):
            return None

        measurements: dict[str, str] = {}
        for key in _REQUIRED_MEASUREMENTS:
            value = payload.get(key)
            if not AudioProcessingService._is_finite_number(value):
                return None
            measurements[key] = str(value)
        return measurements

    @staticmethod
    def _is_finite_number(value: object) -> bool:
        try:
            return math.isfinite(float(str(value)))
        except (TypeError, ValueError):
            return False

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
