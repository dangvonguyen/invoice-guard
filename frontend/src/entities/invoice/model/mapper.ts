import type {
  DecisionDto,
  InvoiceDetailDto,
  InvoiceListItemDto,
  InvoiceSummaryDto,
} from '../api/types';

import type { Decision, Invoice, InvoiceDetail, InvoiceSummary } from './types';

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
    id: dto.id,
    status: dto.status,
    summary: dto.invoice_summary === null ? null : toInvoiceSummary(dto.invoice_summary),
    decision: dto.decision === null ? null : toDecision(dto.decision),
  };
}
