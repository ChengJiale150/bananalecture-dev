# ruff: noqa: TC003

from __future__ import annotations

import asyncio
from pathlib import Path

from PIL import Image

from bananalecture_backend.core.logging_config import get_global_logger

global_logger = get_global_logger()


class ImageProcessingService:
    """Pillow-based image preprocessing for video rendering."""

    async def resize_image(self, input_path: Path, output_path: Path, width: int, height: int) -> None:
        """Resize and pad an image to exact dimensions, matching ffmpeg scale+pad behaviour."""
        await asyncio.to_thread(self._resize_sync, input_path, output_path, width, height)

    def _resize_sync(self, input_path: Path, output_path: Path, width: int, height: int) -> None:
        global_logger.bind(
            input=str(input_path),
            output=str(output_path),
            width=width,
            height=height,
        ).info("image_preprocess_started")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with Image.open(input_path) as img:
            rgb_img = img.convert("RGB")
            rgb_img.thumbnail((width, height), Image.Resampling.LANCZOS)

            canvas = Image.new("RGB", (width, height), (0, 0, 0))
            offset = ((width - rgb_img.width) // 2, (height - rgb_img.height) // 2)
            canvas.paste(rgb_img, offset)
            canvas.save(output_path, format="JPEG", quality=95)

        if not output_path.exists():
            message = "Image preprocessing did not produce an output file"
            global_logger.bind(output=str(output_path)).error("image_preprocess_failed")
            raise RuntimeError(message)

        global_logger.bind(output=str(output_path)).info("image_preprocess_succeeded")


def build_image_processing_service() -> ImageProcessingService:
    """Build an image processing service."""
    return ImageProcessingService()
