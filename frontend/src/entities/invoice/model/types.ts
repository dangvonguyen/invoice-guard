import type { components } from '@/shared/api/schema';

export type InvoiceStatus =
  'upload_failed' | 'processing' | 'processing_error' | 'awaiting_review' | 'approved' | 'rejected';

export interface Invoice {
  id: string;
  status: InvoiceStatus;
  createdAt: Date;
}

export interface InvoiceSummary {
  vendorName: string;
  invoiceDate: string;
  totalAmount: string;
  currency: string;
}

export interface Decision {
  outcome: 'approved' | 'rejected';
  reason: string;
  decidedBy: string;
  decidedAt: Date;
}

export interface InvoiceDetail {
  id: string;
  status: InvoiceStatus;
  summary: InvoiceSummary | null;
  decision: Decision | null;
}

export type InvoiceUploadResponse = components['schemas']['InvoiceUploadResponse'];
