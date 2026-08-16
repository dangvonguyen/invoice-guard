"""Acceptance scenarios for policy handbook ingestion."""

from uuid import UUID

import pytest
import pytest_asyncio
from fastapi import status
from fpdf import FPDF
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_access_token_codec, get_embedding_client
from app.database.models.user import User, UserRole
from app.main import app
from app.services.embeddings.client import EMBEDDING_DIMENSIONS

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
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.multi_cell(
        0,
        10,
        text=(
            "5.1 Meals\n"
            "Employees may expense meals up to $75 per day while traveling.\n\n"
            "5.2 Client Entertainment\n"
            "Client entertainment expenses require pre-approval from a manager.\n"
        ),
    )
    return bytes(pdf.output())


@pytest_asyncio.fixture
async def finance_reviewer(test_db: AsyncSession) -> User:
    """Persist a finance reviewer and issue their bearer token."""
    user = User(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        email="rita@example.com",
        hashed_password="unused-password-hash",
        name="Rita",
        role=UserRole.FINANCE_REVIEWER,
    )
    test_db.add(user)
    await test_db.flush()
    return user


@pytest.fixture
def auth_headers(finance_reviewer: User) -> dict[str, str]:
    """Bearer header authenticating as the finance_reviewer."""
    token = get_access_token_codec().issue(str(finance_reviewer.id))
    return {"Authorization": f"Bearer {token}"}


async def should_activate_a_valid_pdf_upload(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Accept a text-native PDF handbook and activate it immediately."""
    app.dependency_overrides[get_embedding_client] = FakeEmbeddingClient

    response = await client.post(
        "/policies/documents",
        headers=auth_headers,
        files={
            "file": ("expense-handbook-v1.pdf", handbook_pdf_bytes(), "application/pdf")
        },
    )

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["status"] == "active"
    assert body["chunk_count"] > 0

    listing = await client.get("/policies/documents", headers=auth_headers)

    assert listing.status_code == status.HTTP_200_OK
    documents = listing.json()
    assert len(documents) == 1
    assert documents[0]["status"] == "active"
