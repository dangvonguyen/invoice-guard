import type {
  CitationDto,
  DecisionDto,
  EmployeeIdentityDto,
  ExplanationDto,
  InvoiceDetailDto,
  InvoiceListItemDto,
  InvoiceSummaryDto,
  InvoiceUploadResponseDto,
  ReviewerInvoiceDetailDto,
  ReviewFlagDto,
  ReviewQueueItemDto,
} from '../api/types';

import type {
  Citation,
  Decision,
  EmployeeIdentity,
  Explanation,
  Invoice,
  InvoiceDetail,
  InvoiceSummary,
  ReviewerInvoiceDetail,
  ReviewFlag,
  ReviewQueueItem,
  UploadedInvoice,
} from './types';

export function toInvoice(dto: InvoiceListItemDto): Invoice {
  return {
    id: dto.id,
    status: dto.status,
    createdAt: new Date(dto.created_at),
  };
}

export function toInvoiceSummary(dto: InvoiceSummaryDto): InvoiceSummary {
  return {
    vendorName: dto.vendor_name,
    invoiceDate: dto.invoice_date,
    totalAmount: dto.total_amount,
    currency: dto.currency,
  };
}

export function toDecision(dto: DecisionDto): Decision {
  return {
    outcome: dto.outcome,
    reason: dto.reason,
    decidedBy: dto.decided_by,
    decidedAt: new Date(dto.decided_at),
  };
}

export function toInvoiceDetail(dto: InvoiceDetailDto): InvoiceDetail {
  return {
    view: 'employee',
    id: dto.id,
    status: dto.status,
    summary: dto.invoice_summary === null ? null : toInvoiceSummary(dto.invoice_summary),
    decision: dto.decision === null ? null : toDecision(dto.decision),
  };
}

export function toEmployeeIdentity(dto: EmployeeIdentityDto): EmployeeIdentity {
  return {
    id: dto.id,
    name: dto.name,
    email: dto.email,
  };
}

export function toReviewFlag(dto: ReviewFlagDto): ReviewFlag {
  return {
    code: dto.code,
    summary: dto.summary,
    evidence: dto.evidence,
    explainable: dto.explainable,
  };
}

export function toReviewerInvoiceDetail(dto: ReviewerInvoiceDetailDto): ReviewerInvoiceDetail {
  return {
    view: 'reviewer',
    id: dto.id,
    status: dto.status,
    submittedBy: toEmployeeIdentity(dto.employee),
    extractedFields: dto.extracted_fields,
    confidence: dto.confidence,
    confidenceReason: dto.confidence_reason,
    reviewFlags: dto.review_flags.map(toReviewFlag),
    decision: dto.decision === null ? null : toDecision(dto.decision),
  };
}

export function toCitation(dto: CitationDto): Citation {
  return {
    chunkId: dto.chunk_id,
    sectionLabel: dto.section_label,
    content: dto.content,
  };
}

export function toExplanation(dto: ExplanationDto): Explanation {
  return {
    explanation: dto.explanation,
    citations: dto.citations.map(toCitation),
    generatedByModel: dto.generated_by_model,
    generatedAt: new Date(dto.generated_at),
  };
}

export function toUploadedInvoice(dto: InvoiceUploadResponseDto): UploadedInvoice {
  return {
    id: dto.id,
    status: dto.status,
  };
}

export function toReviewQueueItem(dto: ReviewQueueItemDto): ReviewQueueItem {
  return {
    id: dto.id,
    submittedAt: new Date(dto.submitted_at),
    summary: dto.invoice_summary === null ? null : toInvoiceSummary(dto.invoice_summary),
    flagCount: dto.flag_count,
  };
}
