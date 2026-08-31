"""Object storage abstraction for uploaded invoice files."""

from __future__ import annotations

import asyncio
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Protocol
from uuid import uuid4

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import get_settings

if TYPE_CHECKING:
    from app.core.config import Settings


class StorageWriteError(Exception):
    """Raised when a storage backend fails to persist or return file content."""


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

    async def save(self, *, key: str, content: bytes) -> None:
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


class S3StorageClient:
    """Store files in an S3-compatible object store."""

    def __init__(
        self,
        *,
        bucket: str,
        endpoint_url: str | None = None,
        region: str = "us-east-1",
        prefix: str = "",
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
    ) -> None:
        self._bucket = bucket
        self._prefix = prefix
        # Self-hosted stores (MinIO, Ceph) are addressed path-style
        # AWS S3 uses the virtual-hosted
        addressing = Config(s3={"addressing_style": "path"}) if endpoint_url else None
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            region_name=region,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            config=addressing,
        )

    def generate_key(self) -> str:
        """Generate an opaque key for invoice storage."""
        return str(uuid4())

    async def save(self, *, key: str, content: bytes) -> None:
        """Put `content` at `<prefix><key>` in the bucket."""
        try:
            await asyncio.to_thread(self._put, key, content)
        except (BotoCoreError, ClientError) as exc:
            raise StorageWriteError(f"failed to write storage key {key!r}") from exc

    async def read(self, *, key: str) -> bytes:
        """Return the object stored at `<prefix><key>` in the bucket."""
        try:
            return await asyncio.to_thread(self._get, key)
        except (BotoCoreError, ClientError) as exc:
            raise StorageWriteError(f"failed to read storage key {key!r}") from exc

    def _put(self, key: str, content: bytes) -> None:
        self._client.put_object(
            Bucket=self._bucket,
            Key=f"{self._prefix}{key}",
            Body=content,
        )

    def _get(self, key: str) -> bytes:
        response = self._client.get_object(
            Bucket=self._bucket,
            Key=f"{self._prefix}{key}",
        )
        return response["Body"].read()


def build_storage_client(settings: Settings) -> StorageClient:
    """Return the storage client selected by `STORAGE_BACKEND`."""
    if settings.STORAGE_BACKEND == "s3":
        bucket = settings.STORAGE_S3_BUCKET
        if bucket is None:
            raise ValueError(
                "STORAGE_S3_BUCKET is required when STORAGE_BACKEND is 's3'"
            )
        secret = settings.STORAGE_S3_SECRET_ACCESS_KEY
        return S3StorageClient(
            bucket=bucket,
            endpoint_url=settings.STORAGE_S3_ENDPOINT_URL,
            region=settings.STORAGE_S3_REGION,
            prefix=settings.STORAGE_S3_PREFIX,
            access_key_id=settings.STORAGE_S3_ACCESS_KEY_ID,
            secret_access_key=secret.get_secret_value() if secret else None,
        )
    return LocalStorageClient(base_path=Path(settings.STORAGE_LOCAL_PATH))


@lru_cache
def get_storage_client() -> StorageClient:
    """Return the process-wide storage client for the configured backend."""
    return build_storage_client(get_settings())
