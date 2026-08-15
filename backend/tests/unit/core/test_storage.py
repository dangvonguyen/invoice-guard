"""Behavior specifications for local invoice storage."""

from pathlib import Path

import pytest

from app.core.storage import LocalStorageClient, StorageWriteError

pytestmark = [
    pytest.mark.unit,
    pytest.mark.asyncio,
]


async def should_write_content_under_the_given_key(tmp_path: Path) -> None:
    """Persist bytes at base_path/key and make them readable back."""
    client = LocalStorageClient(base_path=tmp_path)

    await client.save("abc123.pdf", b"%PDF-1.4 fake content")

    assert (tmp_path / "abc123.pdf").read_bytes() == b"%PDF-1.4 fake content"


async def should_reject_a_key_that_escapes_the_base_directory(
    tmp_path: Path,
) -> None:
    """Refuse path-traversal keys rather than writing outside base_path.

    Defense in depth: storage keys are generated internally as UUIDs
    """
    client = LocalStorageClient(base_path=tmp_path)

    with pytest.raises(StorageWriteError):
        await client.save("../escape.pdf", b"data")


async def should_load_content_stored_under_the_given_key(tmp_path: Path) -> None:
    """Return the exact bytes previously persisted under a storage key."""
    client = LocalStorageClient(base_path=tmp_path)
    content = b"%PDF-1.4 invoice content"
    await client.save("abc123.pdf", content)

    loaded = await client.read(key="abc123.pdf")

    assert loaded == content


async def should_raise_storage_error_when_loading_a_missing_key(
    tmp_path: Path,
) -> None:
    """Translate a missing local object into the storage boundary error."""
    client = LocalStorageClient(base_path=tmp_path)

    with pytest.raises(StorageWriteError):
        await client.read(key="missing.pdf")


async def should_reject_a_load_key_that_escapes_the_base_directory(
    tmp_path: Path,
) -> None:
    """Refuse path traversal before attempting to read from the filesystem."""
    client = LocalStorageClient(base_path=tmp_path)

    with pytest.raises(StorageWriteError):
        await client.read(key="../outside.pdf")
