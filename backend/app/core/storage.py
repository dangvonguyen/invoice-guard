"""Object storage abstraction for uploaded invoice files."""

import asyncio
from pathlib import Path
from uuid import uuid4


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
        await asyncio.to_thread(self._write, target, content)

    @staticmethod
    def _write(target: Path, content: bytes) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
