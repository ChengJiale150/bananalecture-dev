from __future__ import annotations

import shutil

import pytest

from bananalecture_backend.core.errors import BadRequestError, NotFoundError
from bananalecture_backend.infrastructure.storage import StorageService
from bananalecture_backend.infrastructure.storage_layout import StorageLayout


@pytest.mark.unit
@pytest.mark.asyncio
async def test_storage_service_normalizes_and_reads_canonical_keys(tmp_path) -> None:
    storage = StorageService(tmp_path / "data")
    await storage.initialize()

    key = await storage.write_bytes("projects/demo/slides/slide-1/image/original.png", b"image")

    assert key == "projects/demo/slides/slide-1/image/original.png"
    assert await storage.read_bytes(key) == b"image"
    assert storage.resolve_file(key).exists()


@pytest.mark.unit
@pytest.mark.parametrize(
    ("key", "message"),
    [
        ("", "must not be empty"),
        ("/projects/demo/file.png", "must be relative"),
        ("projects\\demo\\file.png", "forward slashes"),
        ("projects/../file.png", "invalid path segments"),
        ("./projects/demo/file.png", "invalid path segments"),
    ],
)
def test_storage_service_rejects_invalid_keys(tmp_path, key: str, message: str) -> None:
    storage = StorageService(tmp_path / "data")

    with pytest.raises(BadRequestError, match=message):
        storage.normalize_key(key)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_storage_keys_survive_root_directory_migration(tmp_path) -> None:
    source_root = tmp_path / "source"
    storage = StorageService(source_root)
    await storage.initialize()
    key = StorageLayout.slide_audio("project-1", "slide-1")
    await storage.write_bytes(key, b"audio")

    target_root = tmp_path / "target"
    shutil.copytree(source_root, target_root)

    migrated = StorageService(target_root)
    await migrated.initialize()

    assert await migrated.read_bytes(key) == b"audio"


@pytest.mark.unit
def test_resolve_file_raises_not_found_for_missing_key(tmp_path) -> None:
    storage = StorageService(tmp_path / "data")

    with pytest.raises(NotFoundError, match="File not found"):
        storage.resolve_file(StorageLayout.project_video("project-1", "project-video.mp4"))
