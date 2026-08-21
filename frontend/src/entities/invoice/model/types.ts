import type { components } from '@/shared/api/schema';

export type InvoiceStatus =
  'upload_failed' | 'processing' | 'processing_error' | 'awaiting_review' | 'approved' | 'rejected';

export interface Invoice {
  id: string;
  status: InvoiceStatus;
  createdAt: Date;
}

export type InvoiceUploadResponse = components['schemas']['InvoiceUploadResponse'];
export type InvoiceSummary = components['schemas']['InvoiceSummary'];
export type InvoiceDetailResponse = components['schemas']['InvoiceDetailResponse'];
export type DecisionView = components['schemas']['DecisionView'];
