"""Behavior of the S3 storage client against a real MinIO server."""

from collections.abc import Iterator
from uuid import uuid4

import pytest
from testcontainers.community.minio import MinioContainer

from app.core.storage import S3StorageClient, StorageWriteError

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio,
]


@pytest.fixture(scope="module")
def minio() -> Iterator[MinioContainer]:
    """Run a MinIO server for the duration of this module."""
    with MinioContainer() as container:
        yield container


def make_client(minio: MinioContainer, *, prefix: str = "") -> S3StorageClient:
    """Create a fresh bucket and an S3 client bound to it."""
    config = minio.get_config()
    bucket = f"invoices-{uuid4().hex}"
    minio.get_client().make_bucket(bucket)
    return S3StorageClient(
        bucket=bucket,
        endpoint_url=f"http://{config['endpoint']}",
        access_key_id=config["access_key"],
        secret_access_key=config["secret_key"],
        prefix=prefix,
    )


async def should_round_trip_content_stored_under_a_key(minio: MinioContainer) -> None:
    """Return the exact bytes previously written under a generated key."""
    storage = make_client(minio)
    key = storage.generate_key()
    content = b"%PDF-1.4 invoice content"

    await storage.save(key=key, content=content)

    assert await storage.read(key=key) == content


async def should_store_objects_under_the_configured_prefix(
    minio: MinioContainer,
) -> None:
    """Apply the prefix to the object name without baking it into the key."""
    storage = make_client(minio, prefix="invoices/")

    await storage.save(key="abc123", content=b"data")

    stored = minio.get_client().get_object(storage._bucket, "invoices/abc123")
    assert stored.read() == b"data"


async def should_raise_storage_error_when_reading_a_missing_key(
    minio: MinioContainer,
) -> None:
    """Translate a missing object into the storage boundary error."""
    storage = make_client(minio)

    with pytest.raises(StorageWriteError):
        await storage.read(key="does-not-exist")
