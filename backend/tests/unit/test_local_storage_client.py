"""Behavior specifications for S3-compatible invoice storage."""

from pathlib import Path

import pytest

from app.core.storage import LocalStorageClient

pytestmark = [
    pytest.mark.unit,
    pytest.mark.asyncio,
]


async def should_write_content_under_the_given_key(tmp_path: Path) -> None:
    """Persist bytes at base_path/key and make them readable back."""
    client = LocalStorageClient(base_path=tmp_path)

    await client.save("abc123.pdf", b"%PDF-1.4 fake content")

    assert (tmp_path / "abc123.pdf").read_bytes() == b"%PDF-1.4 fake content"
