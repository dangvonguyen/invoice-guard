"""Map a persisted invoice into its role-specific API response shape."""

from app.database.models.decision import InvoiceDecision
from app.database.models.invoice import ExtractionConfidence, Invoice
from app.schemas.decision import DecisionView
from app.schemas.invoice import InvoiceDetailResponse, InvoiceSummary
from app.schemas.review import (
    EmployeeIdentity,
    ReviewerInvoiceDetailResponse,
    ReviewFlagView,
)
from app.services.rules.flags import to_review_flags


def build_decision_view(decision: InvoiceDecision | None) -> DecisionView | None:
    """Build the decision view shown to both the employee and the reviewer."""
    if decision is None:
        return None
    return DecisionView(
        outcome=decision.outcome,
        reason=decision.reason,
        decided_by=decision.decided_by.name,
        decided_at=decision.decided_at,
    )


def build_invoice_summary(invoice: Invoice) -> InvoiceSummary | None:
    """Condense an invoice's extracted fields, or omit them if untrustworthy."""
    if (
        invoice.confidence != ExtractionConfidence.HIGH
        or invoice.extracted_fields is None
    ):
        return None
    return InvoiceSummary.model_validate(invoice.extracted_fields)


def employee_view(invoice: Invoice) -> InvoiceDetailResponse:
    """Build the employee-facing detail view for an owned invoice."""
    return InvoiceDetailResponse(
        id=invoice.id,
        status=invoice.status,
        invoice_summary=build_invoice_summary(invoice),
        decision=build_decision_view(invoice.decision),
    )


def reviewer_view(invoice: Invoice) -> ReviewerInvoiceDetailResponse:
    """Build the reviewer-facing detail view for any invoice."""
    flags = to_review_flags(invoice.rule_results)
    return ReviewerInvoiceDetailResponse(
        id=invoice.id,
        status=invoice.status,
        employee=EmployeeIdentity.model_validate(invoice.owner),
        extracted_fields=invoice.extracted_fields,
        confidence=invoice.confidence,
        confidence_reason=invoice.confidence_reason,
        review_flags=[
            ReviewFlagView(code=flag.code, summary=flag.summary, evidence=flag.evidence)
            for flag in flags
        ],
        decision=build_decision_view(invoice.decision),
    )
