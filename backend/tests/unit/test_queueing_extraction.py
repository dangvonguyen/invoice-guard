"""Specify extraction queue failure callback behavior."""

from types import TracebackType
from unittest.mock import Mock, patch
from uuid import UUID

import pytest
from redis import Redis
from rq.job import Job

from app.queueing.extraction import on_extraction_failure

pytestmark = pytest.mark.unit


INVOICE_ID = UUID("10000000-0000-0000-0000-000000000001")


@pytest.mark.parametrize(
    ("retries_left", "should_mark_failed"),
    [
        (2, False),
        (1, False),
        (0, True),
    ],
)
def should_mark_extraction_failed_only_after_retries_are_exhausted(
    retries_left: int, should_mark_failed: bool
) -> None:
    """Keep retries pending and run terminal handling after the final attempt."""
    job = Mock(spec=Job)
    job.retries_left = retries_left
    job.args = [str(INVOICE_ID)]

    with patch(
        "app.queueing.extraction.InvoiceRepository.mark_extraction_failed"
    ) as mark_extraction_failed:
        on_extraction_failure(
            job=job,
            connection=Mock(spec=Redis),
            exc_type=RuntimeError,
            exc_value=RuntimeError("transient failure"),
            exc_traceback=Mock(spec=TracebackType),
        )

    if should_mark_failed:
        mark_extraction_failed.assert_awaited_once_with(invoice_id=INVOICE_ID)
    else:
        mark_extraction_failed.assert_not_awaited()
