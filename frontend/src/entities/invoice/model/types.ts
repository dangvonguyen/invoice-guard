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
  view: 'employee';
  id: string;
  status: InvoiceStatus;
  summary: InvoiceSummary | null;
  decision: Decision | null;
}

export interface UploadedInvoice {
  id: string;
  status: InvoiceStatus;
}

export interface ReviewQueueItem {
  id: string;
  submittedAt: Date;
  summary: InvoiceSummary | null;
  flagCount: number;
}

export type ExtractionConfidence = 'high' | 'low';

export interface EmployeeIdentity {
  id: string;
  name: string;
  email: string;
}

export interface ReviewFlag {
  code: string;
  summary: string | null;
  evidence: Record<string, unknown>;
}

export interface ReviewerInvoiceDetail {
  view: 'reviewer';
  id: string;
  status: InvoiceStatus;
  submittedBy: EmployeeIdentity;
  extractedFields: Record<string, unknown> | null;
  confidence: ExtractionConfidence | null;
  confidenceReason: string | null;
  reviewFlags: ReviewFlag[];
  decision: Decision | null;
}

export type InvoiceDetailView = InvoiceDetail | ReviewerInvoiceDetail;
