"""Acceptance scenarios for policy handbook ingestion."""

import pytest
from fastapi import status
from httpx import AsyncClient

from app.api.deps import get_embedding_client
from app.core.config import get_settings
from app.main import app
from app.services.embeddings.client import EMBEDDING_DIMENSIONS
from tests.support.pdf import pdf_bytes

pytestmark = [
    pytest.mark.acceptance,
    pytest.mark.asyncio,
]


class FakeEmbeddingClient:
    """Stand in for the embedding-provider boundary with a fixed vector."""

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * EMBEDDING_DIMENSIONS for _ in texts]


def handbook_pdf_bytes() -> bytes:
    """Build a real, parseable PDF with numbered section headings."""
    return pdf_bytes(
        "5.1 Meals\n"
        "Employees may expense meals up to $75 per day while traveling.\n\n"
        "5.2 Client Entertainment\n"
        "Client entertainment expenses require pre-approval from a manager.\n"
    )


@pytest.fixture
def fake_embeddings() -> None:
    """Substitute the embedding-provider boundary for tests that reach it."""
    app.dependency_overrides[get_embedding_client] = FakeEmbeddingClient


@pytest.mark.usefixtures("fake_embeddings")
async def should_activate_a_valid_pdf_upload(
    client: AsyncClient,
    reviewer_headers: dict[str, str],
) -> None:
    """Accept a text-native PDF handbook and activate it immediately."""
    response = await client.post(
        "/policies/documents",
        headers=reviewer_headers,
        files={
            "file": ("expense-handbook-v1.pdf", handbook_pdf_bytes(), "application/pdf")
        },
    )

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()["data"]
    assert body["status"] == "active"
    assert body["chunk_count"] > 0

    listing = await client.get("/policies/documents", headers=reviewer_headers)

    assert listing.status_code == status.HTTP_200_OK
    documents = listing.json()["data"]
    assert len(documents) == 1
    assert documents[0]["status"] == "active"


@pytest.mark.usefixtures("fake_embeddings")
async def should_supersede_the_previous_active_document(
    client: AsyncClient,
    reviewer_headers: dict[str, str],
) -> None:
    """A second upload activates and demotes the first to superseded."""
    first = await client.post(
        "/policies/documents",
        headers=reviewer_headers,
        files={
            "file": ("expense-handbook-v1.pdf", handbook_pdf_bytes(), "application/pdf")
        },
    )
    assert first.status_code == status.HTTP_201_CREATED
    first_id = first.json()["data"]["policy_document_id"]

    second = await client.post(
        "/policies/documents",
        headers=reviewer_headers,
        files={
            "file": ("expense-handbook-v2.pdf", handbook_pdf_bytes(), "application/pdf")
        },
    )
    assert second.status_code == status.HTTP_201_CREATED
    second_body = second.json()["data"]
    assert second_body["status"] == "active"

    listing = await client.get("/policies/documents", headers=reviewer_headers)

    assert listing.status_code == status.HTTP_200_OK
    documents = listing.json()["data"]
    assert len(documents) == 2

    by_id = {document["policy_document_id"]: document for document in documents}
    assert by_id[first_id]["status"] == "superseded"
    assert by_id[second_body["policy_document_id"]]["status"] == "active"


async def should_reject_an_upload_from_a_non_reviewer(
    client: AsyncClient,
    employee_headers: dict[str, str],
    reviewer_headers: dict[str, str],
) -> None:
    """An employee cannot upload, and nothing gets persisted."""
    response = await client.post(
        "/policies/documents",
        headers=employee_headers,
        files={
            "file": ("expense-handbook-v1.pdf", handbook_pdf_bytes(), "application/pdf")
        },
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN

    listing = await client.get("/policies/documents", headers=reviewer_headers)

    assert listing.status_code == status.HTTP_200_OK
    assert listing.json()["data"] == []


async def should_reject_an_upload_without_authentication(
    client: AsyncClient,
) -> None:
    """A request with no bearer token is rejected before any role check."""
    response = await client.post(
        "/policies/documents",
        files={
            "file": ("expense-handbook-v1.pdf", handbook_pdf_bytes(), "application/pdf")
        },
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def should_reject_an_upload_over_the_size_cap(
    client: AsyncClient,
    reviewer_headers: dict[str, str],
) -> None:
    """A file over the configured size cap is rejected, nothing persisted."""
    oversized_content = b"%PDF-1.4\n" + b"0" * get_settings().POLICY_DOCUMENT_MAX_BYTES

    response = await client.post(
        "/policies/documents",
        headers=reviewer_headers,
        files={"file": ("huge-handbook.pdf", oversized_content, "application/pdf")},
    )

    assert response.status_code == status.HTTP_413_CONTENT_TOO_LARGE

    listing = await client.get("/policies/documents", headers=reviewer_headers)
    assert listing.json()["data"] == []


async def should_reject_a_non_pdf_upload(
    client: AsyncClient,
    reviewer_headers: dict[str, str],
) -> None:
    """A non-PDF file is rejected, naming PDF as the supported format."""
    response = await client.post(
        "/policies/documents",
        headers=reviewer_headers,
        files={
            "file": (
                "handbook.docx",
                b"fake docx bytes",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    assert "PDF" in response.json()["detail"]


async def should_reject_a_pdf_with_no_text_layer(
    client: AsyncClient,
    reviewer_headers: dict[str, str],
) -> None:
    """A scanned/image-only PDF with no extractable text is rejected."""
    response = await client.post(
        "/policies/documents",
        headers=reviewer_headers,
        files={"file": ("scanned-handbook.pdf", pdf_bytes(), "application/pdf")},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert "text" in response.json()["detail"].lower()


@pytest.mark.usefixtures("fake_embeddings")
async def should_accept_a_pdf_with_no_heading_structure(
    client: AsyncClient,
    reviewer_headers: dict[str, str],
) -> None:
    """A PDF with only prose paragraphs still ingests as a single section."""
    plain_text = (
        "Employees are expected to submit expense reports promptly and "
        "keep receipts for every purchase made while traveling on "
        "company business.\n"
    )

    response = await client.post(
        "/policies/documents",
        headers=reviewer_headers,
        files={
            "file": ("plain-handbook.pdf", pdf_bytes(plain_text), "application/pdf")
        },
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["data"]["chunk_count"] > 0
