import type { InvoiceStatus } from './types';

const STATUS_LABELS: Record<InvoiceStatus, string> = {
  upload_failed: 'Upload Failed',
  processing: 'Processing',
  processing_error: 'Processing Error',
  awaiting_review: 'Awaiting Review',
  approved: 'Approved',
  rejected: 'Rejected',
};

export function invoiceStatusLabel(status: InvoiceStatus): string {
  return STATUS_LABELS[status];
}

const STATUS_BADGE_VARIANTS: Record<InvoiceStatus, 'secondary' | 'outline' | 'destructive'> = {
  upload_failed: 'destructive',
  processing: 'secondary',
  processing_error: 'destructive',
  awaiting_review: 'outline',
  approved: 'secondary',
  rejected: 'destructive',
};

export function invoiceStatusBadgeVariant(
  status: InvoiceStatus,
): 'secondary' | 'outline' | 'destructive' {
  return STATUS_BADGE_VARIANTS[status];
}
