from collections.abc import Generator
from dataclasses import replace
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from bananalecture_backend.application.use_cases.media import (
    _REFERENCE_IMAGE_MAX_DIMENSION,
    _REFERENCE_IMAGES_CACHE,
    _encode_reference_image,
    _load_template_reference_images,
)
from bananalecture_backend.core.config import ROOT_DIR
from bananalecture_backend.core.templates import get_template_config


@pytest.fixture(autouse=True)
def clear_reference_images_cache() -> Generator[None, None, None]:
    _REFERENCE_IMAGES_CACHE.clear()
    yield
    _REFERENCE_IMAGES_CACHE.clear()


@pytest.mark.unit
def test_encode_reference_image_downscales_and_compresses() -> None:
    source = (ROOT_DIR / "assets" / "xiyouji" / "wukong.png").read_bytes()

    encoded = _encode_reference_image(source)

    assert len(encoded) < len(source)
    with Image.open(BytesIO(encoded)) as image:
        assert image.format == "PNG"
        assert max(image.size) <= _REFERENCE_IMAGE_MAX_DIMENSION


@pytest.mark.unit
def test_encode_reference_image_keeps_small_images() -> None:
    output = BytesIO()
    Image.new("RGBA", (64, 64), (255, 0, 0, 255)).save(output, format="PNG")

    encoded = _encode_reference_image(output.getvalue())

    with Image.open(BytesIO(encoded)) as image:
        assert image.size == (64, 64)
        assert image.mode == "RGBA"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_template_reference_images_caches_per_template(monkeypatch: pytest.MonkeyPatch) -> None:
    template = get_template_config("xiyouji")
    assert template is not None

    reads = 0
    original_read_bytes = Path.read_bytes

    def counting_read_bytes(self: Path) -> bytes:
        nonlocal reads
        reads += 1
        return original_read_bytes(self)

    monkeypatch.setattr(Path, "read_bytes", counting_read_bytes)

    first = await _load_template_reference_images(template)
    second = await _load_template_reference_images(template)

    assert first is not None
    assert len(first) == len(template.reference_images)
    assert all(ref.startswith("data:image/png;base64,") for ref in first)
    assert second is first
    assert reads == len(template.reference_images)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_template_reference_images_skips_missing_files() -> None:
    template = get_template_config("xiyouji")
    assert template is not None
    missing_only = replace(template, id="missing-only", reference_images=["missing.png"])
    partially_missing = replace(
        template,
        id="partially-missing",
        reference_images=["missing.png", template.reference_images[0]],
    )

    assert await _load_template_reference_images(missing_only) is None

    refs = await _load_template_reference_images(partially_missing)
    assert refs is not None
    assert len(refs) == 1
