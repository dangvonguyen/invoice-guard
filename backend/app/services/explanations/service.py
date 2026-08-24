"""Use case for retrieving or generating an explanation for one review flag."""

from uuid import UUID

from app.core.errors import NotFoundError, ValidationError
from app.database.models.explanation import Explanation
from app.database.models.rule_result import RuleOutcome
from app.database.repositories.explanation import ExplanationRepository
from app.database.repositories.invoice import InvoiceRepository
from app.database.repositories.policy_document import PolicyDocumentRepository
from app.schemas.explanation import CitationView, ExplanationView
from app.services.embeddings.client import EmbeddingClient
from app.services.explanations.generation import GenerationClient, RetrievedChunk
from app.services.rules.flags import is_explainable, summary_for
from app.services.rules.result import RuleCode


class RuleNotExplainableError(ValidationError):
    """Raised when the rule code isn't backed by a policy-configured threshold."""

    code = "RULE_NOT_EXPLAINABLE"


class NoActivePolicyDocumentError(NotFoundError):
    """Raised when no policy document has ever been ingested."""

    code = "NO_ACTIVE_POLICY_DOCUMENT"


class ExplanationService:
    """Retrieve a cached explanation, or retrieve, generate, and cache a new one."""

    def __init__(
        self,
        *,
        invoice_repo: InvoiceRepository,
        policy_repo: PolicyDocumentRepository,
        explanation_repo: ExplanationRepository,
        embedding_client: EmbeddingClient,
        generation_client: GenerationClient,
        generation_model: str,
        retrieval_top_k: int,
    ) -> None:
        self._invoice_repo = invoice_repo
        self._policy_repo = policy_repo
        self._explanation_repo = explanation_repo
        self._embedding_client = embedding_client
        self._generation_client = generation_client
        self._generation_model = generation_model
        self._retrieval_top_k = retrieval_top_k

    async def resolve(
        self, *, invoice_id: UUID, rule_code: RuleCode
    ) -> ExplanationView:
        """Return the flag's explanation."""
        invoice = await self._invoice_repo.get_for_review_view(invoice_id)
        if invoice is None:
            raise NotFoundError(f"Invoice {invoice_id} was not found.")

        if not is_explainable(rule_code):
            raise RuleNotExplainableError(f"Rule {rule_code.value} is not explainable.")

        flag = next(
            (
                result
                for result in invoice.rule_results
                if result.rule_code == rule_code.value
                and result.outcome == RuleOutcome.FAIL
            ),
            None,
        )
        if flag is None:
            raise NotFoundError(
                f"No failed flag for rule {rule_code.value} on invoice {invoice_id}."
            )

        existing = await self._explanation_repo.get_by_rule_result(flag.id)
        if existing is not None:
            return _to_view(existing)

        active_document = await self._policy_repo.get_active_document()
        if active_document is None:
            raise NoActivePolicyDocumentError(
                "No active policy document has been ingested."
            )

        summary = (
            summary_for(rule_code, RuleOutcome.FAIL) or f"{rule_code.value} failed."
        )
        query_text = _build_query_text(summary=summary, evidence=flag.evidence)
        [query_embedding] = await self._embedding_client.embed_batch([query_text])

        chunks = await self._policy_repo.search_similar_chunks(
            embedding=query_embedding, top_k=self._retrieval_top_k
        )

        generated = await self._generation_client.generate_explanation(
            summary=summary,
            evidence=flag.evidence,
            chunks=[
                RetrievedChunk(
                    chunk_id=chunk.id,
                    section_label=chunk.section_label,
                    content=chunk.content,
                )
                for chunk in chunks
            ],
        )

        citations = [
            CitationView(
                chunk_id=chunks[index].id,
                section_label=chunks[index].section_label,
                content=chunks[index].content,
            )
            for index in generated.cited_chunk_indexes
            if 0 <= index < len(chunks)
        ]

        persisted = await self._explanation_repo.create(
            rule_result_id=flag.id,
            narrative=generated.narrative,
            citations=[citation.model_dump(mode="json") for citation in citations],
        )

        return _to_view(persisted)


def _build_query_text(*, summary: str, evidence: dict[str, object]) -> str:
    """Build the retrieval query text from a flag's summary and evidence values."""
    evidence_text = ", ".join(f"{key}: {value}" for key, value in evidence.items())
    return f"{summary} ({evidence_text})".strip()


def _to_view(explanation: Explanation) -> ExplanationView:
    """Project a persisted explanation row into its reviewer-facing view."""
    return ExplanationView(
        explanation=explanation.narrative,
        citations=[
            CitationView.model_validate(citation) for citation in explanation.citations
        ],
    )
