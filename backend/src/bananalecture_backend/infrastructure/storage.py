# ruff: noqa: D102, D107, EM101, TRY003

from __future__ import annotations

import asyncio
import tempfile
from functools import partial
from pathlib import Path, PurePosixPath

from bananalecture_backend.core.errors import BadRequestError, NotFoundError


class StorageService:
    """Manage application files through stable logical storage keys."""

    def __init__(self, root_dir: str | Path) -> None:
        self._configured_root = Path(root_dir)
        self._root = self._configured_root.expanduser().resolve(strict=False)
        self._temp_root = self._root / "_tmp"

    @property
    def root(self) -> Path:
        """Return the resolved storage root for diagnostics and tests."""
        return self._root

    async def initialize(self) -> None:
        await asyncio.to_thread(partial(self._root.mkdir, parents=True, exist_ok=True))
        await asyncio.to_thread(partial(self._temp_root.mkdir, parents=True, exist_ok=True))

    async def write_bytes(self, key: str, content: bytes) -> str:
        target = await self.prepare_output_file(key)
        await asyncio.to_thread(target.write_bytes, content)
        return self.normalize_key(key)

    async def read_bytes(self, key: str | None) -> bytes:
        target = self.resolve_file(key)
        return await asyncio.to_thread(target.read_bytes)

    async def prepare_output_file(self, key: str) -> Path:
        normalized = self._to_key_path(key)
        target = self._root / normalized
        await asyncio.to_thread(partial(target.parent.mkdir, parents=True, exist_ok=True))
        return target

    def resolve_file(self, key: str | None) -> Path:
        if key is None:
            raise NotFoundError("File not found")
        target = self._root / self._to_key_path(key)
        if not target.exists():
            raise NotFoundError("File not found")
        return target

    async def create_temp_dir(self, prefix: str) -> Path:
        await asyncio.to_thread(partial(self._temp_root.mkdir, parents=True, exist_ok=True))
        return Path(await asyncio.to_thread(tempfile.mkdtemp, prefix=prefix, dir=str(self._temp_root)))

    def normalize_key(self, key: str) -> str:
        return self._to_key_path(key).as_posix()

    def _to_key_path(self, key: str) -> PurePosixPath:
        if not key:
            raise BadRequestError("Storage key must not be empty")
        if "\\" in key:
            raise BadRequestError("Storage key must use forward slashes")
        if key.startswith("/"):
            raise BadRequestError("Storage key must be relative")
        if any(segment in {"", ".", ".."} for segment in key.split("/")):
            raise BadRequestError("Storage key contains invalid path segments")

        return PurePosixPath(key)
