"""Object storage abstraction for uploaded invoice files."""

import asyncio
from pathlib import Path
from typing import Protocol
from uuid import uuid4


class StorageWriteError(Exception):
    """Raised when a storage backend fails to persist file content."""


class StorageClient(Protocol):
    """Read and persist uploaded file content under an opaque key."""

    def generate_key(self) -> str:
        """Generate an opaque key for invoice storage."""
        ...

    async def save(self, *, key: str, content: bytes) -> None:
        """Persist invoice content under its opaque key."""
        ...

    async def read(self, *, key: str) -> bytes:
        """Return invoice content previously persisted under `key`."""
        ...


class LocalStorageClient:
    """Store files on local disk under a base directory (dev/CI only)."""

    def __init__(self, base_path: Path) -> None:
        self._base_path = base_path.resolve()

    def generate_key(self) -> str:
        """Generate an opaque key for invoice storage."""
        return str(uuid4())

    async def save(self, key: str, content: bytes) -> None:
        """Write `content` to `base_path / key`, creating directories as needed."""
        target = (self._base_path / key).resolve()
        if self._base_path not in target.parents and target != self._base_path:
            raise StorageWriteError(f"storage key escapes base path: {key!r}")

        try:
            await asyncio.to_thread(self._write, target, content)
        except OSError as exc:
            raise StorageWriteError(f"failed to write storage key {key!r}") from exc

    async def read(self, *, key: str) -> bytes:
        """Read content stored under `key`."""
        target = (self._base_path / key).resolve()
        if self._base_path not in target.parents and target != self._base_path:
            raise StorageWriteError(f"storage key escapes base path: {key!r}")
        try:
            return await asyncio.to_thread(target.read_bytes)
        except OSError as exc:
            raise StorageWriteError(f"failed to read storage key {key!r}") from exc

    @staticmethod
    def _write(target: Path, content: bytes) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
