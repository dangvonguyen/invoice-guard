"""Specify extraction queue failure callback behavior."""

from types import TracebackType
from unittest.mock import AsyncMock, MagicMock, Mock, call, patch
from uuid import UUID

import pytest
from redis import Redis
from rq.job import Job

from app.queueing import extraction

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
        extraction.handle_failure(
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


@pytest.mark.asyncio
async def should_evaluate_rules_in_a_fresh_session_after_extraction() -> None:
    """Do not reuse the transaction that extraction commits internally."""
    extraction_session = Mock()
    extraction_context = MagicMock()
    extraction_context.__aenter__ = AsyncMock(return_value=extraction_session)
    extraction_context.__aexit__ = AsyncMock(return_value=None)

    evaluation_session = Mock()
    evaluation_context = MagicMock()
    evaluation_context.__aenter__ = AsyncMock(return_value=evaluation_session)
    evaluation_context.__aexit__ = AsyncMock(return_value=None)

    session_factory = Mock(side_effect=[extraction_context, evaluation_context])

    with (
        patch(
            "app.queueing.extraction.get_session_factory", return_value=session_factory
        ),
        patch("app.queueing.extraction.InvoiceRepository") as invoices,
        patch("app.queueing.extraction.RuleResultRepository") as rule_results,
        patch("app.queueing.extraction.extract_invoice", AsyncMock()),
        patch("app.queueing.extraction.evaluate_rules", AsyncMock()),
    ):
        await extraction.execute(str(INVOICE_ID))

    assert session_factory.call_args_list == [call(), call()]
    invoices.assert_called_once_with(session=extraction_session)
    rule_results.assert_called_once_with(session=evaluation_session)
